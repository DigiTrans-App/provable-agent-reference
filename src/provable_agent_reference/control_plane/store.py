from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_uri(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode()).hexdigest()


class PostgresStore:
    """PostgreSQL adapter; psycopg is imported only when the runtime is used."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("install the control-plane optional dependency") from exc
        with psycopg.connect(self.database_url) as connection:
            with connection.transaction():
                yield connection

    def create_run(self, run: dict[str, Any], event: dict[str, Any], outbox: dict[str, Any]) -> None:
        """Atomically persist state, append the journal, and enqueue the outbox."""
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO runs
                   (run_id, tenant_id, case_id, requester_subject, purpose, audience,
                    risk_tier, policy_version, status)
                   VALUES (%(run_id)s, %(tenant_id)s, %(case_id)s, %(requester_subject)s,
                           %(purpose)s, %(audience)s, %(risk_tier)s, %(policy_version)s,
                           'requested')""",
                run,
            )
            connection.execute(
                """INSERT INTO journal_records
                   (event_id, tenant_id, case_id, run_id, sequence, previous_event_hash,
                    body, body_hash, record_hash)
                   VALUES (%(event_id)s, %(tenant_id)s, %(case_id)s, %(run_id)s,
                           %(sequence)s, %(previous_event_hash)s, %(body)s::jsonb,
                           %(body_hash)s, %(record_hash)s)""",
                {**event, "body": canonical_json(event["body"])},
            )
            connection.execute(
                """INSERT INTO outbox
                   (outbox_id, tenant_id, aggregate_type, aggregate_id, event_type, payload)
                   VALUES (%(outbox_id)s, %(tenant_id)s, %(aggregate_type)s,
                           %(aggregate_id)s, %(event_type)s, %(payload)s::jsonb)""",
                {**outbox, "payload": canonical_json(outbox["payload"])},
            )

    def claim_outbox(self, worker_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if not worker_id or not 1 <= limit <= 500:
            raise ValueError("worker_id and limit are invalid")
        with self.transaction() as connection:
            rows = connection.execute(
                """WITH candidates AS (
                       SELECT outbox_id FROM outbox
                       WHERE published_at IS NULL
                         AND available_at <= clock_timestamp()
                         AND (claimed_at IS NULL OR claimed_at < clock_timestamp() - interval '60 seconds')
                       ORDER BY created_at, outbox_id
                       FOR UPDATE SKIP LOCKED
                       LIMIT %s
                   )
                   UPDATE outbox AS item
                   SET claimed_at = clock_timestamp(), claimed_by = %s, attempts = attempts + 1
                   FROM candidates
                   WHERE item.outbox_id = candidates.outbox_id
                   RETURNING item.outbox_id, item.event_type, item.payload, item.attempts""",
                (limit, worker_id),
            ).fetchall()
        return [
            {"outbox_id": row[0], "event_type": row[1], "payload": row[2], "attempts": row[3]}
            for row in rows
        ]

    def complete_outbox(self, outbox_id: str, worker_id: str) -> None:
        with self.transaction() as connection:
            cursor = connection.execute(
                """UPDATE outbox SET published_at = clock_timestamp(), claimed_at = NULL,
                          claimed_by = NULL, last_error = NULL
                   WHERE outbox_id = %s AND claimed_by = %s AND published_at IS NULL""",
                (outbox_id, worker_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("outbox lease is missing, stale, or already completed")

    def retry_outbox(self, outbox_id: str, worker_id: str, error: str, delay_seconds: int) -> None:
        if not error or len(error) > 2000 or not 1 <= delay_seconds <= 3600:
            raise ValueError("bounded retry error and delay are required")
        with self.transaction() as connection:
            cursor = connection.execute(
                """UPDATE outbox SET available_at = clock_timestamp() + %s,
                          claimed_at = NULL, claimed_by = NULL, last_error = %s
                   WHERE outbox_id = %s AND claimed_by = %s AND published_at IS NULL""",
                (timedelta(seconds=delay_seconds), error, outbox_id, worker_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("outbox lease is missing, stale, or already completed")

    def stage_artifact(self, metadata: dict[str, Any]) -> None:
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO artifacts
                   (digest, tenant_id, case_id, run_id, media_type, byte_length, storage_key, status)
                   VALUES (%(digest)s, %(tenant_id)s, %(case_id)s, %(run_id)s,
                           %(media_type)s, %(byte_length)s, %(storage_key)s, 'staged')""",
                metadata,
            )

    def finalize_artifact(self, digest: str, storage_key: str) -> None:
        with self.transaction() as connection:
            cursor = connection.execute(
                """UPDATE artifacts SET status = 'available', finalized_at = clock_timestamp()
                   WHERE digest = %s AND storage_key = %s AND status = 'staged'""",
                (digest, storage_key),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("artifact is missing, mismatched, or already finalized")

    def unavailable_artifact(self, digest: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                """UPDATE artifacts SET status = 'unavailable'
                   WHERE digest = %s AND status = 'staged'""",
                (digest,),
            )
