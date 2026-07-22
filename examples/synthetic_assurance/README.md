# Synthetic assurance example

This example runs the complete provider-neutral reference pipeline with synthetic evidence and no network access.

```bash
python examples/synthetic_assurance/run.py
```

The output contains the canonical candidate, deterministic verification result, simulated human approval record, exact-use authorization result, and audit manifest.

The approval is a local demonstration record identified as `human_reviewer`; it is not an identity-proofing or production approval system.
