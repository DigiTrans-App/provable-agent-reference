# Contributing

Thank you for helping improve the Provable Agent Reference Framework.

## Principles

Contributions should preserve these project invariants:

1. Model-authored data is semantic and non-authoritative.
2. Identity, scope, evidence hashes, verification inputs, approval, and authorization are derived or checked by trusted deterministic code.
3. A verification failure cannot create an approval or publication path.
4. Authorization is bound to the exact candidate, purpose, audience, and output hash.
5. Tests use synthetic data and must not include credentials or customer data.
6. Provider-specific examples remain optional adapters around the provider-neutral core.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python scripts/validate_repo.py
ruff check .
```

Security-sensitive canonicalization and replay properties run with at least 100 generated
examples in CI. See the [property-testing guide](docs/property-testing.md) for focused commands,
the 1,000-example extended profile, and the failure-reproduction workflow.

## Independent validation

Independent technical reviews are welcome, including critical, negative, and incomplete results. Start with the [independent validation guide](docs/independent-validation.md) and use the [validation report template](docs/validation-report-template.md) for the human assessment.

A useful external review should identify the exact tag or commit, reproduce the public checks, examine the trust boundary and limitations, and include the smallest synthetic reproduction for any failure. Generated reports under `validation-results/` are ignored by Git and should be reviewed manually before any public disclosure.

Use only public or synthetic inputs. Do not place credentials, customer data, private evidence, production traces, proprietary architecture, or private prompts in a report, issue, or pull request. Report unpublished security vulnerabilities through the private process in `SECURITY.md` rather than the public independent-validation issue form.

## Pull requests

- Open an issue for substantial architecture changes.
- Keep pull requests focused and explain the trust-boundary impact.
- Add tests for each behavior change and each failure mode.
- Update schemas and documentation when contracts change.
- Do not commit API keys, `.env` files, private evidence, raw prompts from customer workloads, generated evaluation results, or generated independent-validation reports.
- Use Conventional Commit style when practical, for example `feat(compiler): add evidence-scope binding`.

## AI-assisted contributions

AI tools, including Codex, may assist with code, tests, and documentation. Contributors remain responsible for understanding, reviewing, testing, and licensing every submitted change. Disclose material AI assistance in the pull request when it affects architecture or security-sensitive behavior.

## Contributor license

Unless explicitly stated otherwise, contributions are licensed under Apache License 2.0 under the terms described in `LICENSE`.
