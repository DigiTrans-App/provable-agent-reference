# Decision 0008: Require validated string keys before canonical serialization

Status: **accepted** by maintainer John Agbekponou on 2026-10-30 UTC.

RFC: [#51](https://github.com/DigiTrans-App/provable-agent-reference/issues/51).
The implementation accompanies this ADR; its public PR is tracked from the RFC.

## Context

Python's JSON encoder converts several non-string dictionary key types to strings,
collapsing distinct typed inputs before hashing. The core canonical helper and the
control-plane store's duplicate serializer must enforce the same accepted JSON input
domain. This is an input-conversion ambiguity, not a SHA-256 collision; no authorization
bypass has been demonstrated.

## Decision

Reject every non-string object key with `TypeError` before canonical serialization or
hashing, including dictionaries nested within lists and tuples. Do not coerce or skip
keys. Preserve canonical text, UTF-8 bytes, and digests for valid accepted inputs.

Use the shared validated serializer in the store so it also rejects NaN and infinities
with `ValueError`. Preserve the store's JSON-only hash wrapper and rejection of raw
bytes, and preserve the core helper's existing raw-bytes hashing path.

Retain the JSON wire contract and protocol identifier `0.3.0-candidate.1`. The narrower
Python input domain must be documented in the next package release, which must use a
new version. This source change does not issue a package release or deployment.

## Consequences

Malformed inputs fail before producing trusted digests. Exact-use authorization can
raise `TypeError` for malformed output instead of returning an output-mismatch record.
Key validation takes precedence over circular-input detection when invalid keys are
also present. The iterative traversal adds a pass over reachable containers without
copying them or introducing a separate recursion limit.

Valid finite, string-keyed records retain their hashes. Historical key coercion cannot
be detected or reversed from serialized JSON alone. No automatic normalization,
rehashing, database migration, or claim about production data follows from this decision.

## Evidence and review

Reviewed local implementation: `3e4d0d3c7832a28c5750f62d4c42560cca7e4417`, including
Kiro's core fix and the control-plane store follow-up. Python 3.11 and 3.12 each passed
149 tests with five existing PostgreSQL integration skips. Measured property runs
passed 100 and 1,000 generated examples per property. Compatibility comparisons found
no differences across 5,529 fixed/generated values and 25 committed JSON artifacts.

Tests: [key validation](../../tests/test_canonical_key_validation.py),
[canonicalization properties](../../tests/test_property_canonicalization.py), and
[store validation](../../tests/test_store_canonicalization.py).
Conformance artifacts: [record examples](../../examples/records/),
[DSSE vectors](../../vectors/dsse/), and
[development trust bundle](../../trust/development-trust-bundle.json).

John explicitly approved public disclosure, this decision, and a one-time
independent-review exception limited to the new F-2 implementation PR, with squash
merge contingent on all required GitHub checks passing on its final head. This does
not waive CI, change governance for other work, or count automated validation as a
named human approval. The exception and final check results must be recorded in the PR.

Issue [#11](https://github.com/DigiTrans-App/provable-agent-reference/issues/11) remains
open for its separate remaining acceptance review.
