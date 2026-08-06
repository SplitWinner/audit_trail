# Operations — the honest version

This ledger is operated by a single operator. That is a real limitation and the
mitigations below are disclosed rather than hidden.

## Cadence

- **Anchor**: once per day after the morning prediction run; the anchor covers the
  day's UTC window of ledger writes. A gap of more than 24 hours between ledger
  activity and its anchor is a disclosable event (see thresholds below).
- **Report**: daily, bets-only scope stated in the report payload itself
  (`report_schema_version` 1); each report's bytes are bound into the next anchor.
- **OTS upgrade**: daily; pending calendar attestations are upgraded in place to
  Bitcoin-confirmed proofs.

## Incident thresholds — an `incidents/` entry is required when

- an anchor lands more than 24 hours after the ledger activity it covers;
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
  table; released under contract; never logged, never committed here.

## Recovery targets

Ledger data: zero-loss objective (the database is the primary; anchors are derived and
re-derivable for unanchored days only — an anchored day is immutable). Publication
pipeline: restore within 24 hours. A pipeline outage delays anchoring and is visible;
it never alters what was already anchored.
