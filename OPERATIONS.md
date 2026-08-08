# Operations — the honest version

This ledger is operated by a single operator. That is a real limitation and the
mitigations below are disclosed rather than hidden.

## Cadence

- **Anchor**: once per day after the morning prediction run; the anchor covers the
  day's UTC window of ledger writes. A gap of more than 24 hours between ledger
  activity and its anchor is a disclosable event (see thresholds below).
- **Report**: daily, bets-only scope stated in the report payload itself
  (`report_schema_version` 1); each report's bytes are bound into the next anchor.
- **Attestation**: every anchor is attested into two independent roots
  ([`SPEC/attestation.md`](./SPEC/attestation.md)) — a Sigstore Rekor transparency-log
  entry, signed and written within seconds of publication, and an OpenTimestamps proof
  upgraded to a Bitcoin-confirmed attestation over the following days. Both are
  produced for every anchor; neither is a fallback for the other.
- **OTS upgrade**: daily; pending calendar attestations are upgraded in place to
  Bitcoin-confirmed proofs.

## Incident thresholds — an `incidents/` entry is required when

- an anchor lands more than 24 hours after the ledger activity it covers;
- an anchor carries only one of its two attestations for more than 72 hours;
- the anchor signing key is rotated, or is suspected to have left custody;
- any committed ledger artifact (anchor, model file, report) changes after commit;
- a verifier release alters the semantics of any past verification;
- a salt leaves custody outside a customer contract;
- any verifier mode fails against a published artifact for a non-transient reason.

Entries follow [`incidents/README.md`](./incidents/README.md): within seven days of
detection, append-only, no silent edits.

## Single-operator disclosures

- The operator holds the keys: database service role, the anchor-publishing
  credential, and the salt store. An operator with those keys could, in principle,
  disable database triggers, rewrite rows, and re-enable them. The mitigations are the
  parts the operator *cannot* rewrite: Bitcoin attestations already published, the
  anchor chain in customers' clones, and the disclosure record.
- Anchoring is code, not ceremony: publication is automated; the operator's manual
  surface is starting and stopping it. Pauses are visible as chain gaps and are
  disclosed, not backfilled — **a stale day is never anchored late as if it were live**.
- Salt custody: per-day salts live in the private database alongside the anchors
  table; released under contract; never logged, never committed here. A salt is
  unrecoverable if lost — losing one permanently forecloses manifest-mode verification
  for that day, though content mode and the Bitcoin attestation are unaffected. Salts
  are covered by the database's zero-loss objective below; there is no second copy
  elsewhere, because a second copy is a second thing to leak.
- Attestation dependencies, stated precisely. Bitcoin proof is obtained through
  OpenTimestamps, which is not one server: the client submits to four calendars run by
  three independent operators, so a single operator disappearing does not interrupt
  attestation. Transparency-log proof is obtained from Sigstore Rekor, operated by the
  Linux Foundation and monitored by third parties. Both are infrastructure this ledger
  does not control, which is exactly why there are two of them with unrelated failure
  modes. If either becomes unavailable, anchoring and publication continue unchanged —
  the chain's integrity does not depend on attestation being reachable at publication
  time — and the affected anchors carry one root until the other returns, disclosable
  under the thresholds above. Attestations already obtained are unaffected by any later
  outage: a confirmed Bitcoin proof lives in the blockchain rather than in a calendar,
  and a Rekor inclusion proof checks against signed tree heads that monitors retain
  independently of the operator.
- Anchor signing key custody: one long-lived ed25519 key signs anchor files for the
  Rekor entry. The private half lives with the day salts under the same handling — never
  logged, never committed, released to no one. Public halves, including superseded ones,
  are published in [`KEYS/`](./KEYS/) forever so historical entries stay checkable. A
  compromised key would let an attacker mint entries that impersonate this operator; it
  would not let them alter a published anchor, insert a day into the chain, or forge a
  Bitcoin attestation.

## Recovery targets

Ledger data: zero-loss objective (the database is the primary; anchors are derived and
re-derivable for unanchored days only — an anchored day is immutable). Publication
pipeline: restore within 24 hours. A pipeline outage delays anchoring and is visible;
it never alters what was already anchored.
