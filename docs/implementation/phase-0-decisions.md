# Phase 0 design decisions

Status: **proposed for review**. These decisions resolve the implementation questions raised in
[RFC #35](https://github.com/DigiTrans-App/provable-agent-reference/issues/35). They remain
informative until accepted and do not add claims to protocol `0.3.0-candidate.1`.

## Decision summary

| Question | Proposed decision | Phase 1 consequence |
|---|---|---|
| Record granularity | One immutable record per security-relevant boundary transition; attempts remain distinct under one operation | Implement a typed activity journal and causal run graph |
| Signature and key discovery | DSSE-compatible envelope carrying canonical packet bytes; verifier-pinned issuer trust; optional well-known metadata | Implement a development signer and explicit offline trust bundle |
| Portable execution receipt | Separate authorization, submission, provider acknowledgement, observed effect, and reconciliation | Implement a core receipt plus adapter evidence, with `unknown` fail-closed |
| Memory privacy | Metadata and keyed commitments by default; raw content stored separately and disclosed only by policy | Implement privacy modes, purpose binding, minimization, and deletion status |
| Storage immutability | Deployment assurance levels from logical append-only through WORM and external anchoring | Phase 1 targets sandbox Level S0; non-production pilot requires S1 |

## Proposed profile composition

Internal review found that putting every future feature into one cumulative profile sequence
would force workflows to claim capabilities they do not use. The proposal therefore separates:

1. a cumulative core assurance ladder, potentially extended by `par.activity-bound.v1` and
   `par.authenticated-records.v1`; and
2. independently versioned capability results such as `par.capability.receipted-effect.v1`,
   `par.capability.private-memory.v1`, and `par.capability.durable-lifecycle.v1`, each with
   declared dependencies.

The current packet has no capability-results field. Phase 1 reports experimental capability
results only in its conformance report; it does not add them to Assurance Packet claims. A
future protocol RFC must decide the machine-readable composition model.

These identifiers are reserved design labels only. They must not appear in candidate Assurance
Packet claims. Memory privacy is mandatory whenever memory activity is recorded; it is not a
claim that every workflow uses memory. Storage assurance is reported separately because an
offline verifier cannot prove the producer's operational storage controls.

## Phase 1 boundary

Phase 1 may implement experimental versions of these contracts in the synthetic reference
deployment when all of the following are true:

- fields and identifiers are labeled draft and namespaced;
- no future profile is claimed in an exported packet;
- development identities and keys are visibly non-production;
- negative tests cover mutation, replay, cross-scope access, privilege expansion, duplicate
  effects, unknown outcomes, and trust-on-first-use;
- migration or deletion of experimental records is acceptable and documented.

## Promotion rule

A proposal may move into `docs/decisions/` only after the RFC is accepted. Promotion records the
affected protocol version, final schema/vector revisions, compatibility impact, and review
evidence. Later decisions supersede; they do not rewrite accepted history.

## Detailed proposals

- [Activity record granularity](decision-proposals/0003-activity-record-granularity.md)
- [Signature envelope and key discovery](decision-proposals/0004-signature-envelope-and-key-discovery.md)
- [Portable execution receipts](decision-proposals/0005-portable-execution-receipts.md)
- [Privacy-preserving memory evidence](decision-proposals/0006-memory-privacy.md)
- [Storage assurance levels](decision-proposals/0007-storage-assurance-levels.md)
- [Internal architecture and security review](internal-architecture-security-review.md)
