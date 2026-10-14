# Proposed decision 0006: Memory evidence is metadata-and-commitment first

Status: **proposed**, not an accepted ADR.

## Context

Agent memory can contain customer data, secrets, personal information, privileged material,
prompts, or poisoned content. Full capture is unsafe; an opaque statement that memory was used
is insufficient for accountability. Predictable hashes also do not anonymize sensitive text.

## Proposed decision

Record a privacy-bounded memory-access event whose default mode contains metadata, policy
decisions, and keyed commitments—not raw queries or retrieved content. Store permitted content
separately under its original classification and retention policy.

## Memory access fields

- trusted tenant, case, run, actor, purpose, and policy version;
- memory provider, store, collection/namespace, adapter identity, and schema version;
- declared access purpose, allowed classifications, filters, and result limit;
- query commitment and commitment-key reference/version;
- result-set commitment over ordered result references, plus count and truncation status;
- per-result opaque reference, content commitment, source/provenance reference, classification,
  freshness, and integrity status;
- disclosure mode, minimization decision, retention class, access decision, errors, and
  limitations;
- optional separately authorized evidence-object references.

The portable event never contains a commitment key or credential.

## Disclosure modes

| Mode | Portable content | Intended use |
|---|---|---|
| `metadata_only` | Access metadata and commitments | Default operations and privacy-sensitive workflows |
| `reference` | Metadata plus authorized immutable evidence references | Independent review within a shared trust domain |
| `embedded_minimized` | Explicitly approved, minimized evidence excerpt | Offline verification where disclosure is permitted |

Changing mode is a new policy decision and record. It cannot silently expand an existing packet.

## Commitments

Synthetic development data may use ordinary content digests with an explicit limitation.
Production-sensitive values use a keyed commitment or other reviewed construction so predictable
inputs are not exposed to trivial dictionary comparison. Independent verification then requires
authorized disclosure, a verification service, or a separately shared verification secret.

This proposal does not standardize the cryptographic construction; that remains aligned with
the existing keyed-commitment and selective-disclosure research roadmap.

## Trust treatment

Retrieved memory is untrusted evidence. It is subject to scope, integrity, freshness,
classification, disclosure, and prompt-injection controls before it can support a candidate.
Retrieval rank or model confidence is not proof of relevance or truth.

## Retention and deletion

- Content and metadata have separate retention classes.
- Deletion removes content when policy requires it and appends a tombstone/status record; signed
  or approved history is not rewritten.
- Crypto-erasure may be used when legally and operationally appropriate, but its limitations are
  documented.
- A packet that depends on deleted undisclosed evidence becomes unverifiable or limited; it is
  not silently treated as valid.

## Required negative tests

- raw prompt, token, secret, or unrestricted result in metadata-only mode;
- cross-tenant collection or result reference;
- changed query or result order with reused commitment;
- missing truncation or incomplete-result status;
- predictable sensitive value represented as anonymized because it was hashed;
- stale/poisoned memory promoted to trusted evidence;
- disclosure-mode expansion without a new policy decision;
- deletion that rewrites prior journal history.

## Affected protocol versions

None in Phase 0. Memory evidence behavior may become part of a future activity-bound profile;
the cryptographic commitment mechanism requires separate review and vectors.
