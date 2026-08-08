# Methodology — what this ledger proves and how

## What is proven

1. **Existence in time, twice.** Each day's anchor is attested into two independent
   roots ([`SPEC/attestation.md`](./SPEC/attestation.md)): a Bitcoin timestamp via
   OpenTimestamps, and a Sigstore Rekor transparency-log entry. A prediction covered by
   an anchor demonstrably existed no later than that anchor's Bitcoin block and no later
   than its log inclusion — independent of git, GitHub, or SplitWinner itself, and
   independent of each other. Neither root can be checked away by the failure of the
   other.
2. **Attribution.** The Rekor entry carries a signature over the anchor's bytes by a key
   whose public half is published in [`KEYS/`](./KEYS/). A reader verifies not only when
   an anchor existed but that this operator issued it — a property a timestamp alone
   does not provide.
3. **Integrity.** Ledger rows are hashed at write time; the day manifest covers every
   row; the anchor chain covers every day. Any after-the-fact edit breaks a hash
   someone else can check.
4. **Continuity.** Each anchor commits to the previous anchor's file bytes
   (`prev_anchor_hash`), so the sequence of days is itself tamper-evident, and gaps are
   visible rather than erasable.
5. **Performance claims.** Each daily report's bytes are bound into the next anchor
   (`report_sha256`) — published metrics inherit the same Bitcoin timestamps as the
   predictions they describe.

## What is not proven

- That the predictions are good. The ledger is provenance, not endorsement.
- Anything about *how* predictions are made — features, architectures, training data.
  The ledger records outputs (see the payload schemas' `line_source` note: predictions
  name the market they priced against; training lineage is never in a row).

**Proof basis, stated plainly:** the `.ots` Bitcoin attestations are the evidence. Git
and GitHub timestamps are corroboration only, and this repository's guarantees never
rest on them.

## The daily protocol

1. Predictions are written to the immutable database ledger as they are made
   (append-only; UPDATE/DELETE rejected by trigger; one row per prediction enforced by
   uniqueness). Each row's `content_hash` covers its typed payload
   ([`SPEC/payloads/`](./SPEC/payloads/)).
2. At anchor time the day's `(id, content_hash, recorded_at)` triples, any new model
   registrations, the previous anchor's file hash, and the bound report hash are
   canonically serialized ([`SPEC/canonicalization.md`](./SPEC/canonicalization.md))
   and sealed under a fresh 32-byte salt: `manifest_hash = HMAC-SHA256(salt, payload)`.
3. The anchor file is committed here, signed and submitted to Rekor within seconds, and
   stamped with OpenTimestamps; the Bitcoin proof is upgraded to a confirmed attestation
   on the following days. Both attestation records sit beside the anchor as siblings —
   never inside it, since an identifier cannot be part of the bytes that produce it.
4. Salts stay private and are released to customers under contract — the salt prevents
   dictionary reconstruction of picks from the public manifest while allowing full
   verification by anyone holding the data. Mode B (`content`) needs no salt.

## Model registrations

Models enter the ledger as `{model_id, artifact_sha256, recorded_at}`;
`artifact_sha256` is a Merkle-style digest over the artifact's file contents
(archive-format independent). Public model files disclose registration facts only —
never hyperparameters, storage locations, or feature information. Model IDs follow a
fixed naming grammar and deliberately encode no architecture.

## Versioning

- `manifest_schema_version` (currently **1**) governs the day-manifest payload.
- `payload_schema` (currently `classification.v1`) governs each row type; new
  prediction types — margin of victory, totals, spreads, per-book variants — register
  new payload schemas without touching the manifest layer or existing rows.
- All changes are **forward-only**: a published anchor or row is never rewritten to a
  newer schema. The registry and its history live in [`SPEC/`](./SPEC/).
