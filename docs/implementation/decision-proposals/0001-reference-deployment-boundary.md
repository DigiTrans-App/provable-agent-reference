# Proposed decision 0001: Separate protocol conformance from deployment assurance

Status: **proposed**, not an accepted ADR.

## Context

Protocol conformance verifies portable record behavior. Production deployments add identity,
keys, storage, network, availability, retention, and incident assumptions that the protocol
does not currently test.

## Proposed decision

Maintain separate version identifiers and claims for:

1. protocol conformance profiles;
2. reference deployment document versions;
3. organization-specific operational assurance.

The AWS mapping is informative and replaceable. Logical behavior, not a cloud product, defines
the reference deployment. Passing protocol conformance must never be represented as production
deployment certification.

## Consequences

- Implementations remain portable and may use embedded, separated, or offline patterns.
- Deployment testing and operational evidence require their own reports.
- Documentation and UI must display protocol and deployment status separately.
- Future deployment profiles need independent threat models and negative tests.

## Affected protocol versions

None. This proposal is compatible with `0.3.0-candidate.1` and does not add a packet claim.

## Links

- [RFC issue #35](https://github.com/DigiTrans-App/provable-agent-reference/issues/35)
- [Reference deployment profile](../reference-deployment-profile.md)
- [Adoption and maturity gates](../adoption-and-conformance.md)
