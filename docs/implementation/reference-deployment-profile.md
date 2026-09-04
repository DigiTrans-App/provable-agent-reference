# Minimum reference deployment profile

Status: **informative Phase 0 proposal**. Profile label: `par-deploy.reference.0.1`.

The label identifies this document version; it is not a protocol conformance claim and must not
appear in candidate Assurance Packets.

## Behavioral requirements

A reference deployment must provide:

- authenticated human and workload identities;
- tenant- and case-scoped authorization at every service boundary;
- durable, append-only activity and control-chain records;
- evidence and packet object storage with integrity metadata;
- policy evaluation before delegation, data access, tool use, approval, and external effects;
- asymmetric signing with key identifiers, rotation, and revocation procedures;
- idempotent transitions and external-effect execution;
- auditable approval, expiry, revocation, and supersession paths;
- independent packet export and verification;
- logs, metrics, traces, backup, restore, and incident procedures.

## Logical components

| Component | Responsibility | Fail-closed behavior |
|---|---|---|
| API edge | Authenticate, validate size/schema, assign request ID, enforce rate limit | Reject unauthenticated, oversized, replayed, or malformed requests |
| Run coordinator | Create trusted run context and parent-child causality | Reject unknown tenant, parent, policy, or capability grant |
| Adapter boundary | Normalize bounded runtime observations | Mark unsupported or missing observations unavailable |
| Tool gateway | Resolve tool identity, evaluate policy, enforce grant and idempotency | Do not invoke on denied, stale, excessive, or ambiguous requests |
| Evidence service | Resolve scoped evidence and integrity metadata | Reject cross-scope or unresolved evidence |
| Control-chain service | Compile, verify, approve, authorize, reconstruct | Never skip or infer a transition |
| Human review service | Present exact content/evidence/limitations and capture identity-bound decision | Reject stale hashes, self-approval, expired session, or missing rationale |
| Effect executor | Emit exactly one authorized effect and capture provider receipt | Do not execute stale, consumed, mismatched, or revoked authorization |
| Packet service | Build, sign, export, verify, revoke, and supersede packets | Reject invalid chain, key, profile, or packet |
| Policy service | Serve immutable versioned bundles and decisions | Deny when bundle is missing, unsupported, or unverifiable |
| Audit service | Persist ordered records and support reconstruction/export | Surface gaps; never fabricate continuity |

## Storage model

Use three separable stores:

1. **Transactional state:** runs, grants, transition state, idempotency keys, and active policy
   pointers in PostgreSQL-compatible storage.
2. **Append-only journal:** canonical event envelopes and record hashes, protected from normal
   application updates and deletes.
3. **Artifact store:** evidence objects, authorized outputs, packets, schemas, and vectors using
   immutable versions and retention policy.

Every stored object records tenant, case, run, schema version, classification, retention class,
creation source, and content digest. Credentials and encryption keys are references, never
stored in protocol records.

## Identity and signing

- Workloads authenticate with short-lived platform identities.
- Humans authenticate through enterprise OIDC/SSO with phishing-resistant MFA recommended for
  Tier 3 decisions.
- The system records stable subject and issuer identifiers, not only display names or email.
- Signing uses asymmetric keys held by a managed KMS/HSM boundary.
- Packets include issuer, key ID, algorithm, signature, signing time source, and profile.
- Verifiers use an explicit trust configuration and fail closed on unknown, disabled, or
  expired keys.
- Rotation preserves prior public verification material for the applicable retention period.

The exact signature envelope remains a proposed future normative profile.

## Local reference mapping

| Behavior | Local component |
|---|---|
| API/control plane | Containerized reference service |
| Transactional state | PostgreSQL container |
| Queue/outbox | PostgreSQL outbox plus worker |
| Artifact storage | S3-compatible local object store |
| Signing | Development-only ephemeral key provider clearly marked non-production |
| Identity | Local test issuer and synthetic identities |
| Observability | OpenTelemetry collector and local backend |

The local profile must start without external credentials and must never imply production key
or identity assurance.

## AWS reference mapping

| Behavior | Reference AWS service |
|---|---|
| Container runtime | ECS Fargate by default; EKS is an equivalent deployment choice |
| API edge | Application Load Balancer or API Gateway plus WAF where appropriate |
| Transactional state | RDS/Aurora PostgreSQL with encryption and point-in-time recovery |
| Durable queue | SQS, fed by a transactional outbox relay |
| Artifact storage | Versioned S3; Object Lock where retention policy requires it |
| Signing/key custody | KMS asymmetric keys, CloudTrail data/management events |
| Workload identity | IAM task roles with least-privilege resource policies |
| Human identity | External OIDC/SSO mapped to stable subjects and approval roles |
| Secrets | Secrets Manager with rotation where supported |
| Observability | OpenTelemetry plus CloudWatch and optional SIEM export |

AWS product choices are informative. Equivalent behavior may be implemented elsewhere.

## Reliability rules

- A database commit and event publication use a transactional outbox; no dual-write assumption.
- Consumers are at-least-once and idempotent.
- External effects use a deterministic idempotency key and a durable consumption record.
- A timeout produces `unknown` until reconciled; it is never treated as success or safe retry.
- Clock skew and time-source health are monitored.
- Backup restoration is exercised, including packet and key-discovery dependencies.
- Regional recovery documents which identities, keys, stores, and queues are authoritative.

## Operations and SLO starter set

Measure availability and latency separately for ingestion, verification, human review,
authorization, execution, packet issuance, and offline verification. Also measure:

- denied cross-scope access;
- incomplete evidence rate;
- stale approval and authorization rejection;
- duplicate-effect prevention;
- unreconciled effects;
- signature/key lookup failures;
- audit reconstruction success;
- revocation propagation;
- retention and deletion completion.

Numeric SLOs belong to the adopting organization. The reference supplies dashboards and alert
conditions, not universal business targets.

## Minimum security gates

Before any non-synthetic pilot:

- threat model reviewed for the chosen workflow;
- least-privilege access tests pass;
- tenant isolation and cross-run negative tests pass;
- keys, secrets, and logs are scanned and classified;
- backup and restore are demonstrated;
- incident, revocation, and key-compromise exercises are completed;
- no production destination is reachable from the synthetic reference configuration.
