#!/usr/bin/env python3
"""Generate the synthetic, runnable fixture for verify.py — and the golden vectors.

Produces a two-day chain under sample/ so every mode is exercisable end to end:

  sample/anchors/2099-01-01.json[.ots absent]   genesis anchor (prev_anchor_hash null)
  sample/anchors/2099-01-02.json                second anchor, chained + report-bound
  sample/reports/2099-01-01.json                synthetic daily report (hashed into day 2)
  sample/predictions_full_<date>.json           full rows for Mode B
  sample/predictions_subset_<date>.json         {id, content_hash, recorded_at} for Mode A
  sample/models_<date>.json                     model registrations per day
  sample/salt_<date>.hex                        the fixture's salts (64 hex chars)

EVERYTHING IN THIS FIXTURE IS FAKE. Dates are far-future so no fixture can be
mistaken for production. Values are deterministic so regeneration is byte-stable.

Golden vectors under SPEC/vectors/ are written from the same run. The vectors
freeze the canonical encodings; .github/workflows/integrity.yml re-runs
`verify.py vectors` on every push, so any drift in canonicalization fails CI.

Unlike the alpha's fixture, this script imports the canonicalization FROM
verify.py rather than duplicating it — the golden vectors, not a second copy
of the code, are what pins behavior.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta
import sys
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

import verify  # noqa: E402

_SAMPLE = _REPO_ROOT / "sample"
_VECTORS = _REPO_ROOT / "SPEC" / "vectors"

_SPORTS = ("MLB", "NBA", "NFL", "NHL")


def _fake_row(i: int, date: str) -> dict:
    sport = _SPORTS[i % len(_SPORTS)]
    home = f"Home {i}"
    away = f"Away {i}"
    row_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"sample-{date}-{i}-{sport}"))
    row = {
        "id": row_id,
        "payload_schema": "classification.v1",
        "sport": sport,
        "category": "game",
        "dataset": "pb",
        "model_id": f"2099_2100_{sport.lower()}_pb_gamewinner",
        "prediction_type": "gamewinner",
        "prediction_mode": "live",
        "season": "2099_2100",
        "date_event": date,
        "game_time": f"{date}T23:0{i % 10}:00+00:00",
        "home_team": home,
        "away_team": away,
        "home_team_rotation": str(500 + i * 2),
        "away_team_rotation": str(501 + i * 2),
        "home_line": "-1.5",
        "away_line": "1.5",
        "home_juice": "-110",
        "away_juice": "-105",
        "prediction": home if i % 2 == 0 else away,
        "confidence": "0.6400",
        "bet_type": "favorite" if i % 2 == 0 else "underdog",
        "conformal_set_size": 1,
        "conformal_set": [home if i % 2 == 0 else away],
        "conformal_coverage_target": "0.90",
        "intelligence_category": "bet" if i % 3 == 0 else "skip",
        "probability": "0.6400",
        "edge": "0.0450",
        "expected_value": "0.0310",
        "kelly_criterion": "0.0200",
        "kelly_amount": "20.00",
        "sharp_money": "home" if i % 2 == 0 else "away",
        "line_source": "consensus",
        "recorded_at": f"{date}T13:0{i % 10}:00+00:00",
    }
    row["content_hash"] = verify.row_content_hash(row)
    return row


def _salt_for(date: str) -> bytes:
    return hashlib.sha256(f"splitwinner-sample-salt-{date}".encode()).digest()


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_day(
    date: str,
    row_count: int,
    models: list[dict],
    prev_anchor_path: Path | None,
    report_sha256: str | None,
) -> Path:
    rows = [_fake_row(i, date) for i in range(row_count)]
    subset = [
        {"id": r["id"], "content_hash": r["content_hash"], "recorded_at": r["recorded_at"]}
        for r in rows
    ]
    salt = _salt_for(date)
    prev_hash = (
        hashlib.sha256(prev_anchor_path.read_bytes()).hexdigest() if prev_anchor_path else None
    )
    payload = verify.canonical_day_payload(subset, models, prev_hash, report_sha256, date)
    anchor = {
        "chain_id": verify.CHAIN_ID,
        "anchor_date": date,
        "manifest_schema_version": 1,
        "manifest_hash": verify.manifest_hash(payload, salt),
        "prev_anchor_hash": prev_hash,
        "report_sha256": report_sha256,
        "prediction_count": len(rows),
        "new_model_count": len(models),
        "salted": True,
        "hash_algorithm": verify.HASH_ALGORITHM,
        "published_at": f"{date}T14:00:00+00:00",
        "sample": True,
        "_note": "Synthetic fixture — never a production anchor.",
    }
    _write_json(_SAMPLE / "anchors" / f"{date}.json", anchor)
    _write_json(_SAMPLE / f"predictions_full_{date}.json", rows)
    _write_json(_SAMPLE / f"predictions_subset_{date}.json", subset)
    _write_json(_SAMPLE / f"models_{date}.json", models)
    (_SAMPLE / f"salt_{date}.hex").write_text(salt.hex() + "\n", encoding="utf-8")
    return _SAMPLE / "anchors" / f"{date}.json"


def _write_rekor_fixture(anchor_path: Path, log_index: int) -> None:
    """A synthetic transparency-log record for the sample chain.

    Mode E checks the BINDING — that a .rekor record describes the anchor beside
    it — and deliberately never checks signatures (see SPEC/attestation.md), so a
    synthetic record exercises the mode completely. Without these fixtures the CI
    step passes vacuously on an empty anchors/ and the mode ships untested, which
    is not a state this repository gets to be in.

    Signature and key bytes are obvious placeholders: no sample artifact is ever
    submitted to the real log, and nothing here is a production attestation.
    """
    anchor = json.loads(anchor_path.read_text())
    published = datetime.strptime(anchor["published_at"], "%Y-%m-%dT%H:%M:%S+00:00")
    integrated = published + timedelta(seconds=7)
    record = {
        "log_index": log_index,
        "entry_uuid": hashlib.sha256(anchor_path.name.encode()).hexdigest(),
        "integrated_time": integrated.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "log_id": hashlib.sha256(b"sample-log").hexdigest(),
        "artifact_sha256": hashlib.sha256(anchor_path.read_bytes()).hexdigest(),
        "signature": base64.b64encode(b"sample-signature-not-a-real-attestation").decode(),
        "public_key": base64.b64encode(b"sample-public-key-not-a-real-key").decode(),
        "sample": True,
    }
    _write_json(anchor_path.with_suffix(".json.rekor"), record)


def main() -> None:
    day1 = "2099-01-01"
    day2 = "2099-01-02"

    report = {
        "report_date": day1,
        "report_schema_version": 1,
        "scope": "bets-only",
        "metrics": {"overall": {"hit_rate": "0.6100", "brier": "0.2210", "n": 41}},
        "published_at": f"{day1}T11:30:00+00:00",
        "sample": True,
    }
    report_path = _SAMPLE / "reports" / f"{day1}.json"
    _write_json(report_path, report)
    report_sha = hashlib.sha256(report_path.read_bytes()).hexdigest()

    models_day1 = [
        {
            "model_id": "2099_2100_mlb_pb_gamewinner",
            "artifact_sha256": hashlib.sha256(b"sample-artifact-1").hexdigest(),
            "recorded_at": f"{day1}T09:00:00+00:00",
        }
    ]
    anchor1 = _build_day(day1, 6, models_day1, None, None)
    anchor2 = _build_day(day2, 4, [], anchor1, report_sha)
    # Written after the anchors exist: a .rekor binds the anchor's final bytes,
    # so generating it earlier would bind a file that no longer matches.
    _write_rekor_fixture(anchor1, 1)
    _write_rekor_fixture(anchor2, 2)

    # Golden vectors — freeze the canonical encodings.
    row = _fake_row(0, day1)
    _write_json(
        _VECTORS / "row_classification_v1.json",
        {"kind": "row", "row": row, "expected_content_hash": row["content_hash"]},
    )
    subset = json.loads((_SAMPLE / f"predictions_subset_{day1}.json").read_text())
    payload = verify.canonical_day_payload(subset, models_day1, None, None, day1)
    salt = _salt_for(day1)
    _write_json(
        _VECTORS / "day_manifest_v1.json",
        {
            "kind": "day_manifest",
            "anchor_date": day1,
            "predictions": subset,
            "new_models": models_day1,
            "prev_anchor_hash": None,
            "report_sha256": None,
            "salt_hex": salt.hex(),
            "expected_manifest_hash": verify.manifest_hash(payload, salt),
        },
    )
    print("Wrote two-day sample chain + golden vectors")
    print(f"  day1 anchor: {anchor1.name}  report bound into day2: {report_sha[:16]}…")


if __name__ == "__main__":
    main()
