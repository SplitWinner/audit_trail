#!/usr/bin/env python3
"""CI guard: ledger artifacts are append-only. Fails loudly, never skips.

Rules (INTEGRITY.md invariants 1 and 5):
  * anchors/ models/ reports/ — any *.json at ANY depth: additions only.
  * *.ots under those trees: may be modified in place (OTS upgrade), never
    deleted/renamed/copied-over.
  * SPEC/vectors/*.json and SPEC/payloads/*: additions only.
  * verify.py: non-add changes emit a warning (the corpus job is the hard
    gate — a verifier change that breaks any published artifact fails there).

A diff range this script cannot evaluate is an ERROR, not a skip — silence
must never look like a pass.
"""

from __future__ import annotations

import os
import subprocess
import sys

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # git's canonical empty tree
APPEND_ONLY_DIRS = ("anchors/", "models/", "reports/")
APPEND_ONLY_SPEC = ("SPEC/vectors/", "SPEC/payloads/")


def changed_files(base: str, head: str) -> list[tuple[str, list[str]]]:
    out = subprocess.run(
        ["git", "diff", "--name-status", "-M", "-C", f"{base}..{head}"],
        capture_output=True, text=True, check=True,
    ).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        rows.append((parts[0], parts[1:]))
    return rows


def is_append_only(path: str) -> bool:
    if path.endswith(".json") and path.startswith(APPEND_ONLY_DIRS):
        return True
    return path.startswith(APPEND_ONLY_SPEC)


def is_ots(path: str) -> bool:
    return path.endswith(".ots") and path.startswith(APPEND_ONLY_DIRS)


def main() -> int:
    base = os.environ.get("BASE_SHA", "")
    head = os.environ.get("HEAD_SHA", "HEAD")
    if not base or set(base) == {"0"}:
        # First push to a branch: evaluate the full tree against the empty tree
        # rather than silently skipping.
        base = EMPTY_TREE
    violations: list[str] = []
    warnings: list[str] = []
    for status, paths in changed_files(base, head):
        code = status[0]
        for path in paths:
            if is_append_only(path) and code != "A":
                violations.append(f"{status}\t{path}  (append-only: additions only)")
            if is_ots(path) and code in ("D", "R", "C"):
                violations.append(f"{status}\t{path}  (.ots may be upgraded, never removed)")
            if path == "verify.py" and code != "A":
                warnings.append(
                    "verify.py changed — the verify-corpus job is the hard gate; "
                    "register the release in SPEC/VERIFIERS.md"
                )
    for warning in sorted(set(warnings)):
        print(f"::warning::{warning}")
    if violations:
        print("::error::append-only violation(s):")
        for violation in violations:
            print(f"::error::  {violation}")
        return 1
    print("append-only guard: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
