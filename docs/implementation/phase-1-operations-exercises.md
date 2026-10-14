# Phase 1 operational exercises

These exercises use only the local synthetic PostgreSQL database, artifact volume, fixed embedded effect destination, and public development key.

## Backup and restore

Follow the exact `pg_dump`, guarded reset, and `pg_restore` sequence in `.github/workflows/control-plane-integration.yml`. Pass criteria: restore succeeds, journal rows remain reconstructable, and no non-synthetic database can pass the reset guard. This is a logical recovery demonstration, not a disaster-recovery guarantee.

## Transaction failure injection

Run `python -m unittest tests.test_control_plane_integration.ControlPlaneIntegrationTests.test_failed_mutation_rolls_back_state_journal_and_outbox -v`. Pass criteria: the injected failure leaves no partial state, journal, or outbox mutation.

## Unknown effect and retry safety

Run `python -m unittest tests.test_synthetic_effects.SyntheticEffectTests.test_unknown_outcome_reconciles_without_unsafe_retry -v`. Pass criteria: unknown remains unknown until reconciliation and no automatic effect retry occurs.

## Key compromise and revocation

Treat the development key as compromised by design. In a copy of the trust bundle, set `status` to `disabled` or set `revoked_at` to an RFC3339 time. Both Python and TypeScript verification must fail. Replace the key only by assigning a new globally unique key ID and publishing a new pinned bundle; never reuse an old key ID for new material.

## Authorization revocation and supersession

Run `python -m unittest tests.test_synthetic_effects.SyntheticEffectTests.test_authorization_is_single_use_and_lifecycle_is_explicit -v`. Pass criteria: consumed or revoked authority cannot be consumed again, supersession identifies a successor, and historical records remain intact.

## Artifact loss or corruption

Run `python -m unittest tests.test_control_plane.ControlPlaneTests.test_artifact_reconciler_finalizes_and_fails_closed -v`. Pass criteria: verified bytes become available; missing or digest-mismatched bytes become unavailable rather than silently accepted.

## Public-boundary review

Before every release, confirm that repository changes contain only generic reference controls, synthetic fixtures, and public documentation. Production/customer-specific orchestration, managed evidence operations, commercial connectors, private analytics, credentials, infrastructure, and roadmap content belong in private DigiTrust repositories.
