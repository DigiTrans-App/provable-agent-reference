# Synthetic Codex Evidence Adapter example

This example converts synthetic Codex execution JSONL and synthetic multi-agent lifecycle telemetry into a deterministic, privacy-safe evidence bundle.

It requires no network access and no API key.

## Run

From the repository root:

```bash
python -m pip install -e '.[dev]'
python examples/codex_evidence_adapter/run.py
```

The command prints:

- three scoped evidence records;
- one deterministic evidence bundle;
- a coverage report that distinguishes available, partial, and unavailable evidence;
- only hashes for commands, paths, prompts, tool data, identifiers, and message content.

## Fixtures

- `fixtures/codex_exec.synthetic.jsonl` contains supported execution events plus one intentionally unsupported event.
- `fixtures/codex_otel.synthetic.jsonl` contains one correlated synthetic multi-agent send/receive lifecycle.

## Compatibility vectors

- `expected/codex_evidence_bundle.expected.json`
- `expected/codex_coverage.expected.json`

The unit tests regenerate the evidence from the fixtures and compare it with these published vectors.

## Important limitation

The example demonstrates deterministic normalization and integrity binding. It does not prove that a source stream is authentic or complete. It is a community integration and does not imply OpenAI endorsement, certification, sponsorship, or review.

See [Codex Evidence Adapter v0.1](../../docs/codex-evidence-adapter.md) for the trust boundary and known upstream evidence gaps.
