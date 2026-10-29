# Proposed decision 0007: Report storage assurance separately by level

Status: **proposed**, not an accepted ADR.

## Context

An offline packet can prove internal bindings but cannot prove that the producer operated an
append-only database, retained all events, protected backups, or prevented deletion. Storage
claims therefore belong to deployment assurance and must not be inferred from protocol
conformance.

## Proposed decision

Define four storage assurance levels. A deployment reports its level, exact implementation,
test date, exceptions, and limitations separately from packet conformance.

| Level | Required behavior | Suitable stage |
|---|---|---|
| S0: logical journal | Application exposes append-only records, deterministic ordering, idempotent writes, and repeatable synthetic reset | Local reference and synthetic evaluation |
| S1: controlled durable | Separate writer role, application delete/update denied, versioned artifacts, encrypted backup, restore test, audit logging, retention policy | Authenticated non-production |
| S2: retention enforced | S1 plus WORM/retention lock for finalized packets and receipts, protected journal checkpoints, legal-hold path, key/role separation, tested recovery | Controlled production pilot and enterprise use |
| S3: externally witnessed | S2 plus independently operated timestamp, transparency log, or equivalent external checkpoint witness | Federated or high-assurance ecosystem |

Product names are not requirements. Equivalent controls may satisfy the behavior.

## Scope by artifact

- Mutable workflow state may remain transactional and updateable, but every consequential
  transition is journaled immutably.
- Finalized candidates, decisions, authorizations, receipts, packets, revocations, and
  supersession records are immutable versions.
- Evidence content follows classification and retention policy; deletion appends status and
  affects future verifiability rather than rewriting historical claims.
- Backups, replicas, exports, and key metadata are included in retention and deletion analysis.

## Integrity checkpoints

At S1 and above, the journal periodically creates a signed checkpoint over an ordered range of
event hashes and sequence bounds. Checkpoints detect later gaps or reordering under the signer
and storage assumptions. They do not prove that omitted events were ever observed.

S3 publishes or submits checkpoints to an independently controlled witness. The witness is a
future interoperability component, not a Phase 1 dependency.

## Verification evidence

A storage-assurance report identifies:

- level and scope;
- exact services/configuration revisions without secrets;
- writer, reader, administrator, backup, and key roles;
- retention and deletion settings;
- last backup/restore, access-control, immutability, and recovery test results;
- checkpoint range and signature information;
- exceptions, manual controls, and limitations.

Self-issued reports are labeled as such. They are not embedded as proof that a deployment
actually maintained every control for the packet's lifetime.

## Phase gates

- Phase 1 synthetic reference: S0 required.
- Authenticated non-production maturity Level 2: S1 required.
- Any controlled production effect: S2 required unless a documented risk decision narrows the
  claim and the packet states the limitation.
- Federated trust: S3 is a research and later-profile target.

## Required negative tests

- application role can update or delete finalized records;
- restored database omits journal/artifact/key metadata dependencies;
- retention lock can be shortened by the normal application role;
- checkpoint skips, reorders, or duplicates events;
- deleted evidence leaves a packet appearing fully verifiable;
- storage level is presented as protocol conformance or certification;
- administrative bypass is unlogged or unreviewed.

## Affected protocol versions

None. Storage assurance remains a deployment report unless a future protocol explicitly binds
a signed, independently verifiable storage attestation.
