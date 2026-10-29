# Local durable control plane

Status: **experimental Phase 1 synthetic reference**. This deployment is S0 only and must not
be represented as production storage assurance.

## Start

```bash
docker compose up --build --wait
```

The stack binds PostgreSQL only to loopback, uses an internal container network, requires no
external credentials, and stores artifacts in a dedicated local volume. PostgreSQL and Python
base images are pinned by both human-readable version and CI-captured multi-platform manifest
digest.

## Transaction boundary

Each authoritative mutation writes state, its immutable journal event, and its outbox event in
one PostgreSQL transaction. Journal rows reject updates and deletes. Outbox delivery is
at-least-once; consumers must deduplicate by event identity and content binding.

Capability delegation locks both the persisted run and parent grant, verifies the stored parent
document hash, rejects revoked or expired authority, and checks every attenuation dimension before
atomically inserting the child grant, chained journal event, and outbox record. Deterministic child
grant identity makes an identical retry replay-safe; mismatched collisions fail closed.

Artifact bytes use staged, content-addressed publication. A lease-based reconciler marks database
metadata `available` only after digest and byte-length verification. Missing or corrupt bytes fail
closed to `unavailable`; transient storage errors use bounded exponential retry without persisting
provider error details.

The `Control Plane Integration` workflow starts an isolated PostgreSQL service, runs migrations
and deterministic seeding twice, verifies atomic commit/rollback and outbox lease exclusion, then
performs a logical `pg_dump`/reset/`pg_restore` recovery exercise. The workflow is synthetic-only;
its result is not a durability or disaster-recovery assurance claim.

## Reset

Reset is intentionally difficult to invoke accidentally:

```bash
PAR_ENVIRONMENT=local-synthetic \
PAR_DATABASE_URL=postgresql://par_local:local-synthetic-only@localhost:55432/provable_agent_synthetic \
python scripts/control_plane_reset.py --confirm RESET-LOCAL-SYNTHETIC
```

The command refuses non-local hosts, databases whose names do not end in `_synthetic`, missing
environment markers, and any confirmation value other than the exact literal above.

## Limitations

- synthetic identities and policy inputs only;
- local development credentials only;
- no production destination or external effect;
- no authenticated-record or append-only-storage claim beyond logical S0 behavior;
- broader production-grade fault injection remains outside this synthetic S0 reference scope.
