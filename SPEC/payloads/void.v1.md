# payload_schema: `void.v1`

Registered 2026-08-08. The disposition record for a prediction whose event never
produced a result.

A row declaring `"payload_schema": "void.v1"` hashes exactly these fields, in canonical
serialization ([`../canonicalization.md`](../canonicalization.md)), plus the
`payload_schema` declaration itself:

```
voids_content_hash · voids_id · disposition · effective_at · note
```

## Why this exists

A prediction is anchored before the event. Sometimes the event never happens — a game
is postponed past its scheduled date, abandoned mid-play, or cancelled outright — and
sometimes it happens but the market the row priced against is not settleable, as when
a starting pitcher change voids action.

Without a record, that prediction is permanently ambiguous to anyone computing
performance from the ledger plus public results: they cannot tell "no result" from
"result we would rather not count," and the difference between those two readings is
exactly the kind of thing a vendor could exploit silently. Closing-line value has the
same problem — there is no closing market to price against for an event that never
ran.

A void is **not** a correction. The prediction was legitimate when it was made; the
world changed afterward. Corrections say *we were wrong*; voids say *the event did not
resolve*. Conflating them would let a bad prediction hide behind a weather report,
which is why they are separate schemas with separate vocabularies.

## Fields

- **`voids_content_hash`** — the `content_hash` of the prediction row being voided.
- **`voids_id`** — that row's ledger `id`.
- **`disposition`** — closed vocabulary:
  - `postponed` — rescheduled beyond its original date. The prediction does not carry
    forward to the new date; a fresh prediction, if any, is an ordinary new row.
  - `cancelled` — the event will not be played.
  - `abandoned` — started, then stopped without an official result.
  - `no_action` — played and resolved, but the specific market did not settle (a
    pitcher change, a scratched participant, a market pulled before close).
- **`effective_at`** — the timestamp at which the voiding fact became known to the
  operator, canonical form per the timestamp rule. Not the moment the event was
  scheduled; the moment it became knowable that it would not resolve.
- **`note`** — free text, required. What happened, in plain words.

## Rules

1. A voided prediction is **excluded from win/loss and from CLV**, and included in
   disclosed counts. Reports state void counts alongside settled counts rather than
   quietly reducing the denominator.
2. Voids are anchored on the day they are written. Like every other row, the delay
   between the event and its void record is visible.
3. A void never deletes or alters the prediction. Both rows stand.
4. Voiding is not a way to drop a losing pick. A row voided for a reason that is not
   independently checkable against public information is an incident-log event under
   [`../OPERATIONS.md`](../OPERATIONS.md).

Golden vector: [`../vectors/row_void_v1.json`](../vectors/row_void_v1.json).
