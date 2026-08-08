# KEYS — anchor signing public keys

The public half of every key that has ever signed an anchor file. Append-only:
a rotated key stays here forever, because entries it signed stay checkable
forever.

| File | In use from | Notes |
|---|---|---|
| `anchor-signing.pub` | (pending — generated before the first anchor) | ed25519, current |

The private half lives in the same custody as the day salts and is never
committed here, logged, or released. Rotation procedure and compromise posture:
[`../SPEC/attestation.md`](../SPEC/attestation.md).
