# Phase 1 implementation plan

Status: **implementation in progress; PR A through PR D complete**. The maintainer recorded the
disposition of PR #28, explicitly approved synthetic Phase 1, and documented the independent-review
exception. PR E completes operator and adopter readiness. Production use remains prohibited.

## Phase 1 outcome

Deliver a locally deployable, synthetic, full agentic reference workflow that reconstructs a
multi-agent vendor-assurance response from authenticated test identities through exact-use
authorization, simulated effect receipt, reconciliation, packet signing, and independent
TypeScript verification.

No production destination, customer data, production identity provider, or production key is
used.

## Work packages

| Package | Deliverable | Principal acceptance |
|---|---|---|
| P1.1 Contracts | Draft JSON Schemas for activity envelope, delegation, memory access, tool activity, policy decision, receipt, reconciliation, status, DSSE wrapper, and conformance report | Exact fields, size bounds, version rejection, negative fixtures |
| P1.2 Durable local runtime | Docker Compose, PostgreSQL state/journal, transactional outbox, local object store, reset/seed tooling | One-command startup, S0 behavior, deterministic reset, no external credentials |
| P1.3 Run and capability control | Trusted run coordinator, parent-child graph, narrowed grants, budgets, expiry, revocation | Cross-run/tenant and privilege-expansion tests fail closed |
| P1.4 Agent/tool adapters | Synthetic orchestrator and specialist agents, bounded memory adapter, policy-enforcing tool gateway | No authoritative field copied from model output; no private reasoning retained |
| P1.5 Existing control chain | Integrate compile, verify, approval, exact-use authorization, audit, and packet construction | Current v0.3 tests remain unchanged and pass |
| P1.6 Effects and lifecycle | Simulated delivery adapter, operation/attempt records, receipt, reconciliation, consumption, expiry, revocation, supersession | Duplicate, timeout/unknown, stale, revoked, and compensation tests pass |
| P1.7 Development signing | Standard DSSE envelope, test issuer/key metadata, development signer, rotation/revocation fixtures | Cross-language vectors; no authenticated-profile claim |
| P1.8 TypeScript verifier | Separately implemented schema, canonicalization, binding, DSSE, receipt, and limitation verification | Consumes only contracts/vectors; detects all required mutations |
| P1.9 Reference experience | Vendor-assurance scenario, CLI/API examples, reviewer UI or terminal flow, audit export, runbooks | A new team completes the workflow from the playbook without code changes |

## Delivery sequence

### PR A: contracts and adversarial vectors

- draft schemas and examples;
- positive, negative, downgrade, replay, cross-scope, and mutation vector catalog;
- protocol-versus-capability conformance report shape;
- no runtime behavior.

### PR B: local durable control plane

- Docker Compose and dependency health checks;
- state, journal, outbox, artifacts, migrations, and deterministic reset;
- run/delegation/capability APIs and policy decisions;
- S0 storage-assurance self-report.

### PR C: synthetic full-agentic workflow

- orchestrator, specialist agents, memory and tool adapters;
- current v0.3 control-chain integration;
- simulated Tier 3 effect, receipt, reconciliation, revocation, and supersession;
- customer-safe packet and audit export.

### PR D: development signing and TypeScript verifier

- standard DSSE wrapper and pinned test trust bundle;
- cross-language canonicalization and signature vectors;
- independent TypeScript verifier and CLI;
- end-to-end conformance report.

### PR E: operator and adopter readiness

- implementation guide, threat model, data inventory, and runbooks;
- backup/restore and failure-injection exercises;
- reproducible performance baseline;
- fresh-clone usability test and Phase 1 limitations report.

Each PR remains independently testable. No PR may silently add a claimed future profile.

## Reference workflow

1. Authenticated synthetic requester submits a vendor-security question.
2. Orchestrator receives a bounded grant and delegates evidence collection to specialists.
3. Specialists query synthetic policy/control memory through the governed adapter.
4. Drafting agent proposes claims, evidence references, output, and limitations.
5. Trusted compiler and deterministic verifier construct and check the candidate.
6. Synthetic human reviewer approves the exact candidate and verification result.
7. Exact-use authorizer permits one synthetic customer, purpose, output, channel, and validity.
8. Simulated executor records submission, acknowledgement, effect observation, and reconciliation.
9. Packet service reconstructs the v0.3 chain and emits a development DSSE envelope.
10. TypeScript verifier validates the packet, trust fixture, activity graph, receipt, and
    limitations without importing Python implementation code.
11. A revocation or supersession scenario demonstrates preserved history and changed status.

## Required fail-closed tests

- child capability exceeds parent grant;
- event identity/scope copied from an untrusted adapter body;
- cross-tenant memory, evidence, tool result, receipt, or packet;
- missing/reordered/duplicate event and changed batch membership;
- stale/self approval and mutated candidate, purpose, audience, output, or limitation;
- forged provider receipt or acknowledgement upgraded to effect success;
- duplicate effect, changed idempotency input, timeout/unknown retry, and invalid compensation;
- wrong payload type, key ID, issuer trust, algorithm metadata, signature, rotation, or revocation;
- ordinary hash presented as anonymization;
- unsupported protocol/profile/capability or silent downgrade;
- deleted evidence presented as fully verifiable;
- production network destination or credential present in the reference configuration.

## Phase 1 definition of done

- clean checkout starts locally with one documented command and no external secret;
- all existing tests plus new Python and TypeScript suites pass;
- at least 100 synthetic/adversarial cases are reproducible;
- packet and DSSE vectors verify independently in both languages;
- the complete reference workflow is reconstructable from durable records;
- revocation, supersession, duplicate prevention, unknown-effect reconciliation, backup, and
  restore are demonstrated;
- repository validator, dependency audit, static analysis, package/container scans, and docs
  validation pass;
- limitations state development identities/keys, synthetic evidence, S0 storage, and no
  production-effect authorization;
- an independent reviewer can follow the playbook and produce a machine-readable report.

## Explicitly deferred

- live AWS deployment and S1/S2 evidence;
- enterprise OIDC and phishing-resistant MFA integration;
- production KMS/HSM keys and trusted timestamping;
- live SaaS/cloud effect adapters;
- customer data or customer-specific policies;
- federated issuer discovery, transparency witness, selective disclosure, or certification.

These become later work only after Phase 1 demonstrates the portable control and verification
boundaries with synthetic data.
