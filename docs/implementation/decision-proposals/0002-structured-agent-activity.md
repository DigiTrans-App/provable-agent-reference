# Proposed decision 0002: Record structured agent activity without private chain-of-thought

Status: **proposed**, not an accepted ADR.

## Context

Full agentic accountability requires evidence of requests, delegation, tools, memory, policy,
approval, external effects, and observed outcomes. Capturing unrestricted prompts, payloads, or
private reasoning creates privacy, security, intellectual-property, and retention risks and is
not required to verify authority or causality.

## Proposed decision

Use a trusted event envelope plus allowlisted, versioned activity bodies. Record structured
intent, evidence references, policy decisions, canonical action inputs or digests, result
references, limitations, receipts, and causality. Do not require, request, or retain private
chain-of-thought. Raw content is opt-in and controlled by data classification, minimization,
disclosure, and retention policy.

## Consequences

- Multi-agent and tool activity can be reconstructed without treating provider telemetry as
  authoritative.
- Adapters must implement privacy-bounded allowlists and size limits.
- Some debugging detail is intentionally unavailable and must be reported as such.
- Hashes provide integrity references, not anonymity or truth.
- Future agent-activity profiles need schemas, canonicalization, vectors, and compatibility
  policy before becoming normative.

## Affected protocol versions

None in Phase 0. Future activity profiles would extend, not silently redefine,
`0.3.0-candidate.1`.

## Links

- [RFC issue #35](https://github.com/DigiTrans-App/provable-agent-reference/issues/35)
- [Agentic reference architecture](../agentic-reference-architecture.md)
- [Logical service and event contracts](../service-contracts.md)
