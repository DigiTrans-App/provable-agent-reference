# Threat model

## Protected properties

- A model cannot create authoritative identity or approval.
- Evidence references remain within the authorized tenant and case scope.
- Candidate content is bound to the exact evidence bundle and compiler version.
- Verification failure blocks approval.
- Approval is bound to the exact candidate and verification result.
- Authorization is bound to exact purpose, audience, and output.
- Substitution is detectable through deterministic hashes and audit bindings.

## Representative threats

| Threat | Reference control |
|---|---|
| Prompt injection in evidence | Evidence is treated as data; model output remains non-authoritative |
| Unsupported claim | Selected evidence must resolve exactly in the trusted bundle |
| Cross-tenant evidence | Bundle and record scopes must match trusted context |
| Candidate substitution | Candidate hash is recomputed during verification |
| Disclosure violation | Sensitive categories require redaction intent |
| Self-approval | Approval requires a separate human identifier and passing verification |
| Purpose or audience drift | Exact-use authorization compares both fields |
| Output substitution | Output hash and exact structure must match the approved candidate |
| Audit record substitution | Manifest and linked record hashes are independently recomputed |

## Generated security evidence

The property-based suite generates bounded synthetic inputs for canonical JSON ordering and
Unicode handling, candidate and lifecycle-record mutation, evidence insertion/removal/reordering,
cross-tenant and cross-case reuse, purpose/audience/output replay, total-rehash record
substitution, and adapter context changes. CI evaluates at least 100 examples for every property;
an extended local profile evaluates 1,000.

Passing generated tests is evidence that the implemented invariants hold for the explored input
space. It is not a proof of collision resistance, canonicalization equivalence across languages,
source authenticity, signature security, implementation correctness for all possible inputs, or
deployment security. See the [property-testing guide](property-testing.md) for scope and
reproduction instructions.

## Out of scope for the current reference

- secure identity proofing;
- authenticated digital signatures;
- HSM/KMS-backed key custody;
- trusted timestamping;
- remote attestation;
- production storage and tenant isolation;
- provider-side model or API guarantees;
- regulated-data compliance certification.
