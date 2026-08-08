# Verifier release registry — append-only

The verifier's identity lives here, not inside anchors. Each row records a release of
`verify.py`; the current release must verify **every** anchor, schema, and vector ever
published on this chain (CI-enforced). Confirm what you're running:

```bash
python3 verify.py --version
```

| Version | Date | sha256 of `verify.py` | Changes |
|---|---|---|---|
| 2.0.0 | 2026-08-06 | `2a90230126117bb3ec17a39b75f9a3fbacb62c94b8eff039479ae08ebee2244f` | Founding release of the official-ledger verifier: type-blind day manifests with `prev_anchor_hash` chaining and `report_sha256` binding, HMAC-SHA256 salted manifests, typed row payload registry (`classification.v1`), chain mode, offline Bitcoin mode with real digest binding, golden-vector self-test. Redesign rationale: the sealed alpha (`audit_trail_alpha`, `ALPHA.md`). |
| 2.1.0 | 2026-08-08 | `043c36eefd245d18f6cf29412018789fcd2acac7bebeaea3f39b8b451fe717a8` | Adds Mode E (`rekor`): structural verification that each anchor's `.rekor` record binds that anchor's bytes, with a 300s clock-skew tolerance on the integrated-time ordering. Registers the `correction.v1` and `void.v1` payload schemas. No change to any existing hash, canonical form, or mode — 2.0.0's artifacts verify identically under 2.1.0. |
