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

## Out of scope for v0.1

- secure identity proofing;
- authenticated digital signatures;
- HSM/KMS-backed key custody;
- trusted timestamping;
- remote attestation;
- production storage and tenant isolation;
- provider-side model or API guarantees;
- regulated-data compliance certification.
