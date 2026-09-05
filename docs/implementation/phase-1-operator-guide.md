# Phase 1 operator and adopter guide

Status: **experimental synthetic reference**. This guide does not authorize production use.

## Fresh-clone path

Prerequisites are Git, Python 3.11 or 3.12, Node.js 22 or later, Docker with Compose v2, and local ports 55432 and 8080. No external secret, cloud account, customer data, or production identity is required.

From a clean checkout:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev,control-plane,signing]'
docker compose up --build --wait
python scripts/run_phase1_readiness.py \
  --source-revision "$(git rev-parse HEAD)" \
  --output validation-results/phase1-readiness.json
```

The readiness command runs the complete Python suite, repository validation, independent TypeScript verification of the committed DSSE vector, a fixed canonicalization benchmark, and a self-issued machine-readable report. It fails if fewer than 100 tests are discovered. PostgreSQL integration, backup, and restore remain separate exercises because the ordinary test suite deliberately skips database tests unless the local synthetic environment is configured.

Stop the stack without deleting data using `docker compose down`. Do not use `docker compose down --volumes` as an ordinary stop command.

## Complete synthetic walkthrough

1. Confirm `docker compose ps` reports both services healthy.
2. Export only the documented local values:

   ```bash
   export PAR_ENVIRONMENT=local-synthetic
   export PAR_DATABASE_URL=postgresql://par_local:local-synthetic-only@localhost:55432/provable_agent_synthetic
   export PAR_ARTIFACT_ROOT="$PWD/.local-artifacts"
   ```

3. Run migrations and deterministic seed twice; the second execution must be idempotent:

   ```bash
   python scripts/control_plane_migrate.py
   python scripts/control_plane_migrate.py
   python scripts/control_plane_seed.py
   python scripts/control_plane_seed.py
   ```

4. Run `python -m unittest tests/test_control_plane_integration.py -v` to exercise the transactional state/journal/outbox boundary, durable activity reconstruction, receipt/reconciliation integrity, and rollback behavior.
5. Run `python -m unittest tests/test_synthetic_workflow.py tests/test_synthetic_effects.py -v` for delegation, minimized memory, capability enforcement, exact-use authorization, simulated effect, unknown reconciliation, revocation, and supersession.
6. Run `python -m unittest tests/test_dsse.py -v` and the Node verifier command documented in the readiness output.
7. Review the generated report. `self_issued` must be true, storage must remain `S0` and `incomplete`, and authenticated-records must remain `not_tested`.

## Acceptance and escalation

Stop and investigate if any identity or scope comes from model/adapter output, any production destination becomes reachable, raw memory appears in an exported packet, an acknowledgement is represented as effect success, an unknown outcome retries automatically, a revoked authorization is consumable, a DSSE key is accepted from the envelope, or the report claims production/independent assurance.

Successful execution demonstrates a reproducible synthetic pattern. It is not certification, a production go-live decision, or evidence that a different deployment inherited these controls.
