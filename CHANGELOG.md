# Changelog

## 2.0.0 — 2026-08-06

Founding release of the official SplitWinner ledger. Protocol redesigned from the
public alpha (sealed at `SplitWinner/audit_trail_alpha`; findings in its `ALPHA.md`):

- **One verifier, forever**: the verifier hash left the anchored payload; releases are
  registered in `SPEC/VERIFIERS.md`; CI re-verifies the full published corpus on every
  change, so verifier improvements can never fork the chain.
- **Chained days**: `prev_anchor_hash` links every anchor to the previous anchor's
  exact bytes — tamper-evident order, self-documenting gaps.
- **Reports bound in**: each daily report's sha256 is folded into the next anchor, so
  performance claims inherit the Bitcoin timestamps.
- **Typed row payloads**: rows declare `payload_schema` (founding: `classification.v1`);
  new prediction types register forward-only schemas without touching the manifest
  layer or history.
- **Canonicalization as a spec**: byte-level rules + golden vectors
  (`SPEC/canonicalization.md`, `SPEC/vectors/`), fixed-precision string numerics,
  deterministic tie-broken ordering, no implicit coercion.
- **HMAC-SHA256 salted manifests**; salts strictly 64-hex.
- **Offline Bitcoin mode checks the digest binding** (or says it cannot), fixing the
  alpha's misleading `--offline` output.
- **Hardened CI**: nested-path append-only guard that fails loudly instead of
  skipping, corpus verification, verifier-registry check, `CODEOWNERS`.

The chain opens with its first official anchor (MLB; other sports join at their 2026
season starts). Nothing from the alpha chain carries into this one.
