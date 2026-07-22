# Local evaluations

The local evaluation suite exercises the real provider-neutral pipeline with synthetic data. It makes no network requests and requires no API key.

```bash
python evals/run_local.py
```

The initial matrix covers:

- happy-path compilation, verification, approval, authorization, and audit;
- unknown evidence selection;
- unredacted sensitive content;
- exact-output substitution;
- purpose drift;
- audit-manifest tampering.

Results are written to `evals/results/latest.json`, which is intentionally ignored by Git.

The roadmap targets at least 100 public synthetic cases, including prompt-injection, evidence-scope, replay, policy, disclosure, and adapter-compatibility scenarios.
