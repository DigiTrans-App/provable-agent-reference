# Codex contributor workflow

Codex can accelerate implementation while the human contributor remains responsible for architecture, security, testing, and licensing.

## Recommended loop

1. Open or select a narrowly scoped issue.
2. Ask Codex to inspect the repository and restate the trust-boundary impact.
3. Keep credentials and customer data outside the prompt and repository.
4. Require tests for both the happy path and a fail-closed path.
5. Run:

   ```bash
   python -m unittest discover -s tests -v
   python scripts/validate_repo.py
   ruff check .
   ```

6. Review every diff, especially contracts, hashes, approval, and authorization logic.
7. Summarize material AI assistance in the pull request.

## Suggested task prompt

```text
Implement issue <number> in the Provable Agent Reference Framework.
Preserve the semantic-only model boundary. Do not let model-authored data
supply trusted identity, evidence hashes, verification, approval, or
authorization fields. Add deterministic tests, including at least one
fail-closed case. Make no network request and do not introduce credentials.
```

## Use of API credits

When API credits are available, use them only for public, synthetic evaluation cases, optional provider examples, compatibility testing, and contributor tooling. Do not use credits for customer workloads or proprietary DigiTrust services.
