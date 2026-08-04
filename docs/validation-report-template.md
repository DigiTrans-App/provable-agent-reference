# Independent validation report template

Use this template for a human technical review of a tagged release or commit. Remove instructions that do not apply. Do not include credentials, customer data, private evidence, production traces, or unpublished vulnerability details.

## Review metadata

- **Reviewer name or pseudonym:**
- **Affiliation, optional:**
- **Review date:**
- **Repository tag:**
- **Commit SHA:**
- **Python version:**
- **Operating system and architecture:**
- **Installation method:** source checkout / GitHub release wheel / other
- **Machine-readable report SHA-256:**
- **Machine-readable report shared publicly:** yes / no

## Automated reproduction

### Commands executed

```text
Paste the exact commands, excluding credentials and machine-specific secrets.
```

### Result summary

| Check | Result | Notes |
|---|---|---|
| Git provenance and clean checkout | pass / fail / incomplete | |
| Unit and integration tests | pass / fail / incomplete | |
| Repository validation | pass / fail / incomplete | |
| Local adversarial evaluations | pass / fail / incomplete | |
| Ruff | pass / fail / incomplete | |
| Offline demonstration | pass / fail / incomplete | |
| Release artifact verification | pass / fail / not tested | |

### Reproduction problems

Describe installation failures, platform differences, missing instructions, non-deterministic behavior, or other barriers. Include only bounded, sanitized output needed to reproduce the problem.

## Trust-boundary review

### Model and runtime authority

- Can untrusted model or runtime input assign authoritative identity or scope?
- Can it bypass deterministic verification, human approval, or exact-use authorization?
- Are any trusted fields derived from ambiguous or unbounded input?

**Assessment:**

### Evidence binding and replay resistance

- Are evidence, candidate, verification, approval, authorization, and audit records bound to the intended context?
- Could a record be substituted or replayed across tenants, cases, runs, purposes, audiences, or record types?
- Are canonicalization and ordering assumptions sufficiently explicit?

**Assessment:**

### Failure behavior

- Do malformed, oversized, duplicate, incomplete, or contradictory inputs fail closed?
- Are missing capabilities reported as unavailable rather than inferred?
- Can partial lifecycle evidence be misrepresented as completed delivery or execution?

**Assessment:**

## Privacy and disclosure review

- Does any public example or adapter retain raw prompts, commands, paths, outputs, identifiers, tool payloads, or multi-agent content unexpectedly?
- Are credential-like values rejected before hashing?
- Are hashes described as integrity references rather than anonymization?
- Could predictable values be recovered through dictionary comparison?

**Assessment:**

## Interoperability review

- Is the provider-neutral core usable without a model-provider runtime dependency?
- Is the adapter interface sufficiently narrow for another runtime?
- Which semantics, schemas, or compatibility vectors are missing for cross-runtime conformance?

**Assessment:**

## Findings

Create one section per finding.

### Finding: concise title

- **Severity or priority:** informational / low / medium / high / critical
- **Type:** defect / documentation gap / security concern / research question / non-goal
- **Affected tag or commit:**
- **Relevant files or symbols:**
- **Synthetic reproduction:**
- **Expected behavior:**
- **Observed behavior:**
- **Trust or assurance impact:**
- **Suggested test or remediation:**
- **Public disclosure appropriate:** yes / no / private security report required

## Claims assessment

Identify any project claim that appears:

- supported by code and tests;
- supported but insufficiently documented;
- ambiguous;
- overstated;
- unsupported;
- outside the stated scope.

**Assessment:**

## Overall conclusion

Choose one and explain:

- Reproduced with no substantive findings.
- Reproduced with documented limitations or improvements.
- Partially reproduced; blockers remain.
- Not reproduced; the result appears to be a project defect.
- Not reproduced because of environment or documentation limitations.

A positive conclusion is not an endorsement or certification. A negative conclusion should be accompanied by the smallest synthetic reproduction available.
