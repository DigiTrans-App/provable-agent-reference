# Implementable reference architecture

Status: **Phase 0 design proposal**. These documents are informative, depend on the v0.3
Reference Architecture Candidate, and do not change protocol `0.3.0-candidate.1`.

This package translates the provider-neutral protocol into a system that an implementation
team can build, deploy, operate, and independently evaluate. It deliberately separates logical
requirements from one opinionated deployment example.

## Documents

- [Phase 0 RFC](phase-0-rfc.md)
- [Phase 0 design decisions](phase-0-decisions.md)
- [Internal architecture and security pre-review](internal-architecture-security-review.md)
- [Phase 1 implementation plan](phase-1-implementation-plan.md)
- [Experimental Phase 1 contracts and vectors](phase-1-contracts.md)
- [Full agentic reference architecture](agentic-reference-architecture.md)
- [Minimum reference deployment profile](reference-deployment-profile.md)
- [Logical service and event contracts](service-contracts.md)
- [Team implementation playbook](implementation-playbook.md)
- [Adoption, conformance, and maturity gates](adoption-and-conformance.md)
- [Proposed deployment-boundary decision](decision-proposals/0001-reference-deployment-boundary.md)
- [Proposed agent-activity decision](decision-proposals/0002-structured-agent-activity.md)
- [Proposed activity-granularity decision](decision-proposals/0003-activity-record-granularity.md)
- [Proposed signature and key-discovery decision](decision-proposals/0004-signature-envelope-and-key-discovery.md)
- [Proposed execution-receipt decision](decision-proposals/0005-portable-execution-receipts.md)
- [Proposed memory-privacy decision](decision-proposals/0006-memory-privacy.md)
- [Proposed storage-assurance decision](decision-proposals/0007-storage-assurance-levels.md)

The discussion and acceptance record is [RFC issue #35](https://github.com/DigiTrans-App/provable-agent-reference/issues/35).

## Reading order

Architects should start with the Phase 0 RFC, decision summary, and agentic architecture.
Implementation leads should then read the deployment profile, detailed decision proposals, and
service contracts. Delivery teams should execute the playbook and use the maturity gates as
release criteria.

## Status rule

Nothing in this directory is a conformance requirement unless it is later accepted through the
normative change process, assigned a versioned profile, and backed by machine-readable positive
and negative vectors. A reference deployment can demonstrate a pattern; it cannot certify that
another deployment is secure.
