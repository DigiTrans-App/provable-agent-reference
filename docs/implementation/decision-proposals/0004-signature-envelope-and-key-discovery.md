# Proposed decision 0004: DSSE-style packet signatures with verifier-pinned issuer trust

Status: **proposed**, not an accepted ADR.

## Context

The current packet hash detects mutation but does not authenticate the producer or approver.
Signing an ambiguous JSON representation or trusting a key supplied by the packet would create
false authentication.

## Proposed decision

Wrap the exact canonical Assurance Packet bytes in a DSSE-style detached signing envelope. The
envelope applies domain separation using a registered payload type and supports one or more
signatures without changing the packet's existing content hash.

Conceptual fields are:

- `envelope_version`;
- `payload_type`, versioned for the Assurance Packet media type;
- `payload_digest` over the exact canonical bytes;
- optional embedded payload or an external immutable payload reference;
- signature entries containing `issuer`, `key_id`, `algorithm`, `signature`, and a claimed
  signing time with its time-assurance level;
- envelope limitations.

The first interoperable algorithm profile should require one widely implemented asymmetric
algorithm suitable for managed key services. Additional algorithms require explicit registry,
test vectors, and downgrade handling; verifiers never infer an algorithm from key material.

## Trust and key discovery

The verifier starts with an explicit trust configuration that maps accepted issuer identifiers
to trusted keys or trust roots. A packet-supplied key is never sufficient.

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
- Revocation identifies key, issuer, effective time, reason class, and signed status version.
- A verifier distinguishes invalid-at-signing, revoked-after-signing, unknown-time, and
  currently-disabled results.
- Without an independently trusted time source, the verifier reports signature validity under
  the available time assumptions and must not claim trusted signing time.

## Signer roles

Packet issuer, approver, evidence source, and effect executor are distinct roles. One envelope
signature authenticates only the signing issuer's statement; it does not retroactively
authenticate every embedded actor. Role-specific signed records or attestations require their
own profiles.

## Consequences

- Existing packet hashes remain stable and signatures can be transported separately.
- Offline verification remains possible with a pinned trust bundle.
- Multi-signature and cross-organization use remain possible without requiring them in Phase 1.
- The implementation must define exact canonical bytes before signature interoperability can be
  claimed.

## Phase 1 implementation

Use a clearly labeled development signer and test trust bundle. Test wrong issuer, key,
algorithm, payload type, payload digest, signature, rotation, revocation, and missing trusted
time. Phase 1 exports no `par.authenticated-records.v1` claim.

## Affected protocol versions

None in Phase 0. A future authenticated-records profile requires a normative envelope and
algorithm registry.
