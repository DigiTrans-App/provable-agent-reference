# Development DSSE signing and cross-language verification

PR D wraps exact canonical Assurance Packet bytes in the standard three-field DSSE envelope and signs DSSE v1 pre-authentication encoding with Ed25519.

## Security boundary

The signer is intentionally reproducible from a public label. Its private material is therefore public and is suitable only for synthetic interoperability tests. The pinned bundle at `trust/development-trust-bundle.json` explicitly limits the key to the `packet_issuer` role and development use. It must never authenticate production, customer, evidence-source, approver, or effect-executor records.

Trust metadata remains outside the envelope. Verification fails closed for an unknown key ID, wrong algorithm or role, disabled or revoked key, invalid verification-time window, malformed base64, noncanonical payload, packet-hash mismatch, or bad signature. A successful result does not establish trusted signing time and does not add `par.authenticated-records.v1`.

## Interoperability profile

- Payload type is fixed to `application/vnd.digitrans.provable-agent.assurance-packet+json;version=0.3.0-candidate.1`.
- Payload bytes are UTF-8 deterministic JSON with sorted object keys, no insignificant whitespace, and no floating-point values or integers outside JavaScript's safe range.
- Pre-authentication encoding is `DSSEv1 SP len(type) SP type SP len(payload) SP payload`, where lengths count bytes.
- The Python signer uses `cryptography`; the TypeScript verifier uses only Node's independent `node:crypto` implementation.

Run `python -m unittest tests.test_dsse -v`. The suite signs in Python, verifies in Python and TypeScript, and exercises signature, payload type, key, algorithm, role, status, and revocation failures.
