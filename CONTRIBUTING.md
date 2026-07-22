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

## Pull requests

- Open an issue for substantial architecture changes.
- Keep pull requests focused and explain the trust-boundary impact.
- Add tests for each behavior change and each failure mode.
- Update schemas and documentation when contracts change.
- Do not commit API keys, `.env` files, private evidence, raw prompts from customer workloads, or generated evaluation results.
- Use Conventional Commit style when practical, for example `feat(compiler): add evidence-scope binding`.

## AI-assisted contributions

AI tools, including Codex, may assist with code, tests, and documentation. Contributors remain responsible for understanding, reviewing, testing, and licensing every submitted change. Disclose material AI assistance in the pull request when it affects architecture or security-sensitive behavior.

## Contributor license

Unless explicitly stated otherwise, contributions are licensed under Apache License 2.0 under the terms described in `LICENSE`.
