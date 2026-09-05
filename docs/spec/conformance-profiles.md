# Conformance profiles

Status: normative candidate for `0.3.0-candidate.1`.

Profiles are cumulative and ordered. Claiming a later profile requires every earlier profile.
Passing a profile is an interoperability result for a specific implementation and version; it
is not certification of a deployment or organization.

| Profile | Additional required behavior |
|---|---|
| `par.core.v1` | Canonical candidate construction, deterministic verification, version rejection, and hash recomputation |
| `par.evidence-bound.v1` | Scoped evidence bundle, exact evidence resolution, bundle binding, and cross-scope rejection |
| `par.governed.v1` | Passing verification, exact-hash human approval, visible rationale, and approver/agent identifier separation |
| `par.exact-use.v1` | Purpose, audience, candidate, approval, and exact authorized-output binding |
| `par.reconstructable.v1` | Complete audit reconstruction and portable Assurance Packet verification |

The Python candidate can construct and verify these five profiles for its bounded synthetic
model. Its identifier-separation check is not human identity proofing.

## Claim rules

- Profile identifiers MUST appear in the order above.
- A claim MUST be a non-empty prefix of the supported profile sequence.
- Unknown, duplicate, reordered, or skipped profiles MUST fail validation.
- A conformance report MUST identify protocol version, implementation name and version, exact
  source revision, test-vector revision, environment, results, and limitations.
- Self-issued results MAY support development but MUST NOT be described as independent review.

## Planned profiles

The following names describe roadmap directions and MUST NOT appear in candidate packet claims:

- authenticated records backed by a versioned signer/verifier interface;
- privacy-preserving commitments and selective disclosure;
- trusted timestamp or transparency-service inclusion;
- runtime-attested evidence collection;
- durable single-use consumption, revocation, and supersession.

Each future profile requires a design review, machine-readable contract, positive and negative
vectors, downgrade and replay tests, and an explicit statement of trust assumptions.

## Conformance suite direction

A stable conformance kit should contain provider-neutral fixtures, expected canonical bytes,
expected hashes, mutation operators, negative vectors, and a machine-readable report. At least
one independent implementation in another language is required before declaring the protocol
stable.
