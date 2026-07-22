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

## Scope and limitations

This repository is a reference implementation. It intentionally does not provide production identity, access management, key management, HSM/KMS-backed signing, managed persistence, tenant isolation, secure secret distribution, regulated-data handling, or provider certification.

The framework's hashes bind canonical records and make accidental or malicious record substitution detectable within the reference workflow. They are not a replacement for authenticated signatures, trusted timestamps, remote attestation, or production audit infrastructure.
