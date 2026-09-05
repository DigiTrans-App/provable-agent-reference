# Trust boundary

## Model- or user-authored

- claim text;
- one selected authorized evidence identifier;
- limitations;
- proposed assurance wording;
- content-category declarations;
- redaction intent.

## Trusted-runtime authored or verified

- tenant, case, run, and agent identity;
- purpose, audience, classification, and trusted timestamp;
- evidence records and content hashes;
- canonical claim and candidate identifiers;
- compiler identity and version;
- verification findings and result hash;
- human approver identity and decision;
- exact-use authorization;
- audit manifest bindings.
- Assurance Packet identifiers, lifecycle state, claimed profiles, authorized-output binding,
  and packet hash.

## Rule

No adapter may copy authoritative fields from untrusted model output merely because they appear well formed. Trusted fields must originate from trusted runtime state or be independently resolved and verified.

## Provider adapters

A provider adapter may translate model output into the public `SemanticDraft` contract. It may not bypass trusted compilation, verification, approval, authorization, or audit reconstruction.

## Portable packets

An Assurance Packet builder may package only records that the trusted implementation has
already validated. Packet fields supplied by an untrusted caller do not become authoritative
because they are well formed. An independent verifier must recompute packet, record, evidence,
manifest, and output bindings and reject unsupported protocol or profile claims.
