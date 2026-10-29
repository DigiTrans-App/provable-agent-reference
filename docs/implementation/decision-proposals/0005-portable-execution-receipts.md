# Proposed decision 0005: Portable receipts separate submission from observed effect

Status: **proposed**, not an accepted ADR.

## Context

An HTTP success or provider acknowledgement may show only that a request was received. It does
not necessarily prove that the intended external effect occurred. A portable receipt must
preserve this distinction across SaaS, cloud, database, messaging, and human-task providers.

## Proposed decision

Represent effect evidence as a core receipt record plus provider-specific evidence references.
The portable core records facts common across providers; adapters cannot upgrade provider
semantics into stronger status.

## Core receipt

The proposed core contains:

- receipt schema/version and immutable receipt ID;
- tenant, case, run, operation, attempt, and correlation identifiers;
- authorization ID and hash;
- executor subject/issuer and adapter identity/version;
- provider and operation type;
- canonical request/action digest and privacy-bounded target reference;
- idempotency-key commitment and attempt number;
- submitted, acknowledged, observed, and reconciled times with source/assurance metadata;
- provider receipt identifier and response/effect digest or immutable evidence reference;
- `submission_status`: `not_submitted`, `submitted`, `acknowledged`, `rejected`, or `unknown`;
- `effect_status`: `not_observed`, `succeeded`, `failed`, `partial`, `compensated`, or `unknown`;
- reconciliation method, policy version, errors, and limitations;
- record hash and optional authenticated-record reference.

Raw credentials, bearer tokens, unrestricted provider responses, and sensitive destination
identifiers are prohibited from the portable core.

## Success rule

`submission_status=acknowledged` is not effect success. `effect_status=succeeded` requires an
adapter-defined observation whose semantics and limitations are registered and testable. When a
provider cannot expose such evidence, the result remains `not_observed` or `unknown`.

Provider evidence may include a signed response, immutable event, queryable state snapshot,
message delivery record, transaction identifier, or human completion record. The packet states
which evidence class was used.

## Retry and idempotency

- One logical effect has one `operation_id` and stable canonical action digest.
- Every attempt has a distinct `attempt_id` and immutable receipt.
- The idempotency key is bound to tenant, executor, operation, and action digest.
- Reuse with different content fails.
- `unknown` blocks an unsafe retry until reconciliation proves failure or the provider offers a
  verified idempotent replay contract.
- Compensation is a new authorized effect linked to the original; it does not rewrite success.

## Extensions

Provider extensions use registered namespaces and are covered by the receipt digest. A verifier
may ignore an unsupported informational extension only when the schema marks it non-critical.
Unknown critical extensions fail closed.

## Consequences

- The architecture makes fewer but defensible claims about external outcomes.
- Adapters document provider semantics instead of mapping every `2xx` response to success.
- Reconciliation becomes a first-class operation and metric.
- Cross-provider tools can share one core receipt model.

## Required negative tests

- acknowledgement represented as success;
- forged or substituted provider receipt;
- mismatched authorization, action digest, target, operation, attempt, or tenant;
- duplicate execution under a reused or changed idempotency key;
- unsafe retry after timeout/unknown;
- effect success without registered observation evidence;
- unknown critical extension;
- compensation that overwrites the original receipt.

## Affected protocol versions

None in Phase 0. A future `par.receipted-effects.v1` profile requires a normative receipt schema
and provider-semantics registry.
