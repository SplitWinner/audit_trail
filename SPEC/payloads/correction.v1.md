# payload_schema: `correction.v1`

Registered 2026-08-08. The supersession record: the only sanctioned way to say that an
already-anchored row is wrong.

A row declaring `"payload_schema": "correction.v1"` hashes exactly these fields, in
canonical serialization ([`../canonicalization.md`](../canonicalization.md)), plus the
`payload_schema` declaration itself:

```
supersedes_content_hash · supersedes_id · reason_code · note · corrected_content_hash
```

## Why this exists

An append-only ledger cannot delete. Without a defined way to mark a row superseded,
the first bad row — a duplicate write, a prediction attached to the wrong game, a
price captured from a malformed scrape — creates pressure to do the one thing that
destroys the ledger's meaning: edit history. That failure happened once, in the alpha
(see the sealed alpha repo's `ALPHA.md`). This schema makes the honest response
cheaper than the dishonest one.

A correction **never removes anything**. The original row keeps its hash, its anchor,
and its Bitcoin attestation forever. The correction is a new row in a later day's
manifest that points at the original and states what was wrong with it. Both are
permanently visible; a reader following the chain sees the error and the acknowledgment
in the order they happened.

## Fields

- **`supersedes_content_hash`** — the `content_hash` of the row being corrected. The
  anchor containing it is already published; this value is what ties the correction to
  it unambiguously.
- **`supersedes_id`** — the superseded row's ledger `id`, carried so a reader can
  locate the row without scanning every prior manifest.
- **`reason_code`** — closed vocabulary, extended only by registering a new version of
  this schema:
  - `duplicate` — the same prediction was written more than once.
  - `wrong_event` — the row was attached to the wrong game.
  - `bad_input` — a source value was malformed or misparsed (for example a price
    captured from a broken feed response).
  - `void_event` — the event did not occur or was abandoned such that no settlement is
    possible. Prefer [`void.v1`](./void.v1.md), which records the disposition; use this
    code only when the row itself should not have existed.
  - `operator_error` — anything else, requiring a `note` that says plainly what
    happened.
- **`note`** — free text, required, in the operator's own words. A correction with an
  empty note is not a correction; it is a hash pointing at a hash.
- **`corrected_content_hash`** — the `content_hash` of the replacement row when one
  exists, or `null` when the original is withdrawn with no replacement. A replacement
  is an ordinary row of its own payload type, anchored normally; this field only links
  the two.

## Rules

1. A correction is anchored on the day it is written, never backdated into the day it
   corrects. The gap between the two anchors is part of the record.
2. A correction may itself be corrected. Chains are permitted and readable; nothing is
   collapsed.
3. Publishing a correction is an incident-log event under the thresholds in
   [`../OPERATIONS.md`](../OPERATIONS.md) whenever it changes a figure already
   published in a bound report.
4. Metrics computed from the ledger must apply corrections — a reader who ignores them
   sees the pre-correction record, which is why both are published rather than one.

Golden vector: [`../vectors/row_correction_v1.json`](../vectors/row_correction_v1.json).
