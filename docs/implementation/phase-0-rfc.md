# Phase 0: Minimum Implementable Full Agentic Reference Architecture

Status: **proposal**. Tracking issue: [#35](https://github.com/DigiTrans-App/provable-agent-reference/issues/35).

## Decision sought

Approve an informative implementation architecture and delivery playbook that extends the
bounded v0.3 control chain into a deployable, full agentic system without changing the current
candidate protocol.

## Problem

The reference implementation demonstrates deterministic compilation, verification, approval,
exact-use authorization, audit reconstruction, and offline packet verification. An enterprise
team still has to invent production identity, durable state, key custody, agent and tool event
capture, multi-agent causality, external-effect receipts, operations, and deployment.

That gap makes the project useful as a framework but not yet sufficient as an implementable
reference architecture.

## Outcome

An independent team should be able to:

1. deploy a local reference environment without a model-provider credential;
2. connect any agent runtime through a bounded adapter;
3. attribute every agent, delegation, tool, approval, and external-effect event to a trusted
   run context;
4. execute the current compile-to-reconstruct control chain;
5. issue an authenticated assurance packet without exposing credentials or private reasoning;
6. verify the packet with a separate implementation;
7. revoke or supersede a still-valid authorization while preserving history;
8. operate the system with documented recovery, retention, and incident procedures.

## Scope

Phase 0 specifies:

- logical actors, trust zones, control points, and agentic activity;
- minimum service, API, event, storage, identity, signing, and operational contracts;
- a local deployment and an AWS reference mapping;
- an implementation playbook, team responsibilities, maturity gates, and pilot criteria;
- candidate future profile boundaries and conformance work.

## Full-agentic definition

For this project, a full agentic architecture covers more than generated content. It accounts
for:

- a goal or work request;
- an agent's structured proposal and declared limitations;
- parent-child delegation and scoped authority;
- model, tool, API, data-source, and memory interactions;
- policy checks before consequential actions;
- human review, interruption, and accountable approval;
- external side effects and provider receipts;
- reconciliation of intended and observed outcomes;
- portable assurance, expiry, revocation, and supersession.

It does **not** require or retain private chain-of-thought. Structured intent, selected evidence,
policy rationale, observed results, and receipts are the accountability surface.

## Relationship to v0.3

The v0.3 candidate remains the protocol authority for records through `reconstructed`. Phase 0
uses its invariants unchanged and treats later agentic states and records as design proposals.
New normative records require their own RFC, schemas, profile identifiers, migration behavior,
and conformance vectors.

## Reference use case

The first executable workflow should be a synthetic vendor-assurance response:

1. an orchestrator receives a customer question;
2. specialist agents collect authorized policy and control evidence;
3. a drafting agent proposes a response;
4. trusted controls compile and verify claims;
5. an authenticated reviewer approves the exact response;
6. the authorizer permits one customer, purpose, channel, and validity window;
7. a delivery adapter emits the exact bytes and records the provider receipt;
8. a packet is independently verified and later revocable or supersedable.

This use case exercises multi-agent delegation, evidence collection, human control, and an
external effect while remaining safe to run with synthetic data.

## Deliverables and exit criteria

Phase 0 is complete when:

- this document set is reviewed for internal consistency;
- each logical component has an owner, contract, inputs, outputs, and failure behavior;
- the reference deployment distinguishes mandatory behavior from AWS-specific products;
- the playbook defines security, privacy, reliability, conformance, and pilot gates;
- proposed normative additions are explicitly separated from informative implementation detail;
- unresolved design questions are tracked before Phase 1 code begins.

## Non-goals

- claiming production readiness or certification;
- defining a hosted DigiTrust product architecture;
- selecting one required model provider or agent SDK;
- proving model reasoning, truth, or source completeness;
- storing prompts, private reasoning, secrets, or unrestricted tool payloads by default;
- requiring microservices when the logical boundaries can be preserved in a modular deployment.

## Phase 0 decision disposition

The five architecture questions are resolved as proposed directions in the
[Phase 0 design decisions](phase-0-decisions.md):

- one record per security-relevant boundary transition;
- a DSSE-style packet envelope with verifier-pinned issuer trust;
- a portable execution receipt that separates submission from observed effect;
- metadata-and-commitment-first memory evidence;
- storage assurance reported separately at levels S0 through S3.

These directions authorize experimental Phase 1 design, not protocol claims. Each normative
extension still requires an accepted RFC, schema, canonicalization rules, positive and negative
vectors, migration behavior, and independent review.

The remaining Phase 1 scoping choice is implementation sequencing. The recommended order is a
Python reference control plane and synthetic adapter first, followed immediately by a
separately maintained TypeScript verifier before any stable interoperability claim.
