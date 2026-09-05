from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from typing import Any, Iterator


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
