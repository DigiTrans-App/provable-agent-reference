# Internal architecture and security pre-review

Review status: **complete with limitations**.

Reviewed scope: Phase 0 implementation documents and decisions through branch revision
`a7f8bf0`. This is a maintainer-side pre-review, not the independent architecture/security
review required for acceptance.

## Review method

The review challenged trust-source separation, authorization narrowing, causal reconstruction,
privacy minimization, signature semantics, external-effect claims, storage claims, retry
behavior, profile composition, production overclaiming, and dependency on the v0.3 candidate.

## Findings and disposition

| Severity | Finding | Disposition |
|---|---|---|
| High | One cumulative future profile sequence would force unrelated memory, effect, or lifecycle capabilities and encourage inflated claims | Corrected: keep a cumulative core ladder and report optional capabilities separately pending a normative composition RFC |
| High | Calling a custom envelope with detached payload and extra signature fields DSSE-compatible would be ambiguous | Corrected: use the standard DSSE envelope shape with embedded canonical payload; trust metadata remains external and verifier-pinned |
| Medium | Provider acknowledgement could be mistaken for proof of effect | Already controlled: receipt separates submission and effect status; `unknown` blocks unsafe retry |
| Medium | Memory hashes could be represented as anonymous | Already controlled: ordinary digests are not anonymity; sensitive production values require reviewed keyed commitments and disclosure policy |
| Medium | Storage configuration could be inferred from packet conformance | Already controlled: S0-S3 are separate deployment-assurance reports, not packet claims |
| Medium | Signed packet could be read as authenticating embedded humans, tools, or evidence sources | Corrected: issuer signature authenticates only the issuer statement; role-specific records need separate profiles |

## Threat-control result

| Threat | Phase 0 control | Residual limitation |
|---|---|---|
| Confused deputy / authority expansion | Parent-bound delegation and strict capability narrowing | No schema or enforcement code yet |
| Cross-tenant substitution | Trusted scope on every envelope and negative-test requirement | Deployment isolation not implemented |
| Forged tool result or receipt | Correlation, action binding, adapter evidence, independent reconciliation | Provider evidence quality varies |
| Replay or duplicate effect | Operation/attempt split, stable idempotency binding, consumption record | Provider idempotency may be unverifiable |
| Stale approval/authorization | Exact hashes, validity, mutation invalidation, revocation | Trusted time profile not defined |
| Key substitution / trust on first use | Verifier-pinned trust bundle, unique key IDs, role metadata | Algorithm and metadata profiles remain draft |
| Memory disclosure / poisoning | Metadata-first access, keyed commitments, scope and evidence validation | Commitment construction remains research |
| Journal deletion / reconstruction gaps | S0-S3 controls and signed checkpoints | Packet cannot prove producer completeness |
| Excessive telemetry / private reasoning capture | Allowlisted events; private chain-of-thought prohibited | Adapters require continuing privacy review |

## Phase 1 eligibility

The design is suitable for an **experimental synthetic Phase 1 implementation** provided that:

- all new identifiers and schemas are labeled draft and non-normative;
- no production identity, signature, receipt, storage, or external-effect claim is made;
- the reference configuration cannot reach a production destination;
- all security-relevant mutations and negative cases are implemented before adding a live
  provider adapter;
- the TypeScript verifier is developed from the written contracts and vectors, not by porting
  Python behavior blindly.

## Residual blockers for acceptance

- independent architecture/security review;
- disposition and rebasing of PR #28;
- normative RFCs for profile composition, activity records, signatures, receipts, and durable
  lifecycle;
- cross-language canonicalization and signature vectors;
- implementation threat-model update tied to actual services and infrastructure;
- pilot-specific identity, privacy, legal, retention, incident, and operational review.

## Conclusion

No Phase 0 design issue blocks synthetic implementation planning after the two corrections
above. This result does not satisfy the independent-review gate and does not authorize merge,
stable release, production use, or external effects.
