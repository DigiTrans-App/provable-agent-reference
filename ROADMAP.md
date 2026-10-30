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
- [ ] Independent architecture and security review of the candidate ([#27](https://github.com/DigiTrans-App/provable-agent-reference/issues/27)); not performed. [#27](https://github.com/DigiTrans-App/provable-agent-reference/issues/27) was closed with the candidate merge ([#28](https://github.com/DigiTrans-App/provable-agent-reference/pull/28)), where independent human approval was waived by a maintainer exception. The exception is not an independent review.
- [ ] Second non-OpenAI runtime adapter
- [ ] Second-language verifier or equivalent independent implementation. Partial: a development TypeScript verifier for DSSE envelopes and `packet_hash` binding exists ([#44](https://github.com/DigiTrans-App/provable-agent-reference/pull/44)). It is not yet an accepted independent second-language conformance verifier.
- [ ] Provider-neutral golden canonicalization and negative conformance vectors

- [ ] 100+ synthetic evaluation cases
- [x] Property-based tests for canonicalization and replay resistance ([#11](https://github.com/DigiTrans-App/provable-agent-reference/issues/11)); includes nested input rejection, trusted-field mutations, scope and output replay checks, and documented seed/minimized-example reproduction.
- [ ] Versioned signed-record adapter interface ([#10](https://github.com/DigiTrans-App/provable-agent-reference/issues/10)). Open. Partial: development-only DSSE signing of the whole Assurance Packet exists ([#44](https://github.com/DigiTrans-App/provable-agent-reference/pull/44)); there is no signer/verifier adapter interface, per-record signing, or cross-context replay vectors.
- [ ] Keyed commitment and selective-disclosure research ([#13](https://github.com/DigiTrans-App/provable-agent-reference/issues/13))
- [ ] Formal threat-model review
- [ ] Reproducible benchmark reports
- [ ] Maintainer onboarding and expanded release automation

## Phase 0 - Implementable full agentic reference architecture

Tracked in [#35](https://github.com/DigiTrans-App/provable-agent-reference/issues/35), closed on
2026-09-05 with Phase 0 PR #40. These items are informative design work until accepted through the
normative change process.

- [x] Define the Phase 0 implementation RFC and scope
- [x] Define full agentic actors, activities, authority flow, and privacy boundary
- [x] Define logical service, API, event, storage, identity, and signing contracts
- [x] Define a local and AWS minimum reference deployment profile
- [x] Publish the team implementation playbook and maturity gates
- [x] Resolve record granularity, signature envelope, receipt portability, memory privacy, and storage assurance
- [x] Complete maintainer-side architecture/security pre-review and correct design ambiguities
- [x] Publish the dependency-gated Phase 1 plan ([#37](https://github.com/DigiTrans-App/provable-agent-reference/issues/37))
- [ ] Complete independent architecture/security review (waived for synthetic Phase 1 by a documented maintainer exception; not performed)
- [ ] Accept or revise the proposed architecture decisions (decision 0008 is accepted; proposals 0001 through 0007 remain proposals, implemented experimentally in Phase 1)
- [x] Approve Phase 1 implementation scope after v0.3 candidate disposition (synthetic scope only; recorded in [#37](https://github.com/DigiTrans-App/provable-agent-reference/issues/37))

## Phase 1 - Synthetic full agentic reference deployment

Tracked in [#37](https://github.com/DigiTrans-App/provable-agent-reference/issues/37), closed on
2026-09-05. Development status and formal-acceptance status are listed separately. Everything here
is synthetic, development-only, S0 storage, and not approved for production use, customer data,
or live effects.

Development status (merged to `main`):

- [x] PR A: draft contracts and adversarial vectors ([#41](https://github.com/DigiTrans-App/provable-agent-reference/pull/41))
- [x] PR B: local durable control plane ([#42](https://github.com/DigiTrans-App/provable-agent-reference/pull/42))
- [x] PR C: synthetic full-agentic workflow ([#43](https://github.com/DigiTrans-App/provable-agent-reference/pull/43))
- [x] PR D: development DSSE signing and a TypeScript DSSE verifier ([#44](https://github.com/DigiTrans-App/provable-agent-reference/pull/44))
- [x] PR E: operator guide, threat model, exercises, and a self-issued readiness gate ([#45](https://github.com/DigiTrans-App/provable-agent-reference/pull/45))

Formal-acceptance status (outstanding):

- [ ] Independent architecture/security review (waived for synthetic Phase 1; required before any non-synthetic pilot)
- [ ] Dedicated container vulnerability scan (required before any non-synthetic pilot)
- [ ] Accepted authenticated-records profile and canonical hash-input contract (`par.authenticated-records.v1` is not claimed)
- [ ] Independent second-language conformance verifier (see v0.3)

## v1.0 - Stable reference architecture

- [ ] Two independent technical reviews completed and findings resolved or documented
- [ ] Stable protocol version and compatibility policy
- [ ] Independent implementation passes the public conformance kit
- [ ] Positive, negative, downgrade, and replay vectors published
- [ ] Release-candidate feedback period completed
- [ ] Assurance claims and non-properties reviewed for stable publication

## Non-goals

The public roadmap does not include a hosted SaaS platform, customer-specific workflows, managed evidence operations, proprietary connectors, production identity systems, or commercial enterprise administration.
