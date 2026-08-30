# Changelog

All notable changes to this project will be documented here.

## [Unreleased]

### Added

- Reference Architecture Candidate, normative lifecycle, cumulative conformance profiles, and RFC/ADR change process.
- Versioned portable Assurance Packet schema, synthetic vector, Python builder, strict loader, and offline semantic verifier.
- Independent validation runner for reproducible offline tests, evaluations, linting, demonstrations, Git provenance, and privacy-bounded JSON reports.
- Optional verification of release wheels, source distributions, `ARTIFACTS.json`, and `SHA256SUMS` without extracting archives.
- Machine-readable independent-validation report schema, human reviewer guide and template, public issue form, and fail-closed test coverage.
- Verifier identity and version bindings in verification results and their deterministic hashes.

### Changed

- Updated the optional OpenAI Agents SDK compatibility range to `>=0.22,<0.23`.
- Migrated package license metadata to the current SPDX expression format.
- Raised the build baseline to a patched Setuptools release and upgraded packaging tools explicitly in CI before auditing dependencies.
- Canonical JSON now rejects non-finite numbers, and the Codex JSONL adapter rejects duplicate object keys, excessive nesting, and oversized aggregate streams.

### Security

- Assurance Packet verification recomputes packet, evidence, output, record, manifest, and deterministic rule bindings; malformed profile claims, self-approval under the governed profile, and semantically false rehashed findings fail closed.
- Packet lifecycle state is limited to `reconstructed`; the reference does not infer emission, delivery, consumption, revocation, or supersession.
- Approval and exact-use authorization now reject candidates whose deterministic hash is invalid.
- Approval validates candidate identifiers and requires verification status to agree with error-level findings.
- Audit reconstruction now validates every candidate, verification, approval, authorization, scope, decision, and reason relationship in the control chain.
- Validation and release workflows now audit the resolved Python environment for known dependency vulnerabilities.

## [0.2.0] - 2026-08-03

### Added

- Versioned runtime evidence adapter interface for optional provider and runtime integrations.
- Experimental Codex Evidence Adapter for privacy-minimized execution and multi-agent lifecycle evidence.
- Synthetic Codex JSONL fixtures, deterministic compatibility vectors, an offline example, documentation, and fail-closed tests.
- Offline compatibility validation for the OpenAI Agents SDK surfaces used by the optional example.
- CodeQL analysis for Python changes and scheduled security scanning.
- Pull-request dependency review with moderate-severity enforcement and dependency Scorecard signals.
- OpenSSF Scorecard analysis with SARIF publication to GitHub code scanning.
- Distribution validation for the source archive and wheel, including version, package-content, and metadata checks.
- A tag-triggered GitHub release workflow that publishes the source distribution, wheel, artifact manifest, and SHA-256 checksums.

### Changed

- The optional `openai-agents` compatibility range now permits `>=0.18.3,<0.20`.
- GitHub Actions are pinned to full commit SHAs and use least-privilege tokens, disabled persisted checkout credentials, bounded job timeouts, and concurrency cancellation.
- The release version is validated across `pyproject.toml`, package runtime metadata, the changelog, and the release-notes document.

### Security

- The Codex adapter rejects malformed JSON, oversized or unbounded inputs, orphan receive events, duplicate terminal events, invalid result contracts, and credential-like material before hashing.
- Free-form prompts, commands, paths, outputs, tool payloads, identifiers, and multi-agent content are not retained by the adapter; relevant values are hash-bound instead.
- Direct SHA-256 hashes remain integrity references, not anonymization, signatures, source authentication, or attestation.
- Automated security checks are documented as triage signals rather than certification or proof that vulnerabilities are absent.

### Compatibility

- Python 3.11 and 3.12 are supported and validated.
- The provider-neutral core retains no runtime dependency on a model provider.
- The v0.1 provider-neutral contracts and pipeline remain available; v0.2.0 adds optional adapter and security-automation surfaces.
- Public examples and release validation remain synthetic, offline, and API-key free.

## [0.1.0] - 2026-07-22

### Added

- Provider-neutral semantic draft and evidence contracts.
- Trusted compiler and deterministic verification engine.
- Exact candidate approval and authorization records.
- Tamper-evident audit manifest reconstruction.
- Synthetic examples, adversarial evaluations, and tests.
- Optional OpenAI Agents SDK integration example.
