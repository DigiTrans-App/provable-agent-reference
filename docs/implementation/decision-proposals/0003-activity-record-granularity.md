# Proposed decision 0003: One record per security-relevant boundary transition

Status: **proposed**, not an accepted ADR.

## Context

Recording every runtime token or internal step creates noise, privacy risk, provider coupling,
and false precision. Recording only the final artifact loses delegation, authority, tool, and
effect causality. The architecture needs a stable middle boundary.

## Proposed decision

Create one immutable activity record whenever authority, evidence, policy state, data access,
or an external effect crosses a trust boundary. Each record uses the trusted event envelope and
one versioned typed body.

Minimum activity families are:

- work request and trusted run creation;
- delegation grant, narrowing, expiry, and revocation;
- model invocation summary where it materially contributes to a controlled artifact or action;
- memory/data access decision and result-set commitment;
- tool request, policy decision, attempt, and result;
- evidence resolution;
- compile, verify, approval, and authorization transitions;
- effect submission, provider acknowledgement, reconciliation, and compensation;
- packet issue/verification and lifecycle expiry, consumption, revocation, or supersession.

Do not record token streams, hidden scratch work, or private chain-of-thought. Prompts and raw
payloads are optional classified artifacts, not required activity fields.

## Causality and attempts

- `run_id` identifies one trusted execution context.
- `parent_run_id` and `delegation_id` form the cross-agent authority graph.
- `operation_id` identifies one intended logical operation.
- `attempt_id` identifies each execution attempt under that operation.
- `correlation_id` binds requests, policy decisions, results, receipts, and reconciliation.
- `sequence` is monotonic within one run; cross-run order is a causal graph, not a wall-clock
  total order.
- `previous_event_hash` detects gaps or reordering within the run but does not prove storage
  completeness.

Retries never overwrite an earlier attempt. Batching is permitted only for truly atomic events
with a canonical ordered member list and a batch digest; it may not hide independently
authorized effects.

## Profile allocation

Existing v0.3 records remain in their current profiles. A future `par.activity-bound.v1`
profile should require the envelope, causal graph, delegation and tool/effect activity needed
by the workflow. Later authenticated and receipted-effect profiles should build on it.

## Consequences

- The journal remains reviewable and provider neutral.
- Security-relevant boundaries are visible without retaining unrestricted telemetry.
- Adapters must map provider events to typed records and mark unavailable fields rather than
  fabricate them.
- High-volume observability data remains outside the portable assurance record and can be linked
  by bounded references.

## Required negative tests

- duplicate event ID with changed content;
- skipped or reordered per-run sequence;
- child run without a valid delegation;
- child capability expansion;
- result or receipt bound to another operation, attempt, run, case, or tenant;
- batched effects that lack per-effect authorization;
- provider event containing authoritative identity or scope copied into the trusted envelope.

## Affected protocol versions

None in Phase 0. Future activity records require a separately versioned protocol extension.
