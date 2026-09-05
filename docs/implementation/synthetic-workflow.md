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

This slice does not yet claim the complete PR C outcome. Durable activity persistence, simulated
Tier 3 effect receipts, unknown-outcome reconciliation, revocation, supersession, packet export,
and reconstruction remain acceptance work.
