# Phase 1 implementation threat model and privacy inventory

Status: **self-reviewed synthetic implementation inventory**. Independent review remains recommended before stable protocol promotion and required before any non-synthetic pilot.

## Trust zones and authorities

| Zone | Trusted responsibility | Untrusted or bounded input |
|---|---|---|
| Agent runtime | None of the authoritative identity or authorization fields | Questions, draft meaning, evidence selections |
| Memory/tool adapters | Enforce grants, scope, budgets, minimization | Queries and provider-shaped results |
| Control plane | Tenant/case/run identity, capability grants, state transitions, journal and outbox | Agent and adapter proposals |
| Human control | Exact candidate decision and rationale | Presentation and recommendation |
| Effect gateway | Exact-use binding, single consumption, receipt semantics | Provider acknowledgement and observations |
| Packet/signature verifier | Canonical bytes, hashes, pinned issuer key/role/status | Envelope and packet transport |

## Threat-control inventory

| Threat | Implemented control | Residual limitation |
|---|---|---|
| Cross-scope substitution | Trusted scope on records plus tenant/case/run negative tests | Local S0 administrators remain trusted |
| Capability escalation | Parent-bound multidimensional attenuation, expiry and budget checks | Synthetic identities; no enterprise IdP |
| Activity deletion or reordering | Contiguous sequence and previous-hash verification | No external transparency witness |
| Memory disclosure or poisoning | Scope checks, minimized results, evidence binding, no raw memory export | Ordinary hashes are not anonymous or secret |
| Stale or mutated approval | Exact candidate and verification bindings | Synthetic reviewer identity |
| Duplicate or unsafe effect | Single consumption, fixed local target, receipt/reconciliation split | No live provider idempotency evidence |
| Acknowledgement upgraded to success | `not_observed` semantics until separate observation | Provider evidence remains synthetic |
| Key substitution | Verifier-pinned Ed25519 key metadata and strict role/algorithm/status | Development private key is public |
| False signing-time claim | Verification explicitly reports no trusted signing time | Trusted timestamping is deferred |
| Durability overclaim | S0 self-report remains incomplete | No external immutability or independent attestation |

## Data inventory

| Data class | Example | Handling | Retention/deletion statement |
|---|---|---|---|
| Trusted scope | Synthetic tenant, case, run and actor IDs | Stored in state and immutable records | Reset only through guarded local-synthetic tooling |
| Agent proposal | Question, draft claim, selected reference | Bounded input; never authoritative | Synthetic fixtures only |
| Memory content | Synthetic control text | Used locally to derive evidence; raw text excluded from activity and packet exports | Local process lifetime or synthetic fixture |
| Evidence metadata | ID, classification, source URI, summary, digest | Scope checked and hash bound | Deletion cannot be represented as fully verifiable |
| Activity body | Delegation, memory, tool, policy and lifecycle fields | Allowlisted schema-shaped body | Append-only logical journal at S0 |
| Approval/authorization | Synthetic reviewer, exact hashes, purpose and audience | Trusted deterministic records | Preserved through revocation/supersession |
| Effect metadata | Fixed synthetic target, receipt and reconciliation | No network destination; acknowledgement distinct from observation | Immutable logical record |
| Artifact bytes | Synthetic local bytes | Content-addressed, staged and reconciled | Local volume; unavailable/corrupt state fails closed |
| DSSE material | Public development key, canonical packet, signature | Pinned trust bundle; development-only | Historical test material may remain public |
| Validation metadata | OS, runtime, architecture, counts and benchmark | No path, prompt, secret, customer identifier or raw output | Generated locally; self-issued |

## Prohibited data

Customer data, credentials, production identity tokens, private keys, private chain-of-thought, production endpoints, commercial policy packs, and proprietary DigiTrust implementation details are prohibited. A digest of sensitive input is not treated as anonymization. Any transition beyond synthetic data requires a new privacy, retention, legal, identity, incident-response, and operational review.
