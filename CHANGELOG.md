# Changelog

All notable changes to this project will be documented here.

## [Unreleased]

## [0.2.1] - proposed, not yet published

Security maintenance release for the 0.2 line, prepared from v0.2.0. It contains only the two fixes below and the release controls that publish them. Record formats and hashes for valid inputs are unchanged.

### Security

- `verify_audit_manifest` now reports `authorization_output_mismatch` when an authorization record marked as authorized carries an `output_hash` that differs from the hash of the candidate's approved output (its assurance statement and limitations). Before this change, standalone audit verification could report such a record as valid if the substituted hash was recomputed into the record's own hash, including when the consumer rebuilt the records from strictly JSON-serialized data. Denied records still describe the output that was requested and are not compared with the approved output. The fix is a backport of the audit change in PR #29.
- `canonical_json` and `sha256_uri` now reject object keys that are not strings, at every nesting depth, with `TypeError`. Previously the serializer converted integer, boolean, `None`, and float keys to strings, so `{1: "x"}` and `{"1": "x"}` produced the same canonical text and digest. This is input-representation ambiguity, not a SHA-256 collision. Non-finite numbers (`NaN`, `Infinity`, `-Infinity`) are rejected with `ValueError`. The fix is a backport of the canonical-key change in PR #52 and the non-finite rejection from PR #24.

### Changed

- Release controls from `main` are carried to the 0.2 maintenance line: the release-line allow-list, the hardened release verifier, explicit latest and prerelease labelling, and CI that runs on pull requests into `release/*.*.x`.
- The `dev` extra now includes `pip-audit`, which the validation and release workflows use.

### Compatibility

- Records built from string-keyed, finite-number inputs keep identical canonical text, digests, record formats, and hashes as v0.2.0.
- Callers that pass non-string keys or `NaN`/`Infinity` to `canonical_json`, `sha256_uri`, or `authorize_exact_use` now receive an exception instead of a digest.
- `verify_audit_manifest` can now return `authorization_output_mismatch` for tampered authorized records. Valid records are still accepted.

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
