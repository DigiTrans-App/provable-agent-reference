# ADR 0009: Protected maintenance-line releases

Status: **Accepted** on 2026-10-30 by founding maintainer John Agbekponou.
Acceptance and the bounded implementation-review exceptions are recorded in
[RFC #54](https://github.com/DigiTrans-App/provable-agent-reference/issues/54).

## Context

The latest published minor requires security maintenance while main includes unreleased
compatibility changes. The main-only release ancestry gate cannot authorize a backport.

## Decision

Protected main holds the authoritative `.github/release-lines.json`. Route tags by MAJOR.MINOR
to main or the exact approved maintenance branch. Verify tag format, package version, release
notes, tag/HEAD identity, branch containment, selected allow-list agreement and stable-patch
ordering. A maintenance release must descend from its pinned base. Publish explicit
prerelease/Latest flags under one cross-line `release-publication` concurrency group.

Approve `release/0.2.x` rooted at immutable v0.2.0 commit
`106b91ea790bf96b059d5d60c07f79f16c02eeea`; reserve main for 0.3. Bootstrap under a temporary
admin-only lock, verify permanent PR/status protections, then remove only that temporary lock.
Normal maintenance protection requires two human approvals, strict checks, linear squash
history and no bypass. A one-time review exception does not permit a permanent weakening;
restore normal protection before tagging. CI and exact-head verification remain mandatory.

## Consequences and limits

Supported 0.2 users can receive v0.2.1 without later main features and with valid record
formats/hashes preserved. Each future line addition or retirement requires review. These
controls do not authenticate record producers, replace human review, stop administrators from
editing settings, or coordinate manual/legacy publishers. Operate one authorized release at a
time and verify its artifacts and attestations. Acceptance is not a release or certification.

## Versions and implementation

This decision governs package 0.2 maintenance and the next main release line. It introduces
no protocol or record schema change.

- [Release verifier](../../scripts/verify_release.py)
- [Release workflow](../../.github/workflows/release.yml)
- [Release-line positive/negative tests](../../tests/test_release_lines.py)
- [Metadata and ancestry tests](../../tests/test_release_verification.py)
- [RFC and implementation/release record](https://github.com/DigiTrans-App/provable-agent-reference/issues/54)
