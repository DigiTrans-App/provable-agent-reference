# Proposed decision 0004: DSSE-compatible packet signatures with verifier-pinned issuer trust

Status: **proposed**, not an accepted ADR.

## Context

The current packet hash detects mutation but does not authenticate the producer or approver.
Signing an ambiguous JSON representation or trusting a key supplied by the packet would create
false authentication.

## Proposed decision

Wrap the exact canonical Assurance Packet bytes in a standard DSSE envelope. The envelope uses
DSSE pre-authentication encoding and the standard fields:

- `payloadType`, registered and versioned for the Assurance Packet media type;
- `payload`, containing the base64-encoded exact canonical packet bytes;
- `signatures`, containing standard `keyid` and `sig` values.

Phase 1 does not define a detached-payload extension or add issuer, algorithm, time, or
verification material fields to the DSSE envelope. Those properties come from the verifier's
trusted key metadata or separately standardized attestations. This keeps the transport
compatible instead of calling a project-specific shape DSSE.

The first interoperable algorithm profile should require one widely implemented asymmetric
algorithm suitable for managed key services. Additional algorithms require an explicit
registry, test vectors, and downgrade handling. The verifier resolves the algorithm from pinned
key metadata; it never guesses from a signature or accepts an untrusted algorithm declaration.

## Trust and key discovery

The verifier starts with an explicit trust configuration that maps accepted issuer identifiers
and globally unique key IDs to trusted keys, algorithms, roles, and validity metadata. A
packet-supplied key is never sufficient.

Two discovery modes are allowed:

1. **Offline:** a pinned trust bundle contains issuer, key, validity, status, algorithm, and
   metadata-version information.
2. **Online:** an issuer may publish versioned metadata at a well-known HTTPS location. The
   verifier accepts it only when authenticated by an already trusted root or an explicitly
   pinned metadata digest.

Trust on first use is prohibited for governed or external-use claims. Embedded metadata may aid
transport but cannot create trust.

## Rotation, revocation, and time

- Key IDs are immutable and never reused for different key material.
- Rotation publishes the successor before use and retains historical verification material for
  the applicable record-retention period.
- Revocation metadata identifies key, issuer, effective time, reason class, and signed status
  version.
- A verifier distinguishes invalid-at-signing, revoked-after-signing, unknown-time, and
  currently-disabled results.
- Without an independently trusted time source, the verifier reports signature validity under
  the available time assumptions and must not claim trusted signing time.

## Signer roles

Packet issuer, approver, evidence source, and effect executor are distinct roles. The trusted
key metadata authorizes each key for specific roles. One envelope signature authenticates only
the packet issuer's statement; it does not retroactively authenticate every embedded actor.
Role-specific signed records or attestations require their own profiles.

## Consequences

- Existing packet hashes remain stable and the DSSE envelope transports the exact packet.
- Offline verification remains possible with a pinned trust bundle.
- Multi-signature and cross-organization use remain possible without requiring them in Phase 1.
- The implementation must define exact canonical bytes before signature interoperability can be
  claimed.

## Phase 1 implementation

Use a clearly labeled development signer and test trust bundle. Interoperability is not claimed
until canonical packet bytes and DSSE pre-authentication encoding have cross-language vectors.
Test wrong issuer, key, algorithm, payload type, payload bytes, signature, role, rotation,
revocation, and missing trusted time. Phase 1 exports no `par.authenticated-records.v1` claim.

## Affected protocol versions

None in Phase 0. A future authenticated-records profile requires a normative envelope and
algorithm registry.
