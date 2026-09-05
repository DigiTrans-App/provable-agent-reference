from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from .models import CapabilityGrant


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

    def create_run(
        self,
        run: dict[str, Any],
        event: dict[str, Any],
        outbox: dict[str, Any],
        idempotency: dict[str, Any],
    ) -> str:
        """Atomically persist state, append the journal, and enqueue the outbox."""
        with self.transaction() as connection:
            claimed = connection.execute(
                """INSERT INTO idempotency_keys
                   (tenant_id, subject, operation, key_commitment, request_hash, result_ref)
                   VALUES (%(tenant_id)s, %(subject)s, %(operation)s, %(key_commitment)s,
                           %(request_hash)s, NULL)
                   ON CONFLICT DO NOTHING
                   RETURNING tenant_id""",
                idempotency,
            ).fetchone()
            if claimed is None:
                existing = connection.execute(
                    """SELECT request_hash, result_ref FROM idempotency_keys
                       WHERE tenant_id = %(tenant_id)s AND subject = %(subject)s
                         AND operation = %(operation)s AND key_commitment = %(key_commitment)s
                       FOR UPDATE""",
                    idempotency,
                ).fetchone()
                if existing is None or existing[0] != idempotency["request_hash"]:
                    raise RuntimeError("idempotency key was reused for a different request")
                if existing[1] is None:
                    raise RuntimeError("idempotency operation has no committed result")
                return str(existing[1])
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
            connection.execute(
                """UPDATE idempotency_keys SET result_ref = %(result_ref)s
                   WHERE tenant_id = %(tenant_id)s AND subject = %(subject)s
                     AND operation = %(operation)s AND key_commitment = %(key_commitment)s""",
                idempotency,
            )
        return str(idempotency["result_ref"])

    def create_delegation(
        self,
        grant_record: dict[str, Any],
        event_id: str,
        outbox_id: str,
    ) -> str:
        """Persist an attenuated child grant and its audit records atomically."""
        child_document = grant_record["grant_document"]
        child = _capability_grant(child_document)
        with self.transaction() as connection:
            run_scope = connection.execute(
                "SELECT tenant_id, case_id FROM runs WHERE run_id = %s FOR UPDATE",
                (grant_record["run_id"],),
            ).fetchone()
            if run_scope is None or tuple(run_scope) != (child.tenant_id, child.case_id):
                raise PermissionError("child grant is outside the persisted run scope")
            parent_row = connection.execute(
                """SELECT tenant_id, case_id, run_id, grant_document, grant_hash,
                          valid_until, revoked_at
                   FROM capability_grants WHERE grant_id = %s FOR UPDATE""",
                (grant_record["parent_grant_id"],),
            ).fetchone()
            if parent_row is None:
                raise PermissionError("parent capability grant does not exist")
            parent_document = parent_row[3]
            if parent_row[4] != sha256_uri(parent_document):
                raise RuntimeError("persisted parent grant failed integrity verification")
            if parent_row[6] is not None or parent_row[5] <= datetime.now(UTC):
                raise PermissionError("parent capability grant is revoked or expired")
            if tuple(parent_row[:3]) != (
                child.tenant_id,
                child.case_id,
                grant_record["run_id"],
            ):
                raise PermissionError("parent capability grant is outside the run scope")
            if not _capability_grant(parent_document).permits_child(child):
                raise PermissionError("child capability grant expands parent authority")

            inserted = connection.execute(
                """INSERT INTO capability_grants
                   (grant_id, tenant_id, case_id, run_id, parent_grant_id, grant_document,
                    grant_hash, valid_until)
                   VALUES (%(grant_id)s, %(tenant_id)s, %(case_id)s, %(run_id)s,
                           %(parent_grant_id)s, %(grant_document)s::jsonb, %(grant_hash)s,
                           %(valid_until)s)
                   ON CONFLICT (grant_id) DO NOTHING
                   RETURNING grant_id""",
                {**grant_record, "grant_document": canonical_json(child_document)},
            ).fetchone()
            if inserted is None:
                existing = connection.execute(
                    """SELECT parent_grant_id, grant_hash FROM capability_grants
                       WHERE grant_id = %s""",
                    (grant_record["grant_id"],),
                ).fetchone()
                if existing != (grant_record["parent_grant_id"], grant_record["grant_hash"]):
                    raise RuntimeError("grant identity collision or mismatched replay")
                return str(grant_record["grant_id"])

            previous = connection.execute(
                """SELECT sequence, record_hash FROM journal_records
                   WHERE run_id = %s ORDER BY sequence DESC LIMIT 1""",
                (grant_record["run_id"],),
            ).fetchone()
            sequence = 0 if previous is None else previous[0] + 1
            previous_hash = None if previous is None else previous[1]
            body = {
                "event_type": "capability.delegated",
                "grant_hash": grant_record["grant_hash"],
                "grant_id": grant_record["grant_id"],
                "parent_grant_id": grant_record["parent_grant_id"],
            }
            event = {
                "event_id": event_id,
                "tenant_id": child.tenant_id,
                "case_id": child.case_id,
                "run_id": grant_record["run_id"],
                "sequence": sequence,
                "previous_event_hash": previous_hash,
                "body": body,
                "body_hash": sha256_uri(body),
            }
            event["record_hash"] = sha256_uri(event)
            connection.execute(
                """INSERT INTO journal_records
                   (event_id, tenant_id, case_id, run_id, sequence, previous_event_hash,
                    body, body_hash, record_hash)
                   VALUES (%(event_id)s, %(tenant_id)s, %(case_id)s, %(run_id)s,
                           %(sequence)s, %(previous_event_hash)s, %(body)s::jsonb,
                           %(body_hash)s, %(record_hash)s)""",
                {**event, "body": canonical_json(body)},
            )
            connection.execute(
                """INSERT INTO outbox
                   (outbox_id, tenant_id, aggregate_type, aggregate_id, event_type, payload)
                   VALUES (%s, %s, 'capability_grant', %s, 'capability.delegated', %s::jsonb)""",
                (outbox_id, child.tenant_id, grant_record["grant_id"], canonical_json(body)),
            )
        return str(grant_record["grant_id"])

    def append_agent_activities(self, records: list[dict[str, Any]]) -> None:
        if not records:
            raise ValueError("at least one activity record is required")
        run_id = records[0]["run_id"]
        with self.transaction() as connection:
            run_scope = connection.execute(
                "SELECT tenant_id, case_id FROM runs WHERE run_id = %s FOR UPDATE", (run_id,)
            ).fetchone()
            if run_scope is None:
                raise RuntimeError("activity run does not exist")
            previous = connection.execute(
                """SELECT sequence, record_hash FROM agent_activity_records
                   WHERE run_id = %s ORDER BY sequence DESC LIMIT 1""",
                (run_id,),
            ).fetchone()
            expected_sequence = 0 if previous is None else previous[0] + 1
            expected_previous = None if previous is None else previous[1]
            for record in records:
                if (
                    record["run_id"] != run_id
                    or (record["tenant_id"], record["case_id"]) != tuple(run_scope)
                    or record["sequence"] != expected_sequence
                    or record["previous_event_hash"] != expected_previous
                    or record["body_hash"] != sha256_uri(record["body"])
                ):
                    raise RuntimeError("activity scope, order, chain, or body hash is invalid")
                payload = {key: value for key, value in record.items() if key != "record_hash"}
                if record["record_hash"] != sha256_uri(payload):
                    raise RuntimeError("activity record hash is invalid")
                connection.execute(
                    """INSERT INTO agent_activity_records
                       (event_id, tenant_id, case_id, run_id, sequence, previous_event_hash,
                        event_type, body, body_hash, record, record_hash)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s)""",
                    (
                        record["event_id"],
                        record["tenant_id"],
                        record["case_id"],
                        run_id,
                        record["sequence"],
                        record["previous_event_hash"],
                        record["event_type"],
                        canonical_json(record["body"]),
                        record["body_hash"],
                        canonical_json(record),
                        record["record_hash"],
                    ),
                )
                connection.execute(
                    """INSERT INTO outbox
                       (outbox_id, tenant_id, aggregate_type, aggregate_id, event_type, payload)
                       VALUES (%s, %s, 'agent_activity', %s, %s, %s::jsonb)""",
                    (
                        "outbox_" + record["event_id"],
                        record["tenant_id"],
                        record["event_id"],
                        record["event_type"],
                        canonical_json(
                            {
                                "event_id": record["event_id"],
                                "record_hash": record["record_hash"],
                            }
                        ),
                    ),
                )
                expected_sequence += 1
                expected_previous = record["record_hash"]

    def reconstruct_agent_activities(self, run_id: str) -> list[dict[str, Any]]:
        with self.transaction() as connection:
            rows = connection.execute(
                """SELECT record FROM agent_activity_records
                   WHERE run_id = %s ORDER BY sequence""",
                (run_id,),
            ).fetchall()
        records = [row[0] for row in rows]
        previous = None
        for sequence, record in enumerate(records):
            payload = {key: value for key, value in record.items() if key != "record_hash"}
            if (
                record["sequence"] != sequence
                or record["previous_event_hash"] != previous
                or record["body_hash"] != sha256_uri(record["body"])
                or record["record_hash"] != sha256_uri(payload)
            ):
                raise RuntimeError("persisted activity reconstruction failed closed")
            previous = record["record_hash"]
        return records

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

    def claim_artifacts(self, worker_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if not worker_id or not 1 <= limit <= 500:
            raise ValueError("worker_id and limit are invalid")
        with self.transaction() as connection:
            rows = connection.execute(
                """WITH candidates AS (
                       SELECT digest FROM artifacts
                       WHERE status = 'staged'
                         AND reconcile_available_at <= clock_timestamp()
                         AND (reconcile_claimed_at IS NULL OR
                              reconcile_claimed_at < clock_timestamp() - interval '60 seconds')
                       ORDER BY created_at, digest
                       FOR UPDATE SKIP LOCKED
                       LIMIT %s
                   )
                   UPDATE artifacts AS item
                   SET reconcile_claimed_at = clock_timestamp(), reconcile_claimed_by = %s,
                       reconcile_attempts = reconcile_attempts + 1
                   FROM candidates
                   WHERE item.digest = candidates.digest
                   RETURNING item.digest, item.storage_key, item.byte_length,
                             item.reconcile_attempts""",
                (limit, worker_id),
            ).fetchall()
        return [
            {
                "digest": row[0],
                "storage_key": row[1],
                "byte_length": row[2],
                "attempts": row[3],
            }
            for row in rows
        ]

    def finalize_artifact(self, digest: str, storage_key: str, worker_id: str) -> None:
        with self.transaction() as connection:
            cursor = connection.execute(
                """UPDATE artifacts SET status = 'available', finalized_at = clock_timestamp(),
                          reconcile_claimed_at = NULL, reconcile_claimed_by = NULL,
                          last_reconcile_error = NULL
                   WHERE digest = %s AND storage_key = %s AND status = 'staged'
                     AND reconcile_claimed_by = %s""",
                (digest, storage_key, worker_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("artifact lease is missing, stale, mismatched, or finalized")

    def unavailable_artifact(self, digest: str, worker_id: str, reason: str) -> None:
        if not reason or len(reason) > 500:
            raise ValueError("a bounded unavailability reason is required")
        with self.transaction() as connection:
            cursor = connection.execute(
                """UPDATE artifacts SET status = 'unavailable', reconcile_claimed_at = NULL,
                          reconcile_claimed_by = NULL, last_reconcile_error = %s
                   WHERE digest = %s AND status = 'staged' AND reconcile_claimed_by = %s""",
                (reason, digest, worker_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("artifact lease is missing, stale, or already reconciled")

    def retry_artifact(
        self, digest: str, worker_id: str, error: str, delay_seconds: int
    ) -> None:
        if not error or len(error) > 500 or not 1 <= delay_seconds <= 3600:
            raise ValueError("bounded retry error and delay are required")
        with self.transaction() as connection:
            cursor = connection.execute(
                """UPDATE artifacts
                   SET reconcile_available_at = clock_timestamp() + %s,
                       reconcile_claimed_at = NULL, reconcile_claimed_by = NULL,
                       last_reconcile_error = %s
                   WHERE digest = %s AND status = 'staged' AND reconcile_claimed_by = %s""",
                (timedelta(seconds=delay_seconds), error, digest, worker_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("artifact lease is missing, stale, or already reconciled")


def _capability_grant(document: dict[str, Any]) -> CapabilityGrant:
    return CapabilityGrant(
        capabilities=frozenset(document["capabilities"]),
        tenant_id=document["tenant_id"],
        case_id=document["case_id"],
        allowed_effects=frozenset(document["allowed_effects"]),
        max_tool_calls=document["max_tool_calls"],
        max_model_calls=document["max_model_calls"],
        valid_until=datetime.fromisoformat(document["valid_until"]),
        delegation_depth=document["delegation_depth"],
    )
