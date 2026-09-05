# Synthetic full-agentic workflow

Status: **experimental Phase 1 PR C implementation**. All identities, evidence, memory, tools,
reviewers, and results are synthetic. No network destination or production effect is reachable.

The first PR C slice connects a deterministic evidence specialist to a privacy-bounded memory
adapter and capability-enforcing tool gateway, then feeds the proposed semantic draft into the
existing trusted compiler, deterministic verifier, approval, exact-use authorization, and audit
chain.

The adapters enforce tenant/case scope, expiry, explicit capabilities, result minimization, and
per-agent tool-call budgets. Query and idempotency inputs are stored only as deterministic
development commitments, which provide binding but no anonymity or secrecy. Raw
memory text is used to calculate the evidence digest but is not returned in activity results.
Authoritative run identity and scope always come from `TrustedRunContext`, never an adapter or
agent response.

The orchestrator emits an explicit, bounded delegation to the evidence specialist. Trusted code
wraps delegation, memory, and tool bodies in schema-shaped activity records, assigns scope and
sequence, and creates a contiguous hash chain. PostgreSQL persists the activity batch and one
outbox notification per record in a single transaction; reconstruction recomputes every body and
record hash and rejects gaps or reordered links.

This slice does not yet claim the complete PR C outcome. Simulated Tier 3 effect receipts,
unknown-outcome reconciliation, revocation, supersession, and packet export remain acceptance work.
