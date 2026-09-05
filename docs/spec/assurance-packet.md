# Assurance Packet candidate

Status: normative candidate for `0.3.0-candidate.1`.

An Assurance Packet is a portable, self-contained representation of one reconstructed,
authorized control chain.
Its JSON shape is defined by
[`assurance-packet.schema.json`](../../schemas/assurance-packet.schema.json).

## Required content

The packet contains:

- a protocol version and deterministic packet identifier;
- cumulative claimed conformance profiles;
- a `reconstructed` lifecycle state;
- the complete scoped evidence bundle;
- canonical candidate, verification, approval, authorization, and audit records;
- the exact authorized output, not merely its digest;
- explicit packet-level limitations;
- a creation timestamp bound to the audit manifest time;
- a packet hash.

## Canonical packet hash

To calculate `packet_hash`:

1. remove the top-level `packet_hash` member;
2. serialize the remaining JSON value with UTF-8, sorted object keys, no insignificant
   whitespace, Unicode preserved, and non-finite numbers rejected;
3. calculate SHA-256 over those bytes;
4. encode the value as `sha256:<64 lowercase hexadecimal characters>`.

Array order is significant. Object insertion order is not significant. A verifier MUST reject
an unsupported protocol version before relying on the binding.

## Packet identifier

The candidate Python implementation derives `packet_id` from the protocol version, candidate
hash, manifest hash, and evidence-bundle hash. The identifier is a deterministic locator, not
an authentication or secrecy mechanism.

## Required semantic verification

JSON Schema validation is necessary but insufficient. A verifier MUST also:

1. recompute the packet and evidence-bundle hashes;
2. recompute every record hash supported by the declared protocol version;
3. verify that the candidate binds the included bundle and exact evidence record;
4. verify tenant and case scope consistency;
5. verify candidate-to-verification, verification-to-approval, approval-to-authorization, and
   manifest bindings;
6. require passing verification and an approved decision;
7. enforce the governed-profile separation-of-duties rule;
8. recompute the authorized-output hash and compare its exact content with the candidate;
9. require an authorized exact-use decision;
10. preserve and report all limitations.

A failure in any required check invalidates the packet. A verifier MUST NOT return a partial
success as if it satisfied the claimed profile.

## Security properties and non-properties

A valid packet provides deterministic integrity and linkage evidence for the records it
contains under the declared protocol. It does not by itself establish:

- who produced or approved the records;
- whether a source system emitted complete or authentic evidence;
- whether timestamps came from a trusted authority;
- whether an external action occurred;
- whether the authorized output was emitted, delivered, consumed, revoked, or superseded;
- confidentiality or anonymity of hashed values;
- non-repudiation, production isolation, or regulatory compliance.

Signatures, attestations, transparency services, and selective disclosure require later,
separately versioned profiles.

## Version handling

Consumers MUST treat `0.3.0-candidate.1` as experimental. Candidate packets MUST NOT be
represented as stable `v1` protocol artifacts. Unknown fields are rejected by the candidate
schema so that security-relevant data cannot be silently ignored.

The Python reference exposes `load_assurance_packet` to parse and semantically verify a
JSON-compatible packet received from another process. Parsing rejects missing and unexpected
fields and does not convert a well-formed but invalid packet into a trusted object. Consumers
must still validate the JSON value against the versioned schema before semantic verification.
