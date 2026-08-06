# Integrity — the invariants

1. **Ledger artifacts are append-only.** Files under `anchors/`, `models/`, and
   `reports/` are added, never modified, renamed, or deleted. `.ots` proofs may be
   modified in place only to upgrade a pending attestation to a Bitcoin-confirmed one —
   never deleted or renamed.
2. **History is never rewritten.** `main` is linear, branch-protected, and this
   repository is never force-pushed. (Anywhere else that may be a housekeeping habit;
   here it is a violation.)
3. **One verifier verifies the whole chain.** `verify.py`'s hash is not part of any
   anchored payload; releases are registered in
   [`SPEC/VERIFIERS.md`](./SPEC/VERIFIERS.md). Any change to the verifier must keep
   every published anchor, payload schema, and golden vector passing — CI runs that
   corpus on every push and pull request, so a chain-breaking change cannot merge.
4. **Schemas are forward-only.** New manifest or payload schema versions apply from
   their registration date; published artifacts are never migrated. (The alpha violated
   this once — `audit_trail_alpha/ALPHA.md` — which is why it is now mechanical.)
5. **The SPEC registry is append-only** — canonicalization rules, payload schemas,
   vectors, and verifier releases accumulate; they are never edited in place.

## Enforcement

- **Cryptography**: row hashes, salted HMAC manifests, `prev_anchor_hash` chaining,
  Bitcoin attestations — anyone can check; nothing depends on trusting this repo's host.
- **Database**: the ledger tables reject UPDATE/DELETE by trigger and enforce one row
  per prediction by uniqueness; the DDL is version-controlled with the pipeline.
- **CI** (`.github/workflows/integrity.yml`): an append-only guard on every push/PR
  (nested-path aware; a push it cannot evaluate fails loudly instead of skipping) and
  the full verification corpus (`vectors`, `chain`, sample anchors, and every published
  anchor's schema acceptance).
- **Process**: branch protection with required checks, `CODEOWNERS` on `verify.py` and
  `SPEC/`, and the incident policy in [`incidents/`](./incidents/) — anything that
  alters the semantics of past verifications is disclosable within seven days.
