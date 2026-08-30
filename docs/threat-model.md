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
| Assurance packet substitution | Packet, bundle, record, manifest, and exact-output bindings are recomputed |
| Profile inflation | Claims must be a cumulative prefix of implemented, versioned profiles |
| Authorized output omitted | The packet carries the exact output and recomputes its authorization hash |
| Agent self-approval in governed packets | Approver and agent identifiers must differ |

## Assurance Packet limitations

A valid candidate packet provides deterministic integrity and linkage evidence only under its
declared protocol assumptions. It does not authenticate the producer or approver, prove source
or runtime completeness, establish trusted time, demonstrate that an external action occurred,
or make predictable hashes confidential. Unknown protocol versions, invalid profile sequences,
missing evidence, output substitution, and any broken cross-record binding fail closed.

## Out of scope for v0.1

- secure identity proofing;
- authenticated digital signatures;
- HSM/KMS-backed key custody;
- trusted timestamping;
- remote attestation;
- production storage and tenant isolation;
- provider-side model or API guarantees;
- regulated-data compliance certification.
- durable emission, consumption, expiry, revocation, and supersession records.
