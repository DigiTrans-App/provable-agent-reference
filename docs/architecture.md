# Architecture

This page describes the implemented v0.2 control flow. The technology-neutral
[Reference Architecture Candidate](reference-architecture-candidate.md) and its
[protocol candidate](spec/README.md) define the proposed v0.3 separation between normative
requirements, the Python reference implementation, adapters, and conformance evaluation.

The framework separates semantic generation from authoritative controls.

```mermaid
flowchart TD
    U[User request] --> A[Agent runtime]
    A -->|SemanticDraft| C[Trusted compiler]
    T[TrustedRunContext] --> C
    E[Authorized EvidenceBundle] --> C
    C --> K[CanonicalCandidate]
    K --> V[Deterministic verifier]
    E --> V
    V -->|pass| H[Human approval]
    H --> X[Exact-use authorization]
    X --> O[Authorized output]
    O --> P[Portable assurance packet]
    K -. hash .-> M[Audit manifest]
    V -. result hash .-> M
    H -. approval hash .-> M
    X -. authorization hash .-> M
```

## Data flow

1. A model or human produces a `SemanticDraft`.
2. A trusted runtime supplies `TrustedRunContext` and an `EvidenceBundle`.
3. `TrustedCompiler` resolves the selected evidence and derives the canonical candidate identifiers and hashes.
4. `DeterministicVerifier` evaluates integrity, evidence, scope, disclosure, and limitation rules.
5. A human decision is bound to the exact candidate and verification hash.
6. `authorize_exact_use` compares purpose, audience, and exact output.
7. `build_audit_manifest` binds the complete control chain.
8. `build_assurance_packet` packages the evidence, records, exact authorized output,
   limitations, and packet binding for offline verification.

```mermaid
sequenceDiagram
    participant Agent
    participant Compiler
    participant Verifier
    participant Human
    participant Authorizer
    Agent->>Compiler: semantic draft
    Compiler->>Verifier: canonical candidate + evidence binding
    Verifier-->>Human: passing verification result
    Human-->>Authorizer: approval bound to candidate hash
    Authorizer-->>Agent: exact-use authorization
```

## Design characteristics

- **Provider-neutral:** core contracts do not require a model SDK.
- **Fail closed:** verification failure cannot produce approval.
- **Deterministic:** canonical JSON and SHA-256 produce stable bindings.
- **Minimal model authority:** models select evidence identifiers and draft semantic content only.
- **Exact-use control:** approved content cannot be silently repurposed or substituted.
- **Auditable:** a manifest reconstructs candidate, verification, approval, and authorization relationships.
- **Portable candidate:** an Assurance Packet carries the complete reconstructable chain and
  exact authorized output for an independent verifier.

## Reference versus production

The reference uses deterministic hashes and in-memory objects. A production deployment should add authenticated identities, durable append-only storage, trusted timestamps, KMS/HSM-backed signatures, policy governance, access controls, monitoring, retention, and independent operational review.
