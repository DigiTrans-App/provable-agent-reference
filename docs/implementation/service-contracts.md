# Logical service and event contracts

Status: **informative Phase 0 proposal**. Names and fields are implementation inputs, not
normative protocol additions.

Record boundaries follow the proposed
[activity-granularity decision](decision-proposals/0003-activity-record-granularity.md). External
effect semantics follow the proposed
[portable receipt decision](decision-proposals/0005-portable-execution-receipts.md).

## Contract principles

- Expose logical contracts before selecting service boundaries.
- Carry trusted context from authenticated infrastructure, never from free-form agent output.
- Version every external request, response, event, policy bundle, and schema.
- Make correlation, causality, idempotency, classification, and limitations explicit.
- Reject unknown security-relevant fields instead of silently ignoring them.
- Return machine-readable failure codes and do not upgrade `unknown` to success.

## Trusted event envelope

Every journaled activity uses an envelope equivalent to:

```json
{
  "event_version": "0.1-draft",
  "event_id": "evt_example",
  "event_type": "tool.requested",
  "tenant_id": "tenant_example",
  "case_id": "case_example",
  "run_id": "run_example",
  "parent_run_id": "run_parent_or_null",
  "sequence": 7,
  "actor": {
    "subject": "workload_subject",
    "issuer": "trusted_issuer",
    "actor_type": "agent_runtime"
  },
  "policy_version": "policy:example:4",
  "occurred_at": "trusted-or-declared-time",
  "observed_at": "control-plane-time",
  "previous_event_hash": "sha256:...",
  "body_hash": "sha256:...",
  "limitations": []
}
```

The complete canonicalization and hash inputs require a future protocol RFC. `occurred_at` may
be a source-declared time and must identify its assurance level; `observed_at` is the receiving
control plane's time.

## Required logical operations

| Operation | Required inputs | Success output | Principal failures |
|---|---|---|---|
| Create run | Authenticated requester, purpose, audience, risk tier, policy | Trusted run context | identity, scope, policy, replay |
| Register delegation | Parent run, child subject, task, narrowed grant, expiry | Delegation record | privilege expansion, unknown child, stale parent |
| Record observation | Run context, adapter identity, bounded typed event | Observation record | unsupported type, size, sequence, cross-scope |
| Request tool | Tool/version, canonical args, grant, idempotency key | Policy decision and correlation ID | denied capability, stale grant, ambiguous tool |
| Record tool result | Correlation ID, provider identity, bounded result/status | Result record | mismatch, replay, unsupported receipt |
| Resolve evidence | Tenant/case/run scope and evidence reference | Integrity-bound evidence record | missing, cross-scope, classification denial |
| Compile | Trusted context, semantic draft, evidence bundle | Canonical candidate | unresolved evidence, invalid scope/input |
| Verify | Candidate, bundle, policy/version | Verification result | binding, policy, disclosure, evidence failure |
| Decide approval | Authenticated human, exact hashes, decision/rationale | Approval record | stale hash, self-approval, expired session |
| Authorize effect | Approval, exact action/output, audience/purpose, validity | Authorization record | mismatch, expiry, policy denial |
| Execute effect | Authorization, idempotency key, executor identity | Execution receipt or unknown status | stale/consumed/revoked authorization, provider ambiguity |
| Reconcile effect | Authorization and observed provider state | Reconciliation record | unverifiable or conflicting observation |
| Build packet | Complete supported chain and limitations | Packet plus issuer signature | incomplete chain, unsupported profile/key |
| Verify packet | Packet and explicit trust configuration | Results and limitations | schema, binding, signature, trust, replay/profile |
| Revoke/supersede | Authorized actor, target, reason, effective time/successor | Bound status record | unauthorized actor, invalid target or ordering |

## Error taxonomy

Use stable codes grouped by boundary:

- `IDENTITY_*`: missing, unauthenticated, wrong issuer, disabled subject;
- `SCOPE_*`: tenant, case, run, classification, or purpose mismatch;
- `CAPABILITY_*`: absent, expanded, expired, consumed, or denied grant;
- `EVIDENCE_*`: unresolved, incomplete, integrity failure, stale, disallowed disclosure;
- `BINDING_*`: candidate, verification, approval, authorization, output, or receipt mismatch;
- `POLICY_*`: unknown version, deny, obligation unmet;
- `EFFECT_*`: duplicate, unknown outcome, receipt mismatch, reconciliation required;
- `PROFILE_*`: unknown, skipped, reordered, unsupported;
- `KEY_*`: unknown issuer/key, invalid signature, expired, revoked;
- `SYSTEM_*`: unavailable, timeout, storage failure, sequence conflict.

Errors returned to an agent are privacy-bounded and must not disclose another tenant's
existence, secret material, policy internals, or unrestricted evidence content.

## Idempotency and ordering

- Mutating operations require an idempotency key scoped to tenant, operation, and trusted
  subject.
- Reuse with different canonical inputs is a conflict.
- Event sequence is monotonic within one run; causality across runs uses parent and correlation
  identifiers rather than wall-clock ordering alone.
- Consumers detect duplicates by immutable event ID and content hash.
- External effects remain pending or unknown until a receipt is reconciled.

## Compatibility

Additive fields are not automatically safe. A consumer either supports the declared schema and
profile or rejects it. Migration tools retain original records and create explicitly linked
successors; they do not rewrite signed or approved history.

## Transaction and capability invariants

- A security-relevant state mutation, its canonical journal record, and its outbox entry commit
  in one PostgreSQL transaction. If any element cannot commit, none becomes authoritative.
- Artifact bytes are not dual-written with the database. They are uploaded to a content-addressed
  staging key, verified against the declared digest, and finalized through an outbox-driven,
  idempotent workflow. Missing, orphaned, or mismatched artifacts remain unavailable and are
  reconciled explicitly.
- Capability attenuation compares the complete grant: capability identifiers, tenant/case/run
  scope, allowed resources and effects, budgets, validity, delegation depth, and obligations.
  A child grant must never be broader on any dimension. Equality is permitted only where policy
  explicitly allows pass-through; otherwise at least one dimension must narrow.
