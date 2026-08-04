# Security Policy

## Supported versions

Security fixes are applied to the latest released minor version and the `main` branch.

## Reporting a vulnerability

Please use GitHub's **Report a vulnerability** workflow to open a private security advisory. Do not open a public issue for vulnerabilities, exposed credentials, or sensitive data.

Include:

- affected version or commit;
- a minimal synthetic reproduction;
- expected and observed behavior;
- potential impact;
- any proposed remediation.

## Automated security checks

The public repository uses a layered, least-privilege automation baseline:

- **Validation** runs unit tests, repository checks, local adversarial evaluations, linting, the framework demo, and the optional OpenAI Agents SDK compatibility test on Python 3.11 and 3.12.
- **CodeQL** analyzes Python changes on pull requests and pushes to `main`, and runs on a weekly schedule using the extended security query suite.
- **Dependency Review** evaluates dependency changes on pull requests and fails when a newly introduced vulnerability has moderate or greater severity.
- **OpenSSF Scorecard** evaluates repository and supply-chain practices on pushes to `main`, branch-protection changes, and a weekly schedule. SARIF findings are uploaded to GitHub code scanning.

Third-party GitHub Actions are pinned to full commit SHAs and are kept current through Dependabot. Workflow tokens use read-only permissions unless a narrowly scoped write permission is required to publish code-scanning results or OpenSSF attestations.

Automated findings are triage inputs, not certification. A passing workflow does not prove source authenticity, runtime completeness, production isolation, or absence of vulnerabilities.

## Scope and limitations

This repository is a reference implementation. It intentionally does not provide production identity, access management, key management, HSM/KMS-backed signing, managed persistence, tenant isolation, secure secret distribution, regulated-data handling, or provider certification.

The framework's hashes bind canonical records and make accidental or malicious record substitution detectable within the reference workflow. They are not a replacement for authenticated signatures, trusted timestamps, remote attestation, or production audit infrastructure.
