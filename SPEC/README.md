# SPEC — the append-only registry of everything this ledger can attest

This directory is the single source of truth for the ledger's formats. Every file in it
is **append-only**: entries are added, never modified or removed. CI enforces it.

| File | Owns |
|---|---|
| [`canonicalization.md`](./canonicalization.md) | The byte-level serialization rules every hash in this repo is computed over |
| [`payloads/`](./payloads/) | Row payload schemas — one file per `payload_schema` value, added as new prediction types ship. Registered: `classification.v1` (predictions), `correction.v1` (supersession), `void.v1` (unresolved events) |
| [`vectors/`](./vectors/) | Golden vectors: known inputs → known digests. `verify.py vectors` must reproduce all of them; CI runs it on every push |
| [`attestation.md`](./attestation.md) | The two attestation roots — Bitcoin and transparency log — what each proves, artifact layout, key policy |
| [`VERIFIERS.md`](./VERIFIERS.md) | The verifier release registry: version, sha256, date, what changed |

## The two invariants the registry exists to protect

1. **One verifier verifies the whole chain, forever.** The verifier's hash is not part
   of any anchored payload. A change to `verify.py` must keep every published anchor,
   every payload schema, and every golden vector passing — CI re-verifies the corpus on
   every commit, so a change that breaks history cannot merge.
2. **Schemas are forward-only.** A new `manifest_schema_version` or `payload_schema`
   applies to new anchors and rows from its registration date onward. Published anchors
   and ledger rows are never rewritten to a new schema — that failure happened once in
   the alpha (see the sealed alpha repo's `ALPHA.md`) and is mechanically blocked here.

## Chain identity and succession

The chain is identified by `chain_id`, currently `splitwinner-official-2026`. The year
in that identifier names the chain's **origin**, not its expiry — this chain continues
across season and calendar boundaries and is not rotated annually. There is no
scheduled rollover, and a new year does not begin a new chain.

Should a successor chain ever become necessary — a cryptographic break in SHA-256, a
migration off Bitcoin attestation — it is created under these rules and no others:

- The successor's genesis anchor sets `prev_anchor_hash` to the sha256 of the
  **predecessor's final anchor file**, exactly as any other day does. Continuity is
  never severed; a chain boundary is a link, not a gap.
- The successor's anchor files carry `predecessor_chain_id` naming the chain they
  continue, so the sequence is walkable in both directions without external knowledge.
- The predecessor is sealed with a final anchor stating that it is final, and is never
  written to again.
- The transition is an incident-log event under [`../OPERATIONS.md`](../OPERATIONS.md).

Stating this now is deliberate: a successor chain whose genesis begins with a null
`prev_anchor_hash` would quietly discard every prior guarantee, and that is exactly the
shortcut a future operator under time pressure would reach for.

## Layer map

```
row payload   (typed: classification.v1, mov.v1, …)   → content_hash  (sha256)
day manifest  (type-blind: id/content_hash/recorded_at triples
               + prev_anchor_hash + report_sha256)     → manifest_hash (HMAC-SHA256, per-day salt)
anchor file   (public: hashes + counts + policy)       → sha256 chained into the next day
.ots proof    (per anchor file)                        → Bitcoin block attestation
.rekor record (per anchor file)                        → transparency-log inclusion + signature
```

The day manifest is deliberately **type-blind** — new prediction types (margin of
victory, totals, spreads, per-book variants) add payload schemas and never touch the
manifest layer, the chain, or the verifier's ability to check history.
