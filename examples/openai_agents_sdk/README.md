# OpenAI Agents SDK example

This optional example demonstrates the public trust boundary with the OpenAI Agents SDK:

1. a governed tool returns minimized synthetic evidence metadata;
2. the agent returns only a semantic draft;
3. provider-neutral trusted code resolves evidence and compiles the canonical candidate;
4. deterministic local code verifies, records a simulated human approval, authorizes the exact use, and builds an audit manifest.

## Install

```bash
python -m pip install -e '.[openai]'
```

## Configure

Set a local API key and a model available to your OpenAI project:

```bash
export OPENAI_API_KEY='your-local-secret'
export OPENAI_MODEL='your-enabled-model'
```

On Windows PowerShell:

```powershell
$env:OPENAI_API_KEY = 'your-local-secret'
$env:OPENAI_MODEL = 'your-enabled-model'
```

## Run

```bash
python examples/openai_agents_sdk/agent.py
```

The example uses synthetic data, disables tracing, performs no retry in application code, and prints only bounded result metadata. Do not put a key in source control.

This compatibility example is not part of CI and does not imply OpenAI endorsement, certification, partner status, model availability, or production readiness.
