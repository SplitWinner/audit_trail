# Attestation — the two independent roots

Every anchor file is attested twice, into infrastructures that fail in unrelated ways:

| Root | Mechanism | Trust basis | Latency | Adds |
|---|---|---|---|---|
| **Bitcoin** | OpenTimestamps `.ots` proof | proof-of-work | hours to days | existence no later than a block |
| **Transparency log** | Sigstore Rekor entry | append-only Merkle log + operator key, third-party monitored | seconds | inclusion at a signed time, and **attribution** |

Neither is a fallback for the other; both are produced for every anchor. A reader may
check either, or both, and reach the same conclusion about when the anchor existed.

## Why two

A single attestation path is a single point of failure, and the failure modes here are
genuinely different. Bitcoin attestation depends on calendar servers being willing to
submit and on the chain being reachable; a transparency log depends on an operator's
signing key and on monitors watching for split views. A break in one says nothing about
the other. For a reader whose job is diligence, "two roots, independently checkable"
is a materially different claim than "one root, plus a plan."

Rekor also supplies something Bitcoin alone does not: **attribution**. An OTS proof
shows a hash existed by a block; it does not say who published it. A Rekor entry
carries a signature over the anchor bytes by a key whose public half is published in
this repository, so a reader can verify not only *when* an anchor existed but *that
this operator issued it*. Both properties matter to a counterparty; only together do
they answer "who committed to this, and when."

## What is attested, and what is never inside the hashes

The attested object is the **anchor file's bytes** — the same sha256 that becomes the
next day's `prev_anchor_hash`. Both attestations are produced *after* those bytes
exist, and therefore live **outside** every hashed structure, exactly as the verifier's
own hash does ([`README.md`](./README.md), invariant 1).

An attestation identifier is never written into the anchor file it attests. Doing so
would require knowing the identifier before computing the bytes that produce it — a
circular dependency that would make the chain unverifiable. Attestations are siblings
of the anchor, not contents of it.

## Artifacts

```
anchors/YYYY-MM-DD.json         the anchor file — hashed into the next day's chain link
anchors/YYYY-MM-DD.json.ots     OpenTimestamps proof over those bytes
anchors/YYYY-MM-DD.json.rekor   Rekor entry record over those bytes
```

The `.rekor` file is JSON and records what a reader needs to locate and check the entry
without trusting this repository:

```
{
  "log_index":       <integer, the entry's position in the log>,
  "entry_uuid":      "<hex>",
  "integrated_time": "YYYY-MM-DDTHH:MM:SS+00:00",
  "log_id":          "<hex, the log's key fingerprint>",
  "artifact_sha256": "<the anchor file's sha256 — must equal the file it sits beside>",
  "signature":       "<base64, over the anchor file bytes>",
  "public_key":      "<base64, the anchor signing key's public half>"
}
```

`artifact_sha256` is the binding a reader checks first: it must equal the sha256 of the
anchor file in the same directory. A `.rekor` file whose binding disagrees with its
anchor is a failure, not a discrepancy to reconcile.

## The anchor signing key

One long-lived **ECDSA P-256** keypair signs anchor files, with SHA-256 as the digest.
That combination is not a preference — it is what Rekor's `hashedrekord` verifier
accepts while keeping the logged artifact hash identical to the anchor file's sha256.
ed25519 was tested first and rejected by the log (`unsupported hash algorithm:
"SHA-256" not in [SHA-512]`); signing ed25519 over SHA-512 would have logged a digest
that does not equal the anchor's identity hash, breaking the binding this whole layer
depends on. The public half is committed at
[`../KEYS/anchor-signing.pub`](../KEYS/anchor-signing.pub); the private half lives in
the same custody as the day salts ([`../OPERATIONS.md`](../OPERATIONS.md)).

Rotation is additive and never retroactive: a new public key is appended to the KEYS
directory with the date from which it applies, the previous key remains published
forever so historical entries stay checkable, and the rotation is an incident-log
event. A key rotation does not re-sign past anchors — those keep the signature they
were issued with, which is the whole point of publishing superseded keys.

A compromised signing key would let an attacker produce entries that *look* like this
operator's. It would not let them alter a published anchor, insert a day into the
chain, or forge a Bitcoin attestation — which is why the chain's integrity does not
rest on this key, and why the key's compromise is a disclosure event rather than a
catastrophe.

## Verification

`verify.py` stays dependency-free and therefore does **not** check signatures — no
Python standard library ships signature verification, and adding a cryptography
dependency would cost the property that the whole ledger can be checked with one file
of stdlib Python. Instead the modes split by what each can honestly do:

- `verify.py rekor` — structural: every anchor has a `.rekor` sibling, its
  `artifact_sha256` equals the anchor file's actual digest, its fields are well-formed,
  and its `integrated_time` is not earlier than the anchor's `published_at`. Pure
  stdlib, offline, no network.
- `rekor-cli verify --artifact anchors/<date>.json --signature … --pki-format …` —
  cryptographic: the signature and the log inclusion proof. External tooling, the same
  arrangement as `ots` for Bitcoin ([`../requirements-bitcoin.txt`](../requirements-bitcoin.txt)).

This mirrors Mode C exactly: the stdlib verifier proves the binding, and a specialist
tool proves the cryptography. A reader who runs only `verify.py` learns that the
repository is internally consistent; a reader who runs both external checks learns that
two independent infrastructures agree about when these bytes existed.

## When a root is unavailable

Anchoring never blocks on attestation. If either path is unavailable, the anchor file
is still written, committed, and chained — the ledger's integrity properties do not
depend on either root being reachable at publication time. The missing attestation is
produced when the path returns, and the delay is disclosed under the incident
thresholds in [`../OPERATIONS.md`](../OPERATIONS.md).

Attestations already obtained are unaffected by any later outage. A confirmed Bitcoin
proof lives in the blockchain, not in a calendar server; a Rekor inclusion proof is
checkable against a signed tree head that monitors retain independently of the log
operator.
