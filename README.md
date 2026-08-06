# SplitWinner audit_trail — the official ledger

Every SplitWinner prediction is hashed into an immutable database ledger the moment it
is made, and each day's ledger is sealed into a salted manifest, chained to the
previous day, and timestamped into the **Bitcoin blockchain** via OpenTimestamps —
before games settle. This repository is the public half of that system: the anchors,
the proofs, and a single-file verifier anyone can run.

**Receipts, never the recipe.** The ledger proves *when* predictions existed and that
they were never altered. It does not expose how they are made.

## Verify it

```bash
git clone https://github.com/SplitWinner/audit_trail.git
cd audit_trail

python3 verify.py vectors                 # self-test against the golden vectors
python3 verify.py chain                   # walk the prev_anchor_hash links
python3 verify.py bitcoin                 # check Bitcoin attestations (needs `ots`)
python3 verify.py anchor --date …         # recompute a day (contract holders: rows + salt)
python3 verify.py content --predictions … # recompute per-row hashes from full rows
```

Modes `vectors`, `chain`, `anchor`, and `content` are pure standard library with no
network access. `bitcoin` uses the pinned OpenTimestamps client
(`pip install -r requirements-bitcoin.txt`); its online form is the binding check.

## How it fits together

- [`SPEC/`](./SPEC/) — the append-only registry: canonicalization rules, payload
  schemas, golden vectors, verifier releases. Start with [`SPEC/README.md`](./SPEC/README.md).
- [`METHODOLOGY.md`](./METHODOLOGY.md) — what is proven, what is not, and the daily protocol.
- [`INTEGRITY.md`](./INTEGRITY.md) — the invariants and how they are enforced.
- [`OPERATIONS.md`](./OPERATIONS.md) — the operational reality, including its limits.
- [`incidents/`](./incidents/) — the disclosure log. Anything that alters the meaning
  of this record is written down here within seven days of detection.

## The record

**This chain opens with its first official anchor** — MLB first, other sports joining
as their 2026 seasons begin. The system's public alpha (2026-05-19 → 2026-06-25, run
under the product's previous name) is preserved verbatim and sealed at
[`SplitWinner/audit_trail_alpha`](https://github.com/SplitWinner/audit_trail_alpha);
its lessons are why this protocol looks the way it does. The gap between alpha and
official is a stated fact, not a smoothed-over one.
