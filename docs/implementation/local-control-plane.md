# Local durable control plane

Status: **experimental Phase 1 synthetic reference**. This deployment is S0 only and must not
be represented as production storage assurance.

## Start

```bash
docker compose up --build --wait
```

The stack binds PostgreSQL only to loopback, uses an internal container network, requires no
external credentials, and stores artifacts in a dedicated local volume.

## Transaction boundary

Each authoritative mutation writes state, its immutable journal event, and its outbox event in
one PostgreSQL transaction. Journal rows reject updates and deletes. Outbox delivery is
at-least-once; consumers must deduplicate by event identity and content binding.

Artifact bytes use staged, content-addressed publication. Database metadata may become
`available` only after digest verification and finalization. Missing or orphaned bytes remain
unavailable and require reconciliation.

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
- backup, restore, outbox worker leases, artifact reconciliation, and failure injection remain
  acceptance work within PR B.
