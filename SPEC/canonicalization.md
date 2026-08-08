# Canonicalization — byte-level rules

Every hash in this ledger is computed over bytes produced by exactly these rules. A
conforming implementation in any language must reproduce them byte-for-byte; the golden
vectors in [`vectors/`](./vectors/) are the conformance test.

## JSON serialization

1. Object keys sorted lexicographically (Unicode code-point order), at every depth.
2. Compact separators: `,` between items, `:` between key and value — no whitespace.
3. Non-ASCII characters escaped as `\uXXXX` (ASCII-only output), then encoded UTF-8.
4. **No implicit coercion.** A value that JSON cannot represent is an error, never a
   silent `str()` conversion. Non-finite floats (`NaN`, `Infinity`) are rejected.
5. Numeric-valued *measurements* (lines, juice, probabilities, edges, stakes) are
   serialized by the writer as **fixed-precision decimal strings** (e.g. `"0.6400"`,
   `"-110"`), so canonical bytes never depend on any language's float formatting.
   Structural integers (counts, set sizes, schema versions) remain JSON numbers.
6. **Timestamps** are strings in exactly one form: `YYYY-MM-DDTHH:MM:SS+00:00`.
   UTC always, offset written as `+00:00` and never `Z`, seconds always present and
   never fractional — a sub-second component is truncated (not rounded) by the writer
   before serialization. A timestamp carrying any other offset is converted to UTC
   first. This rule exists because databases and language runtimes disagree freely
   about timestamp rendering: Postgres will return microseconds on one row and none on
   the next, and most ISO-8601 libraries emit `Z`. Either variation changes the bytes
   and therefore the hash for otherwise identical data, which would break the promise
   that a conforming implementation in any language reproduces these digests.
   Applies to every hashed timestamp — `recorded_at`, `game_time`, and any added by a
   future payload schema.
7. **Dates** (`anchor_date`, `date_event`) are `YYYY-MM-DD` and are calendar dates in
   **UTC**, matching the anchor's UTC coverage window described in
   [`../OPERATIONS.md`](../OPERATIONS.md). A row belongs to the anchor day whose UTC
   window contains its `recorded_at`. Sport-local conventions — the 5 AM ET sports day
   the product uses elsewhere — never determine ledger membership.

## Row content hash

`content_hash = sha256(canonical(projection ∪ {"payload_schema": <name>}))` where the
projection takes exactly the fields listed in the row's payload schema (missing fields
serialize as `null`). See [`payloads/`](./payloads/).

## Day manifest hash

```
payload = canonical({
  "chain_id":         "splitwinner-official-2026",
  "anchor_date":      "YYYY-MM-DD",
  "predictions":      [{id, content_hash, recorded_at}…]  sorted by (content_hash, id),
  "new_models":       [{model_id, artifact_sha256, recorded_at}…] sorted by model_id,
  "prev_anchor_hash": sha256 of the previous anchor FILE bytes (null for genesis),
  "report_sha256":    sha256 of the bound daily report file (null if none),
})
manifest_hash = HMAC-SHA256(key = salt, message = payload)
```

The sort tie-break `(content_hash, id)` makes ordering fully deterministic even for
identical hashes. The salt is 32 random bytes, generated per day, stored privately,
written as exactly 64 lowercase hex characters wherever it is exchanged — no other
encoding is accepted.

## What is deliberately outside the hashes

The anchor file's human-readable fields (counts, policy block, timestamps) — they are
*disclosed* by the anchor and bound transitively by the next day's `prev_anchor_hash`
over the whole file, but the manifest hash itself covers only the payload above.
