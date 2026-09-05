# Experimental Phase 1 contracts and vectors

Status: **experimental, stacked, and non-normative**. These contracts are a design-and-test
artifact for Phase 1 PR A. They do not change protocol `0.3.0-candidate.1`, establish a future
profile, authenticate a producer, or demonstrate a deployable runtime.

The contract work follows the [Phase 1 implementation plan](phase-1-implementation-plan.md)
and the proposed [logical service and event contracts](service-contracts.md). Implementation
remains dependency-gated by the disposition of PR #28, the Phase 0 RFC, and explicit maintainer
approval recorded in [Phase 1 tracker #37](https://github.com/DigiTrans-App/provable-agent-reference/issues/37).

## What this change adds

| Area | Contract | Synthetic example |
|---|---|---|
| Trusted activity | `agent-activity-record.schema.json` | Delegation, memory, tool, policy, and lifecycle records |
| Typed activity bodies | Delegation, memory, tool, policy, lifecycle body schemas | Embedded in the activity examples |
| Effect evidence | `execution-receipt.schema.json` | Successful synthetic observation with explicit provider evidence |
| Effect reconciliation | `reconciliation-record.schema.json` | Receipt-bound synthetic reconciliation |
| Packet transport | `dsse-assurance-envelope.schema.json` | Standard DSSE shape with non-cryptographic placeholder values |
| Reporting | `agentic-conformance-report.schema.json` | Self-issued, incomplete, contract-only report |
| Schema-negative vectors | `agentic-negative-vector-set.schema.json` | Version, size, field, binding, disclosure, effect, and downgrade mutations |
| Semantic-negative vectors | `agentic-semantic-vector-set.schema.json` | Replay, scope, ordering, hash-chain, and receipt-substitution cases |

All examples use synthetic identifiers, placeholder digests, invalid test issuers, and no
customer data, credential, production key, or external destination.

## Validation boundary

`scripts/validate_agentic_contracts.py` performs three checks:

1. every positive example validates under JSON Schema Draft 2020-12 with date-time format
   checking;
2. every schema-negative mutation becomes invalid under its declared schema;
3. every semantic-negative record set remains individually schema-valid but fails its named
   cross-record invariant.

The repository validator invokes this check so the vectors run in the existing Python 3.11 and
3.12 CI matrix.

The initial executable catalog contains:

- 11 positive schema examples;
- 15 schema-negative mutations;
- 6 schema-valid semantic failures.

This is the PR A seed set, not the Phase 1 target of at least 100 adversarial cases.

## Fail-closed rules represented now

- unknown or mismatched event/body types are rejected;
- unknown security-relevant fields are rejected;
- unsupported draft versions and DSSE payload types are rejected;
- activity and receipt size bounds are explicit;
- metadata-only memory records cannot carry raw content;
- a provider acknowledgement cannot be upgraded to observed effect success without evidence;
- compensation requires a separately identified authorization;
- the DSSE envelope cannot carry packet-supplied issuer or algorithm trust fields;
- core profiles remain cumulative while experimental capability results are reported separately;
- duplicate events, duplicate per-run sequence, cross-case or cross-tenant activity, broken hash
  continuity, and substituted receipt reconciliation fail semantic validation.

## Deliberately unresolved

JSON Schema cannot establish hash correctness, canonicalization, authentic identity, trusted
time, key trust, append-only storage, policy correctness, or external effect. These require
trusted runtime construction and independent verification.

The following remain future work and must not be inferred from these fixtures:

- canonical hash inputs and independently computed example digests;
- DSSE pre-authentication encoding, real development signatures, algorithm selection, trust
  bundles, rotation, and revocation vectors;
- delegation-grant narrowing against a parent grant;
- complete activity-family coverage and authenticated envelope construction;
- idempotency-state validation, unknown-effect retry policy, and compensation execution;
- S0 runtime behavior, durable journal/outbox, backup, or restore;
- any authenticated-records, receipted-effect, private-memory, durable-lifecycle, S1, S2, or S3
  claim.

## Promotion rule

These files may be revised incompatibly while labeled `0.1-draft`. Promotion requires accepted
decisions, canonicalization and compatibility rules, expanded positive and negative vectors,
cross-language verification, an explicit capability identifier, and maintainer approval. It
must not silently modify an existing protocol profile.
