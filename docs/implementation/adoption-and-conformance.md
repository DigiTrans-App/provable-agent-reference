# Adoption, conformance, and maturity gates

Status: **informative Phase 0 proposal**.

## Maturity model

| Level | Name | Demonstrated capability | Explicit limitation |
|---|---|---|---|
| 0 | Library evaluation | Existing deterministic control chain runs locally | No deployment or identity assurance |
| 1 | Reconstructable sandbox | Agent/tool events and complete synthetic packet reconstruct offline | Synthetic identities and development keys |
| 2 | Authenticated non-production | Workload/human identity, durable stores, signing, revocation, recovery | Not approved for production effects |
| 3 | Controlled pilot | One bounded workflow, shadow mode, independent verifier, operational gates | Limited scope; not general certification |
| 4 | Enterprise implementation | Tenant isolation, production IAM/KMS, receipts, SLOs, incident and lifecycle controls | Assurance limited to declared profiles and trust anchors |
| 5 | Federated ecosystem | Cross-organization issuers/verifiers, portable trust discovery and revocation | Requires governance and profiles not yet specified |

Passing a level is an internal implementation claim unless independently evaluated. It is not
a certification, legal conclusion, or statement that model outputs are correct.

Storage behavior is reported separately using the proposed
[S0-S3 storage assurance levels](decision-proposals/0007-storage-assurance-levels.md); it is not
inferred from protocol or maturity level alone.

## Phase 1 acceptance

The minimum deployable reference should demonstrate Levels 0 and 1:

- one-command local startup without external credentials;
- multi-agent synthetic vendor-assurance workflow;
- bounded agent, delegation, memory, tool, policy, and effect events;
- existing v0.3 control-chain behavior through reconstruction;
- development signature envelope and explicit limitations;
- execution receipt, reconciliation, revocation, and supersession demonstrations;
- deterministic reset and repeatable test dataset.
- a separately implemented TypeScript verifier using published contracts and vectors.

## Phase 2 acceptance

- second runtime adapter outside the initial provider/runtime family;
- second-language verifier maintained independently from the Python builder;
- portable positive and negative vectors;
- signature, receipt, revocation, replay, and downgrade tests;
- machine-readable conformance report with exact source and environment provenance;
- migration behavior for every changed schema or hash input.

## Pilot gates

A non-production or shadow pilot requires:

- authenticated identities and managed keys;
- customer-approved data inventory and retention policy;
- no unrestricted credential or network access by agents;
- policy-gated tool gateway and disabled-by-default effect destinations;
- human review for Tier 2 and Tier 3 activity;
- backup/restore, key compromise, revocation, and unknown-effect exercises;
- named workflow owner, security owner, on-call owner, and stop authority;
- independent verification results and unresolved limitations accepted in writing.

## Stable architecture gates

In addition to the v1.0 protocol gates, an implementable stable reference architecture should
have:

- two materially different deployments or one deployment reproduced by an independent team;
- one independently maintained verifier;
- one non-OpenAI runtime adapter;
- 100+ synthetic and adversarial cases across all trust boundaries;
- published performance and recovery benchmarks with reproducible methods;
- compatibility, key-rotation, revocation, and schema-migration procedures;
- deployment hardening, incident, retention, deletion, and decommission runbooks;
- a completed release-candidate feedback period with material findings resolved or disclosed.

## Practical ceiling

The project can evolve into a provider-neutral assurance and transaction-control layer for
multi-agent systems. It can support portable evidence packets, governed delegation,
capability-based tool use, authenticated approvals, exact external effects, independent
verification, and cross-organization audit exchange.

It should not claim to provide universal agent safety, prove factual correctness, reveal or
validate private model reasoning, guarantee source completeness, replace domain regulation, or
certify an organization. The strongest honest claim is narrower and valuable: under declared
trust anchors and profiles, specified agent actions and decisions are attributable,
integrity-bound, policy-controlled, reconstructable, and independently verifiable.

## Recommended product boundary

The public reference should include protocol, schemas, reference services, local/AWS examples,
synthetic workflows, adapters, verifier, conformance kit, and runbooks. Managed DigiTrust may
add enterprise tenancy, connectors, policy packs, workflow administration, managed key and
evidence operations, dashboards, support, and compliance-specific mappings.

Keeping this boundary prevents a public conformance claim from depending on proprietary hosted
behavior while preserving a clear path from evaluation to a supported enterprise product.
