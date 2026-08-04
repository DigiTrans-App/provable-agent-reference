# Independent validation guide

This guide is for engineers, researchers, security reviewers, and maintainers who want to evaluate the Provable Agent Reference Framework independently.

The objective is not to obtain an endorsement. A useful review should try to reproduce the published behavior, challenge the trust boundary, identify unsupported claims, and document failures or limitations precisely.

## Validation scope

The public validation kit evaluates whether a specific checkout can reproducibly:

- run the deterministic unit and integration tests;
- validate repository schemas, examples, links, version metadata, and secret hygiene;
- pass the local adversarial evaluation suite;
- pass Ruff structural linting;
- run the fully offline framework demonstration;
- bind a report to the checked-out Git commit and, when requested, an annotated release tag;
- verify the published wheel, source distribution, `ARTIFACTS.json`, and `SHA256SUMS` without extracting an archive;
- produce a machine-readable, privacy-bounded JSON report.

The kit does **not** prove source-runtime authenticity, provider-log completeness, production identity, tenant isolation, non-repudiation, or the absence of vulnerabilities. A passing result is a reproducibility signal, not certification.

## Privacy boundary

Use only the public repository, public release files, and synthetic inputs.

Do not put any of the following into a validation report, issue, discussion, or pull request:

- API keys, credentials, tokens, or private keys;
- customer, employee, patient, student, or regulated data;
- private prompts, production traces, proprietary evidence, or confidential architecture;
- unpublished vulnerability details.

The runner replaces repository and home-directory paths and redacts several common credential patterns before retaining bounded output tails. That redaction is defense in depth, not a complete data-loss-prevention system. Review the generated report manually before sharing it.

Report security-sensitive findings through the private process in [`SECURITY.md`](../SECURITY.md), not through the public validation issue form.

## Validate a checkout that contains the kit

For `main` and future release tags that contain `scripts/run_external_validation.py`, the runner can operate in place:

```bash
git clone https://github.com/DigiTrans-App/provable-agent-reference.git
cd provable-agent-reference

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev,openai]'

EXPECTED_COMMIT="$(git rev-parse HEAD)"
python scripts/run_external_validation.py \
  --expected-commit "${EXPECTED_COMMIT}"
```

For a future immutable tag that includes the kit, add `--expected-tag <tag>` after checking out that annotated tag.

The default report path is:

```text
validation-results/independent-validation-report.json
```

The generated directory is ignored by Git in checkouts that contain this kit. The runner exits with:

- `0` when all required checks and requested artifact checks pass;
- `1` when a validation or provenance check fails;
- `2` when the report cannot be written.

Do not use `--allow-dirty` for an independent release reproduction. That option exists for local investigation and records the dirty state, but it weakens the reproducibility claim.

## Validate the immutable v0.2.0 release

The `v0.2.0` tag was published before the Independent Validation Kit was added, so the tagged checkout does not contain the runner. Validate it with two separate checkouts:

- a current **validator checkout** containing the kit;
- an immutable **target checkout** at `v0.2.0`.

From a parent working directory:

```bash
git clone https://github.com/DigiTrans-App/provable-agent-reference.git \
  provable-agent-reference-validator

git clone https://github.com/DigiTrans-App/provable-agent-reference.git \
  provable-agent-reference-v0.2.0

git -C provable-agent-reference-v0.2.0 fetch --tags
git -C provable-agent-reference-v0.2.0 checkout --detach v0.2.0

python -m venv validation-venv
source validation-venv/bin/activate  # Windows: validation-venv\Scripts\activate
python -m pip install -e './provable-agent-reference-v0.2.0[dev,openai]'

python provable-agent-reference-validator/scripts/run_external_validation.py \
  --repository provable-agent-reference-v0.2.0 \
  --output "$(pwd)/v0.2.0-independent-validation-report.json" \
  --expected-tag v0.2.0 \
  --expected-commit 106b91ea790bf96b059d5d60c07f79f16c02eeea
```

This arrangement intentionally runs the public validation logic from the validator checkout while executing the tests, repository checks, evaluations, linting, and demonstration against the separate target checkout. The virtual environment installs the target release, not the validator checkout.

Before relying on the result:

1. verify that the validator checkout came from this public repository;
2. record the validator checkout commit separately in the human report;
3. confirm that the machine-readable report identifies the target commit and annotated tag;
4. review the generated report before sharing it publicly.

The report digest binds the report content, but it does not authenticate the validator code. A future release that includes the kit will permit a single-checkout tagged reproduction.

## Verify v0.2.0 release artifacts

Download these four files from the [v0.2.0 GitHub Release](https://github.com/DigiTrans-App/provable-agent-reference/releases/tag/v0.2.0) into one directory:

```text
provable_agent_reference-0.2.0-py3-none-any.whl
provable_agent_reference-0.2.0.tar.gz
ARTIFACTS.json
SHA256SUMS
```

Using the two-checkout setup above, run:

```bash
python provable-agent-reference-validator/scripts/run_external_validation.py \
  --repository provable-agent-reference-v0.2.0 \
  --output "$(pwd)/v0.2.0-independent-validation-report.json" \
  --expected-tag v0.2.0 \
  --expected-commit 106b91ea790bf96b059d5d60c07f79f16c02eeea \
  --release-dir /path/to/downloaded-release-assets \
  --require-artifacts \
  --expected-artifact-version 0.2.0
```

Artifact validation checks:

- the exact expected file set;
- SHA-256 values in `SHA256SUMS`;
- hashes and byte sizes in `ARTIFACTS.json`;
- wheel project name, version, metadata, and public package presence;
- source-distribution project structure and required public files;
- path traversal and absolute-path indicators in archive member names.

The runner does not claim that SHA-256 checksums authenticate the publisher. They detect content changes relative to the published manifests. Publisher authentication and stronger provenance require an additional signing or attestation mechanism.

## Report structure

The JSON report conforms to [`independent-validation-report.schema.json`](../schemas/independent-validation-report.schema.json) and includes:

- project name and version;
- Git commit, exact tags, dirty-tree state, and optional annotated-tag details;
- a limited operating-system and Python environment summary;
- each required command, return code, duration, status, and bounded sanitized output tail;
- optional release-artifact verification results;
- explicit errors and limitations;
- `report_sha256`, calculated from the canonical report content before the digest field is added.

The report digest identifies one report document. It is not a signature, identity proof, trusted timestamp, or guarantee that the reviewer executed the commands honestly.

## Manual technical review

Automation is only the first part of an independent review. Reviewers should also examine:

### Trust boundary

- Can model- or runtime-authored input override tenant, case, run, timestamp, classification, approval, or authorization scope?
- Are identity and authoritative scope derived or checked by trusted deterministic code?
- Can a failing verification result reach approval or exact-use authorization?
- Are candidate, approval, authorization, and audit records bound to the intended hashes and context?

### Evidence semantics

- Does the framework distinguish evidence integrity from evidence authenticity and completeness?
- Does it report unavailable runtime evidence instead of reconstructing missing facts heuristically?
- Could evidence be replayed across tenants, cases, runs, candidates, purposes, or audiences?
- Are ordering and canonicalization assumptions explicit and testable?

### Privacy and disclosure

- Does the Codex adapter retain raw prompts, commands, paths, outputs, identifiers, tool payloads, or multi-agent content unexpectedly?
- Are credential-like values rejected before hashing?
- Are direct hashes described accurately as integrity references rather than anonymization?
- Could predictable or low-entropy values be recovered through dictionary comparison?

### Failure behavior

- Do malformed, oversized, incomplete, duplicate, or contradictory events fail closed?
- Can an unmatched send be misrepresented as completed delivery?
- Are unsupported event types ignored or reported without silently becoming evidence?
- Are limitations visible to downstream reviewers?

### Reuse and interoperability

- Is the provider-neutral core usable without an OpenAI runtime dependency?
- Is the runtime-adapter boundary narrow enough to support another agent framework?
- Which schema, compatibility-vector, or conformance changes would be required for another runtime?

## Documenting findings

Use [`docs/validation-report-template.md`](validation-report-template.md) for the human review. A useful finding should contain:

1. the exact tag or commit;
2. the relevant environment and command;
3. a minimal synthetic reproduction;
4. expected and observed behavior;
5. trust-boundary or assurance impact;
6. whether the finding is a defect, documentation gap, research question, or non-goal;
7. a proposed test, documentation correction, or narrowly scoped remediation when possible.

For non-sensitive results, open the **Independent validation result** issue form. A documentation correction, test case, adapter improvement, or focused implementation may instead be submitted as a pull request.

A review is valuable even when every automated check passes. Clearly stated limitations, ambiguous claims, negative results, and unsuccessful integration attempts are all useful evidence for maintainers and future reviewers.
