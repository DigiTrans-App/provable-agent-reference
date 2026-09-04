# Roadmap

## v0.1 - Reference foundation

- [x] Semantic-only draft contract
- [x] Trusted deterministic compiler
- [x] Scoped evidence bundles
- [x] Deterministic verification findings
- [x] Human approval bound to candidate hash
- [x] Exact-use authorization
- [x] Tamper-evident audit manifest
- [x] Synthetic examples and tests
- [x] Optional OpenAI Agents SDK example
- [x] Local adversarial evaluation harness

## v0.2.0 - Runtime interoperability and security baseline

Released on 2026-08-03.

- [x] Versioned adapter interface for agent runtimes
- [x] Experimental Codex execution and multi-agent evidence adapter
- [x] Codex synthetic compatibility test vectors
- [x] Offline OpenAI Agents SDK compatibility validation
- [x] CodeQL, dependency-review, and OpenSSF Scorecard automation
- [x] Full-SHA GitHub Actions pinning and least-privilege workflow permissions
- [x] Validated source distribution and wheel release artifacts
- [x] SHA-256 artifact manifest and tag-triggered GitHub release workflow

## v0.2.x - Interoperability hardening

- [x] Independent validation runner, report schema, artifact verification, reviewer guide, and public intake workflow
- [ ] Additional provider or runtime example
- [ ] Cross-runtime evidence-adapter conformance profile ([#12](https://github.com/DigiTrans-App/provable-agent-reference/issues/12))
- [ ] Additional cross-runtime compatibility test vectors
- [ ] JSON-LD or equivalent provenance profile exploration
- [ ] Pluggable policy rules

## v0.3 - Reference Architecture Candidate

- [x] Separate the architecture, protocol candidate, Python implementation, adapters, and conformance model
- [x] Normative lifecycle state machine and fail-closed invalidation rules
- [x] Candidate portable Assurance Packet schema, builder, verifier, and synthetic vector
- [x] Cumulative versioned conformance profiles
- [x] Public RFC and immutable ADR process
- [ ] Independent architecture and security review of the candidate ([#27](https://github.com/DigiTrans-App/provable-agent-reference/issues/27))
- [ ] Second non-OpenAI runtime adapter
- [ ] Second-language verifier or equivalent independent implementation
- [ ] Provider-neutral golden canonicalization and negative conformance vectors

- [ ] 100+ synthetic evaluation cases
- [ ] Property-based tests for canonicalization and replay resistance ([#11](https://github.com/DigiTrans-App/provable-agent-reference/issues/11))
- [ ] Versioned signed-record adapter interface ([#10](https://github.com/DigiTrans-App/provable-agent-reference/issues/10))
- [ ] Keyed commitment and selective-disclosure research ([#13](https://github.com/DigiTrans-App/provable-agent-reference/issues/13))
- [ ] Formal threat-model review
- [ ] Reproducible benchmark reports
- [ ] Maintainer onboarding and expanded release automation

## Phase 0 - Implementable full agentic reference architecture

Tracked in [#35](https://github.com/DigiTrans-App/provable-agent-reference/issues/35). These
items are informative design work until accepted through the normative change process.

- [x] Define the Phase 0 implementation RFC and scope
- [x] Define full agentic actors, activities, authority flow, and privacy boundary
- [x] Define logical service, API, event, storage, identity, and signing contracts
- [x] Define a local and AWS minimum reference deployment profile
- [x] Publish the team implementation playbook and maturity gates
- [ ] Resolve record granularity, signature envelope, receipt portability, and memory privacy
- [ ] Accept or revise the proposed architecture decisions
- [ ] Approve Phase 1 implementation scope after v0.3 candidate disposition

## v1.0 - Stable reference architecture

- [ ] Two independent technical reviews completed and findings resolved or documented
- [ ] Stable protocol version and compatibility policy
- [ ] Independent implementation passes the public conformance kit
- [ ] Positive, negative, downgrade, and replay vectors published
- [ ] Release-candidate feedback period completed
- [ ] Assurance claims and non-properties reviewed for stable publication

## Non-goals

The public roadmap does not include a hosted SaaS platform, customer-specific workflows, managed evidence operations, proprietary connectors, production identity systems, or commercial enterprise administration.
