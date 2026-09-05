from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from provable_agent_reference.control_plane.artifacts import ArtifactReconciler, LocalArtifactStore
from provable_agent_reference.control_plane.assurance import s0_report
from provable_agent_reference.control_plane.models import CapabilityGrant
from provable_agent_reference.control_plane.outbox import OutboxWorker
from provable_agent_reference.control_plane.security import validate_local_reset_target


class ControlPlaneTests(unittest.TestCase):
    def grant(self, **changes):
        values = {
            "capabilities": frozenset({"evidence.read", "tool.prepare"}),
            "tenant_id": "tenant_synthetic",
            "case_id": "case_synthetic",
            "allowed_effects": frozenset({"draft"}),
            "max_tool_calls": 5,
            "max_model_calls": 3,
            "valid_until": datetime.now(UTC) + timedelta(hours=1),
            "delegation_depth": 2,
        }
        values.update(changes)
        return CapabilityGrant(**values)

    def test_child_grant_must_attenuate_every_dimension(self):
        parent = self.grant()
        child = self.grant(
            capabilities=frozenset({"evidence.read"}),
            max_tool_calls=2,
            max_model_calls=1,
            valid_until=parent.valid_until,
            delegation_depth=1,
        )
        self.assertTrue(parent.permits_child(child))
        self.assertFalse(parent.permits_child(self.grant(delegation_depth=2)))
        self.assertFalse(parent.permits_child(self.grant(allowed_effects=frozenset({"send"}))))
        self.assertFalse(parent.permits_child(self.grant(tenant_id="tenant_other")))

    def test_artifact_publication_is_content_addressed_and_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LocalArtifactStore(Path(directory))
            digest = store.publish(b"synthetic evidence")
            self.assertEqual(store.read(digest), b"synthetic evidence")
            self.assertEqual(store.publish(b"synthetic evidence"), digest)
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                store.publish(b"changed", expected_digest=digest)

    def test_artifact_reconciler_finalizes_and_fails_closed(self):
        class FakeStore:
            def __init__(self):
                self.finalized = []
                self.unavailable = []
                self.retried = []

            def claim_artifacts(self, _worker_id, _limit):
                return [
                    {
                        "digest": good_digest,
                        "storage_key": "sha256/good",
                        "byte_length": len(good_content),
                        "attempts": 1,
                    },
                    {
                        "digest": "sha256:" + "0" * 64,
                        "storage_key": "sha256/missing",
                        "byte_length": 10,
                        "attempts": 1,
                    },
                ]

            def finalize_artifact(self, digest, storage_key, worker_id):
                self.finalized.append((digest, storage_key, worker_id))

            def unavailable_artifact(self, digest, worker_id, reason):
                self.unavailable.append((digest, worker_id, reason))

            def retry_artifact(self, digest, worker_id, error, delay_seconds):
                self.retried.append((digest, worker_id, error, delay_seconds))

        with tempfile.TemporaryDirectory() as directory:
            artifacts = LocalArtifactStore(Path(directory))
            good_content = b"synthetic reconciliation evidence"
            good_digest = artifacts.publish(good_content)
            store = FakeStore()
            result = ArtifactReconciler(store, artifacts, "artifact-worker").run_once()

        self.assertEqual(result, (1, 1, 0))
        self.assertEqual(store.finalized[0], (good_digest, "sha256/good", "artifact-worker"))
        self.assertEqual(store.unavailable[0][0:2], ("sha256:" + "0" * 64, "artifact-worker"))
        self.assertEqual(store.retried, [])

    def test_artifact_reconciler_retries_transient_storage_failure(self):
        class FailingArtifacts:
            def read(self, _digest):
                raise OSError("sensitive mount detail")

        class FakeStore:
            finalized = []
            unavailable = []
            retried = []

            def claim_artifacts(self, _worker_id, _limit):
                return [
                    {
                        "digest": "sha256:" + "1" * 64,
                        "storage_key": "sha256/transient",
                        "byte_length": 10,
                        "attempts": 3,
                    }
                ]

            def finalize_artifact(self, *args):
                self.finalized.append(args)

            def unavailable_artifact(self, *args):
                self.unavailable.append(args)

            def retry_artifact(self, *args):
                self.retried.append(args)

        store = FakeStore()
        result = ArtifactReconciler(store, FailingArtifacts(), "artifact-worker").run_once()
        self.assertEqual(result, (0, 0, 1))
        self.assertEqual(store.finalized, [])
        self.assertEqual(store.unavailable, [])
        self.assertEqual(store.retried[0][3], 8)
        self.assertNotIn("sensitive mount detail", store.retried[0][2])

    def test_reset_target_is_local_and_synthetic_only(self):
        validate_local_reset_target(
            "local-synthetic",
            "postgresql://user:password@localhost:5432/reference_synthetic",
        )
        with self.assertRaises(RuntimeError):
            validate_local_reset_target(
                "production",
                "postgresql://user:password@localhost:5432/reference_synthetic",
            )
        with self.assertRaises(RuntimeError):
            validate_local_reset_target(
                "local-synthetic",
                "postgresql://user:password@db.example.com/reference_synthetic",
            )
        with self.assertRaises(RuntimeError):
            validate_local_reset_target(
                "local-synthetic",
                "postgresql://user:password@localhost/reference_production",
            )

    def test_s0_report_does_not_overclaim_storage_assurance(self):
        report = s0_report("revision-test")
        self.assertEqual(report["level"], "S0")
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["controls"]["external_immutability"], "not_claimed")

    def test_outbox_worker_completes_and_retries_with_bounded_error(self):
        class FakeStore:
            def __init__(self):
                self.completed = []
                self.retried = []

            def claim_outbox(self, worker_id, limit):
                return [
                    {"outbox_id": "ok", "event_type": "run.requested", "payload": {}, "attempts": 1},
                    {"outbox_id": "bad", "event_type": "run.requested", "payload": {}, "attempts": 2},
                ]

            def complete_outbox(self, outbox_id, worker_id):
                self.completed.append((outbox_id, worker_id))

            def retry_outbox(self, outbox_id, worker_id, error, delay_seconds):
                self.retried.append((outbox_id, worker_id, error, delay_seconds))

        store = FakeStore()

        def publish(_event_type, payload):
            if payload == {} and len(store.completed) == 1:
                raise ConnectionError("sensitive provider detail")

        worker = OutboxWorker(store, "worker-test", publish)
        self.assertEqual(worker.run_once(), (1, 1))
        self.assertEqual(store.completed, [("ok", "worker-test")])
        self.assertEqual(store.retried[0][:2], ("bad", "worker-test"))
        self.assertNotIn("sensitive provider detail", store.retried[0][2])
        self.assertEqual(store.retried[0][3], 4)


if __name__ == "__main__":
    unittest.main()
