# Team implementation playbook

Status: **informative Phase 0 proposal**.

This playbook is the delivery path from architecture selection to a controlled pilot. Teams
must adapt legal, privacy, security, and operational gates to their organization.

Implementation teams should record any deviation from the
[Phase 0 design decisions](phase-0-decisions.md), including its trust-boundary impact, tests,
owner, and expiration or promotion plan.

## Team and decision rights

| Role | Accountable for |
|---|---|
| Executive/workflow owner | Permitted business outcome, risk acceptance, pilot stop/go |
| Product owner | Use case, user experience, limitations, success measures |
| Architecture lead | Boundaries, contracts, portability, decision records |
| Security lead | Threat model, identity, keys, isolation, testing, incident readiness |
| Privacy/data owner | Data inventory, minimization, retention, disclosure, deletion |
| Agent/runtime lead | Adapter, delegation, tool and memory instrumentation |
| Control-plane lead | Compile, verify, approve, authorize, packet and audit services |
| Platform/SRE lead | Deployment, reliability, observability, backup and recovery |
| Independent verifier | Conformance evidence and adversarial evaluation |
| Human-review lead | Approval policy, reviewer training, escalation and sampling |

The same person may fill multiple implementation roles, but independent verification and
separation-of-duty claims require distinct accountable subjects.

## Stage 1: choose one bounded workflow

- Write one business outcome and one prohibited outcome.
- Identify requester, affected parties, approver, executor, verifier, and auditor.
- Classify the workflow using the architecture risk tiers.
- Enumerate every external effect and data source.
- Define where the agent stops when evidence, policy, or identity is unavailable.

**Exit:** one-page workflow charter, data classification, initial risk tier, and named owner.

## Stage 2: model authority and trust

- Draw trust zones and data flows.
- List human, workload, agent, tool, evidence-source, issuer, and verifier identities.
- Define capability grants and prove each delegation narrows authority.
- Identify authoritative sources for tenant, case, purpose, audience, time, and policy.
- Record all assumptions and non-properties.

**Exit:** reviewed trust-boundary model with no authoritative field sourced from model output.

## Stage 3: define evidence and agent activity

- Select required activity types from the agentic architecture.
- Define allowlisted event bodies and size limits.
- Decide what is stored directly, digest-bound, referenced, redacted, or prohibited.
- Do not request or retain private chain-of-thought.
- Define missing, partial, stale, conflicting, and unverifiable evidence behavior.

**Exit:** versioned event catalog, data dictionary, retention classes, and negative examples.

## Stage 4: define policy and human control

- Map risk tiers to allow, deny, automated verification, human approval, and escalation.
- Version policy bundles and obligations.
- Design the review surface to show exact content, evidence, limitations, purpose, audience,
  expiry, and requested effect.
- Define stale-decision invalidation and emergency revocation.
- Train reviewers on what approval does and does not establish.

**Exit:** tested policy matrix and approval procedure with separation-of-duty rules.

## Stage 5: implement the trusted control chain

- Integrate the existing compiler, verifier, approval, authorization, audit, and packet behavior.
- Validate complete predecessor records at every transition.
- Make transitions idempotent and append-only.
- Preserve rejected, expired, revoked, failed, and superseded histories.
- Add mutation tests for every binding.

**Exit:** the synthetic workflow passes positive and fail-closed transition tests.

## Stage 6: instrument the agentic runtime

- Assign authenticated run and workload identities outside the model.
- Capture delegation, model, memory, tool, policy, and observation events through bounded
  adapters.
- Put consequential tools behind the policy-enforcing gateway.
- Use short-lived, capability-scoped credentials.
- Add correlation, parentage, sequence, budget, expiry, and idempotency controls.

**Exit:** a multi-agent run is reconstructable without prompts or private reasoning.

## Stage 7: control external effects

- Canonicalize the exact action or output before authorization.
- Require approval appropriate to the risk tier.
- Execute through one trusted gateway.
- Persist provider receipt and observed status.
- Treat timeouts as unknown, reconcile before retrying, and support compensating action.

**Exit:** duplicate, stale, revoked, mismatched, and unknown-outcome tests fail safely.

## Stage 8: deploy and operate

- Deploy local synthetic first, then an isolated non-production environment.
- Configure tenant boundaries, workload identity, OIDC, KMS, secrets, queues, stores, and
  network policy.
- Establish dashboards, alerts, backups, restore tests, retention, deletion, and key rotation.
- Run incident exercises for key compromise, forged evidence, cross-tenant access, stuck
  effects, policy rollback, and revocation.

**Exit:** operational-readiness review passes and production destinations remain disabled.

## Stage 9: independent conformance

- Pin exact source, schema, vector, policy, and environment versions.
- Run positive, negative, mutation, replay, downgrade, and cross-scope vectors.
- Verify packets with a separately maintained implementation.
- Record failures and limitations; self-issued reports are labeled non-independent.

**Exit:** required profiles pass and every exception has an owner and disposition.

## Stage 10: controlled pilot

- Begin in shadow mode with synthetic or approved non-sensitive data.
- Compare agent recommendations and intended effects with existing human processes.
- Sample human-review quality and measure override behavior.
- Define automatic stop conditions and a rollback path.
- Permit limited effects only after a formal go/no-go decision.

**Exit:** pilot report covers security, privacy, reliability, conformance, user outcomes,
limitations, incidents, and the next risk decision.

## Minimum test matrix

| Domain | Required tests |
|---|---|
| Identity | wrong issuer, disabled subject, spoofed approver, workload impersonation |
| Scope | cross-tenant/case/run evidence, memory, tool, packet, and receipt substitution |
| Delegation | expanded grant, sibling/parent escalation, expired child, budget overrun |
| Evidence | missing, partial, stale, conflicting, poisoned, malformed, oversized |
| Bindings | mutation at every predecessor and total-rehash attempts |
| Approval | self, stale, expired, changed output, missing rationale, replay |
| Effects | duplicate, reordered, revoked, unknown timeout, forged receipt, reconciliation conflict |
| Keys | wrong issuer, algorithm, key, rotation, expiry, revocation, signature |
| Profiles | unknown, skipped, duplicate, reordered, downgrade |
| Operations | queue replay, database restore, regional recovery, clock skew, audit gap |

## Release checklist

- [ ] Workflow charter and risk tier approved
- [ ] Architecture and data-flow diagrams current
- [ ] Threat model and privacy assessment complete
- [ ] Identity, capability, and key ownership documented
- [ ] Protocol and implementation versions pinned
- [ ] Negative tests and independent verifier pass
- [ ] Backup, restore, incident, revocation, and key-rotation exercises pass
- [ ] Reviewer training and escalation complete
- [ ] Limitations visible to users and packet consumers
- [ ] Production effect destinations explicitly enabled through change control
- [ ] Pilot stop conditions and owner recorded

## Definition of successful implementation

An independent operator can deploy the system, run the complete workflow, explain every trust
anchor, reconstruct every consequential action, verify a packet using separate software,
demonstrate revocation and recovery, and identify the assurance claims the system cannot make.
