# Normative change process

Architecture, protocol, schema, canonicalization, profile, security, and compatibility changes
use a public issue-first process.

## RFC requirement

A proposal is an RFC when it changes a normative requirement, trust boundary, hash input,
lifecycle transition, profile, compatibility promise, or public assurance claim. The RFC issue
must include:

1. problem and motivation;
2. trust-boundary impact;
3. proposed normative requirements;
4. alternatives and rejected options;
5. compatibility and migration behavior;
6. privacy and security considerations;
7. test vectors and failure cases;
8. implementation and rollout plan;
9. unresolved questions and explicit non-goals.

Implementation SHOULD wait until reviewers agree that the problem and intended invariants are
clear. Experimental code MAY accompany an RFC when it is isolated and labeled non-normative.

## Architecture decision records

An accepted RFC produces a concise ADR under `docs/decisions/` before or with implementation.
The ADR records status, context, decision, consequences, protocol versions affected, and links
to the RFC, implementation, and conformance vectors. A later decision supersedes rather than
rewrites an accepted ADR.

## Review and acceptance

Normative changes require the review policy in `GOVERNANCE.md`, all required checks, resolved
conversations, compatibility evidence, and exact-head approval. Security-critical changes must
receive security-relevant independent review. Candidate status does not waive fail-closed tests
or public disclosure of limitations.

## Stability

A candidate becomes stable only after:

- at least two independent technical reviews;
- one second-language verifier or equivalent independent implementation;
- published positive and negative conformance vectors;
- documented migration behavior;
- no unresolved critical security finding;
- a release candidate period with public feedback.
