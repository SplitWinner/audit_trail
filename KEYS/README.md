# KEYS — anchor signing public keys

The public half of every key that has ever signed an anchor file. Append-only:
a rotated key stays here forever, because entries it signed stay checkable
forever.

| File | In use from | Notes |
|---|---|---|
| `anchor-signing.pub` | 2026-08-08 | ECDSA P-256, current |

ECDSA P-256 with SHA-256, because that is what Rekor's `hashedrekord` accepts while
keeping the logged digest equal to the anchor file's own sha256 — see the spec for the
tested rejection of the alternative.

The private half lives in the same custody as the day salts and is never
committed here, logged, or released. Rotation procedure and compromise posture:
[`../SPEC/attestation.md`](../SPEC/attestation.md).
