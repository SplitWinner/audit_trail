#!/usr/bin/env python3
"""Independent verifier for the SplitWinner official audit_trail ledger.

Subcommands:
  anchor   Mode A — recompute a day's manifest from prediction rows + salt
  content  Mode B — recompute per-row content hashes from full rows
  chain    Mode D — verify the prev_anchor_hash links across all anchors
  bitcoin  Mode C — check the OpenTimestamps Bitcoin attestations
  vectors  self-test against SPEC/vectors golden vectors

Design invariants (see SPEC/ and INTEGRITY.md):
  * ONE verifier verifies EVERY anchor ever published on this chain. The
    verifier's own hash is NOT part of any anchored payload; tool provenance
    lives in SPEC/VERIFIERS.md. Improving this file never forks the chain,
    and CI re-verifies the full published corpus on every change.
  * Schema changes are forward-only. A published anchor is never rewritten.
  * Refusal over guessing: anything this tool cannot positively establish is
    reported as a failure (exit 1) or an operational refusal (exit 2), never
    as a pass.

Pure standard library. Modes A/B/D make no network calls. Mode C shells out
to the `ots` client (requirements-bitcoin.txt) and only the online form
talks to the network.

Exit codes: 0 verified · 1 cryptographic failure · 2 operational error.
"""

from __future__ import annotations

import argparse
import base64  # noqa: F401  (kept out of salt handling deliberately; see _load_salt)
import hashlib
import hmac as hmac_mod
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

CHAIN_ID = "splitwinner-official-2026"
HASH_ALGORITHM = "hmac-sha256"

# ---------------------------------------------------------------------------
# Canonicalization — the byte-level rules live in SPEC/canonicalization.md.
# json.dumps with sorted keys, compact separators, ensure_ascii=True, and NO
# default= coercion: a value the canonical form cannot represent is an error,
# never a silent str(). Non-finite floats are rejected.
# ---------------------------------------------------------------------------


def _canonical_bytes(obj: object) -> bytes:
    _reject_nonfinite(obj)
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def _reject_nonfinite(obj: object) -> None:
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError("non-finite float in payload")
    if isinstance(obj, dict):
        for v in obj.values():
            _reject_nonfinite(v)
    if isinstance(obj, list):
        for v in obj:
            _reject_nonfinite(v)


# ---------------------------------------------------------------------------
# Row payload schemas (Mode B). Each ledger row declares `payload_schema`;
# its content hash covers the projection listed here plus the declaration
# itself. New market types register new schemas in SPEC/payloads/ — adding
# one never touches existing schemas, rows, or anchors.
# ---------------------------------------------------------------------------

PAYLOAD_SCHEMAS: dict[str, tuple[str, ...]] = {
    "classification.v1": (
        "sport", "category", "dataset", "model_id", "prediction_type",
        "prediction_mode", "season", "date_event", "game_time", "home_team",
        "away_team", "home_team_rotation", "away_team_rotation", "home_line",
        "away_line", "home_juice", "away_juice", "prediction", "confidence",
        "bet_type", "conformal_set_size", "conformal_set",
        "conformal_coverage_target", "intelligence_category", "probability",
        "edge", "expected_value", "kelly_criterion", "kelly_amount",
        "sharp_money", "line_source",
    ),
}


def row_content_hash(row: dict) -> str:
    schema = row.get("payload_schema")
    if schema not in PAYLOAD_SCHEMAS:
        raise ValueError(
            f"unknown payload_schema {schema!r}; known: {sorted(PAYLOAD_SCHEMAS)}"
        )
    fields = PAYLOAD_SCHEMAS[schema]
    payload = {f: row.get(f) for f in fields}
    payload["payload_schema"] = schema
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


# ---------------------------------------------------------------------------
# Day manifest (Mode A). manifest_schema_version 1. The manifest is
# deliberately type-blind: rows contribute only (id, content_hash,
# recorded_at) regardless of payload_schema, so new prediction types never
# change this layer. prev_anchor_hash and report_sha256 are folded INTO the
# hashed payload, chaining days and binding the daily report.
# ---------------------------------------------------------------------------

MANIFEST_SCHEMA_VERSIONS = (1,)


def canonical_day_payload(
    predictions: list[dict],
    new_models: list[dict],
    prev_anchor_hash: str | None,
    report_sha256: str | None,
    anchor_date: str,
) -> bytes:
    rows = sorted(
        (
            {
                "id": str(r["id"]),
                "content_hash": r["content_hash"],
                "recorded_at": r["recorded_at"],
            }
            for r in predictions
        ),
        key=lambda r: (r["content_hash"], r["id"]),
    )
    models = sorted(
        (
            {
                "model_id": m["model_id"],
                "artifact_sha256": m["artifact_sha256"],
                "recorded_at": m["recorded_at"],
            }
            for m in new_models
        ),
        key=lambda m: m["model_id"],
    )
    return _canonical_bytes(
        {
            "chain_id": CHAIN_ID,
            "anchor_date": anchor_date,
            "predictions": rows,
            "new_models": models,
            "prev_anchor_hash": prev_anchor_hash,
            "report_sha256": report_sha256,
        }
    )


def manifest_hash(payload: bytes, salt: bytes) -> str:
    return hmac_mod.new(salt, payload, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Salt: exactly 64 hex characters (32 bytes). No base64, no sniffing.
# ---------------------------------------------------------------------------

_SALT_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def load_salt(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8").strip()
    if not _SALT_RE.match(text):
        raise ValueError("salt must be exactly 64 hex characters (32 bytes)")
    return bytes.fromhex(text)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _self_sha256() -> str:
    return _file_sha256(Path(__file__).resolve())


# ---------------------------------------------------------------------------
# Mode A — anchor
# ---------------------------------------------------------------------------


def _verify_anchor(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    anchor_path = repo / "anchors" / f"{args.date}.json"
    if not anchor_path.exists():
        print(f"REFUSE  no anchor for {args.date} at {anchor_path} (run from repo root?)")
        return 2
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))

    version = anchor.get("manifest_schema_version")
    if version not in MANIFEST_SCHEMA_VERSIONS:
        print(
            f"REFUSE  manifest_schema_version {version!r} unknown to this verifier "
            f"(supports {MANIFEST_SCHEMA_VERSIONS}); update the verifier — the current "
            "one always verifies the full chain (SPEC/VERIFIERS.md)"
        )
        return 2
    if anchor.get("chain_id") != CHAIN_ID:
        print(f"FAIL  chain_id {anchor.get('chain_id')!r} != {CHAIN_ID!r}")
        return 1

    predictions = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    if not isinstance(predictions, list):
        print("REFUSE  --predictions must be a JSON array of rows")
        return 2
    models: list[dict] = []
    if args.models:
        models = json.loads(Path(args.models).read_text(encoding="utf-8"))
    try:
        salt = load_salt(Path(args.salt))
    except ValueError as err:
        print(f"REFUSE  {err}")
        return 2

    payload = canonical_day_payload(
        predictions,
        models,
        anchor.get("prev_anchor_hash"),
        anchor.get("report_sha256"),
        anchor["anchor_date"],
    )
    computed = manifest_hash(payload, salt)
    if computed != anchor["manifest_hash"]:
        print(
            f"FAIL  anchor {args.date}: recomputed manifest {computed[:16]}… does not "
            f"match published {anchor['manifest_hash'][:16]}…"
        )
        return 1
    print(
        f"PASS  anchor {args.date} (schema v{version}): {len(predictions)} predictions "
        f"+ {len(models)} model registrations hash to {computed[:16]}… matching the "
        "published anchor"
    )
    return 0


# ---------------------------------------------------------------------------
# Mode B — content
# ---------------------------------------------------------------------------


def _verify_content(args: argparse.Namespace) -> int:
    rows = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        print("REFUSE  --predictions must be a JSON array of full rows")
        return 2
    mismatches = []
    for row in rows:
        try:
            computed = row_content_hash(row)
        except ValueError as err:
            print(f"REFUSE  row {row.get('id')}: {err}")
            return 2
        if computed != row.get("content_hash"):
            mismatches.append((row.get("id"), computed, row.get("content_hash")))
    if mismatches:
        for row_id, computed, published in mismatches[:10]:
            print(f"FAIL  row {row_id}: computed {computed[:16]}… != {str(published)[:16]}…")
        if len(mismatches) > 10:
            print(f"FAIL  … and {len(mismatches) - 10} more")
        return 1
    print(f"PASS  {len(rows)} rows: every content_hash matches its payload")
    return 0


# ---------------------------------------------------------------------------
# Mode D — chain
# ---------------------------------------------------------------------------


def _verify_chain(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    anchors_dir = repo / "anchors"
    if not anchors_dir.is_dir():
        print("REFUSE  no anchors/ directory (run from repo root?)")
        return 2
    paths = sorted(anchors_dir.glob("*.json"))
    if not paths:
        print("PASS  chain empty: the ledger opens with its first anchor")
        return 0
    prev_path: Path | None = None
    for path in paths:
        anchor = json.loads(path.read_text(encoding="utf-8"))
        expected = _file_sha256(prev_path) if prev_path else None
        actual = anchor.get("prev_anchor_hash")
        if actual != expected:
            shown = expected[:16] + "…" if expected else None
            got = actual[:16] + "…" if isinstance(actual, str) else actual
            print(f"FAIL  {path.name}: prev_anchor_hash {got} != {shown}")
            return 1
        prev_path = path
    print(f"PASS  chain intact: {len(paths)} anchors, genesis {paths[0].stem} → head {paths[-1].stem}")
    return 0


# ---------------------------------------------------------------------------
# Mode C — bitcoin (ots)
# ---------------------------------------------------------------------------

_BLOCK_RE = re.compile(r"Bitcoin block (\d+)")
_OTS_DIGEST_RE = re.compile(r"File sha256 hash: ([0-9a-f]{64})")


def _run_ots(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(args, capture_output=True, text=True, timeout=180)
    return proc.returncode, proc.stdout + proc.stderr


def _verify_bitcoin(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    anchors_dir = repo / "anchors"
    if not anchors_dir.is_dir():
        print("REFUSE  no anchors/ directory (run from repo root?)")
        return 2
    targets = (
        [anchors_dir / f"{args.date}.json"]
        if args.date
        else sorted(p for p in anchors_dir.glob("*.json") if p.with_suffix(".json.ots").exists())
    )
    if not targets:
        print("PASS  no stamped anchors yet")
        return 0
    if shutil.which("ots") is None:
        print("REFUSE  `ots` client not found — pip install -r requirements-bitcoin.txt")
        return 2
    failures = 0
    for path in targets:
        ots_path = path.with_suffix(".json.ots")
        if not ots_path.exists():
            print(f"FAIL  {path.name}: no .ots proof")
            failures += 1
            continue
        digest = _file_sha256(path)
        if args.offline:
            code, out = _run_ots(["ots", "info", str(ots_path)])
            bound = _OTS_DIGEST_RE.search(out)
            block = _BLOCK_RE.search(out)
            if bound and bound.group(1) == digest and block:
                print(f"PASS  {path.name}: proof binds {digest[:16]}…, Bitcoin block {block.group(1)} (offline)")
            elif bound and bound.group(1) != digest:
                print(f"FAIL  {path.name}: proof binds {bound.group(1)[:16]}…, file is {digest[:16]}…")
                failures += 1
            else:
                print(f"REFUSE  {path.name}: offline info cannot confirm the digest binding — run online")
                failures += 1
        else:
            code, out = _run_ots(["ots", "verify", "-d", digest, str(ots_path)])
            block = _BLOCK_RE.search(out)
            if code == 0 and block:
                print(f"PASS  {path.name}: Bitcoin block {block.group(1)} attests {digest[:16]}…")
            else:
                print(f"FAIL  {path.name}: ots verify did not confirm ({out.strip().splitlines()[-1] if out.strip() else 'no output'})")
                failures += 1
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# vectors — self-test against SPEC/vectors
# ---------------------------------------------------------------------------


def _verify_vectors(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    vectors_dir = repo / "SPEC" / "vectors"
    files = sorted(vectors_dir.glob("*.json"))
    if not files:
        print("REFUSE  no golden vectors found under SPEC/vectors/")
        return 2
    failures = 0
    for path in files:
        vector = json.loads(path.read_text(encoding="utf-8"))
        kind = vector["kind"]
        if kind == "row":
            computed = row_content_hash(vector["row"])
            expected = vector["expected_content_hash"]
        elif kind == "day_manifest":
            payload = canonical_day_payload(
                vector["predictions"],
                vector["new_models"],
                vector["prev_anchor_hash"],
                vector["report_sha256"],
                vector["anchor_date"],
            )
            computed = manifest_hash(payload, bytes.fromhex(vector["salt_hex"]))
            expected = vector["expected_manifest_hash"]
        else:
            print(f"REFUSE  {path.name}: unknown vector kind {kind!r}")
            return 2
        if computed != expected:
            print(f"FAIL  {path.name}: computed {computed[:16]}… != expected {expected[:16]}…")
            failures += 1
        else:
            print(f"PASS  {path.name}")
    return 1 if failures else 0


# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Independent verifier for the SplitWinner audit_trail official ledger. "
            "Subcommands: anchor (Mode A), content (Mode B), chain (Mode D), "
            "bitcoin (Mode C), vectors (self-test)."
        )
    )
    parser.add_argument("--version", action="version", version=f"verify.py sha256 {_self_sha256()}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_anchor = sub.add_parser("anchor", help="Mode A: recompute a day's manifest")
    p_anchor.add_argument("--date", required=True)
    p_anchor.add_argument("--predictions", required=True)
    p_anchor.add_argument("--models")
    p_anchor.add_argument("--salt", required=True)
    p_anchor.add_argument("--repo-root", default=".")
    p_anchor.set_defaults(func=_verify_anchor)

    p_content = sub.add_parser("content", help="Mode B: recompute per-row content hashes")
    p_content.add_argument("--predictions", required=True)
    p_content.set_defaults(func=_verify_content)

    p_chain = sub.add_parser("chain", help="Mode D: verify prev_anchor_hash links")
    p_chain.add_argument("--repo-root", default=".")
    p_chain.set_defaults(func=_verify_chain)

    p_btc = sub.add_parser("bitcoin", help="Mode C: check Bitcoin attestations")
    p_btc.add_argument("--date")
    p_btc.add_argument("--offline", action="store_true")
    p_btc.add_argument("--repo-root", default=".")
    p_btc.set_defaults(func=_verify_bitcoin)

    p_vec = sub.add_parser("vectors", help="self-test against SPEC/vectors")
    p_vec.add_argument("--repo-root", default=".")
    p_vec.set_defaults(func=_verify_vectors)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
