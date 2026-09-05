from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime, timedelta

from provable_agent_reference.control_plane.models import CapabilityGrant
from provable_agent_reference.control_plane.service import ControlPlaneService
from provable_agent_reference.control_plane.store import PostgresStore, canonical_json, sha256_uri


@unittest.skipUnless(os.environ.get("PAR_DATABASE_URL"), "requires local synthetic PostgreSQL")
class ControlPlaneIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = PostgresStore(os.environ["PAR_DATABASE_URL"])

    def test_create_run_is_atomic_and_outbox_is_lease_protected(self) -> None:
        run_id = "00000000-0000-4000-8000-000000000101"
        event_id = "00000000-0000-4000-8000-000000000102"
        outbox_id = "00000000-0000-4000-8000-000000000103"
        run = {
            "run_id": run_id,
            "tenant_id": "tenant_synthetic",
            "case_id": "case_integration",
            "requester_subject": "subject_synthetic",
            "purpose": "integration test",
            "audience": "maintainers",
            "risk_tier": 0,
            "policy_version": "phase-1",
        }
        body = {"event_type": "run.requested", "run_id": run_id}
        event = {
            "event_id": event_id,
            "tenant_id": run["tenant_id"],
            "case_id": run["case_id"],
            "run_id": run_id,
            "sequence": 0,
            "previous_event_hash": None,
            "body": body,
            "body_hash": "sha256:" + "1" * 64,
            "record_hash": "sha256:" + "2" * 64,
        }
        outbox = {
            "outbox_id": outbox_id,
            "tenant_id": run["tenant_id"],
            "aggregate_type": "run",
            "aggregate_id": run_id,
            "event_type": "run.requested",
            "payload": body,
        }
        idempotency = {
            "tenant_id": run["tenant_id"],
            "subject": run["requester_subject"],
            "operation": "run.create",
            "key_commitment": "sha256:" + "4" * 64,
            "request_hash": "sha256:" + "5" * 64,
            "result_ref": run_id,
        }

        self.assertEqual(self.store.create_run(run, event, outbox, idempotency), run_id)
        self.assertEqual(self.store.create_run(run, event, outbox, idempotency), run_id)
        claimed = self.store.claim_outbox("integration-worker", limit=10)
        claimed_ids = [str(item["outbox_id"]) for item in claimed]
        self.assertIn(outbox_id, claimed_ids)
        self.assertEqual(claimed_ids.count(outbox_id), 1)
        self.assertEqual(self.store.claim_outbox("other-worker", limit=10), [])
        for claimed_id in claimed_ids:
            self.store.complete_outbox(claimed_id, "integration-worker")

        with self.store.transaction() as connection:
            counts = connection.execute(
                """SELECT
                     (SELECT count(*) FROM runs WHERE run_id = %s),
                     (SELECT count(*) FROM journal_records WHERE event_id = %s),
                     (SELECT count(*) FROM outbox WHERE outbox_id = %s AND published_at IS NOT NULL)""",
                (run_id, event_id, outbox_id),
            ).fetchone()
        self.assertEqual(counts, (1, 1, 1))

    def test_failed_mutation_rolls_back_state_journal_and_outbox(self) -> None:
        import psycopg

        run_id = "00000000-0000-4000-8000-000000000111"
        payload = {
            "run_id": run_id,
            "tenant_id": "tenant_synthetic",
            "case_id": "case_rollback",
            "requester_subject": "subject_synthetic",
            "purpose": "rollback test",
            "audience": "maintainers",
            "risk_tier": 0,
            "policy_version": "phase-1",
        }
        event = {
            "event_id": "00000000-0000-4000-8000-000000000112",
            "tenant_id": payload["tenant_id"],
            "case_id": payload["case_id"],
            "run_id": run_id,
            "sequence": 1,
            "previous_event_hash": None,
            "body": {"event_type": "run.requested", "run_id": run_id},
            "body_hash": "invalid",
            "record_hash": "sha256:" + "3" * 64,
        }
        outbox = {
            "outbox_id": "00000000-0000-4000-8000-000000000113",
            "tenant_id": payload["tenant_id"],
            "aggregate_type": "run",
            "aggregate_id": run_id,
            "event_type": "run.requested",
            "payload": event["body"],
        }
        idempotency = {
            "tenant_id": payload["tenant_id"],
            "subject": payload["requester_subject"],
            "operation": "run.create",
            "key_commitment": "sha256:" + "6" * 64,
            "request_hash": "sha256:" + "7" * 64,
            "result_ref": run_id,
        }

        with self.assertRaises(psycopg.errors.CheckViolation):
            self.store.create_run(payload, event, outbox, idempotency)
        with self.store.transaction() as connection:
            count = connection.execute("SELECT count(*) FROM runs WHERE run_id = %s", (run_id,)).fetchone()[0]
        self.assertEqual(count, 0)

    def test_delegation_uses_persisted_parent_and_is_replay_safe(self) -> None:
        valid_until = datetime.now(UTC) + timedelta(hours=1)
        with self.store.transaction() as connection:
            run_id, tenant_id, case_id = connection.execute(
                "SELECT run_id, tenant_id, case_id FROM runs ORDER BY created_at LIMIT 1"
            ).fetchone()
            parent_document = {
                "allowed_effects": ["draft"],
                "capabilities": ["evidence.read", "tool.prepare"],
                "case_id": case_id,
                "delegation_depth": 2,
                "max_model_calls": 3,
                "max_tool_calls": 5,
                "tenant_id": tenant_id,
                "valid_until": valid_until.isoformat(),
            }
            connection.execute(
                """INSERT INTO capability_grants
                   (grant_id, tenant_id, case_id, run_id, parent_grant_id, grant_document,
                    grant_hash, valid_until)
                   VALUES ('grant_synthetic_root', %s, %s, %s, NULL, %s::jsonb, %s, %s)""",
                (
                    tenant_id,
                    case_id,
                    run_id,
                    canonical_json(parent_document),
                    sha256_uri(parent_document),
                    valid_until,
                ),
            )
        child = CapabilityGrant(
            capabilities=frozenset({"evidence.read"}),
            tenant_id=tenant_id,
            case_id=case_id,
            allowed_effects=frozenset({"draft"}),
            max_tool_calls=2,
            max_model_calls=1,
            valid_until=valid_until,
            delegation_depth=1,
        )
        service = ControlPlaneService(self.store)
        grant_id = service.delegate_capability(
            run_id, "grant_synthetic_root", child, "delegation-replay-test"
        )
        self.assertEqual(
            service.delegate_capability(
                run_id, "grant_synthetic_root", child, "delegation-replay-test"
            ),
            grant_id,
        )
        expanded = CapabilityGrant(
            capabilities=frozenset({"evidence.read", "effect.send"}),
            tenant_id=tenant_id,
            case_id=case_id,
            allowed_effects=frozenset({"draft"}),
            max_tool_calls=2,
            max_model_calls=1,
            valid_until=valid_until,
            delegation_depth=1,
        )
        with self.assertRaises(PermissionError):
            service.delegate_capability(
                run_id, "grant_synthetic_root", expanded, "delegation-expanded-test"
            )
        with self.store.transaction() as connection:
            counts = connection.execute(
                """SELECT
                     (SELECT count(*) FROM capability_grants WHERE grant_id = %s),
                     (SELECT count(*) FROM journal_records
                      WHERE body->>'grant_id' = %s),
                     (SELECT count(*) FROM outbox WHERE aggregate_id = %s)""",
                (grant_id, grant_id, grant_id),
            ).fetchone()
        self.assertEqual(counts, (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
