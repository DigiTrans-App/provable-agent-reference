from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from provable_agent_reference.control_plane.artifacts import LocalArtifactStore
from provable_agent_reference.control_plane.models import CapabilityGrant
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


if __name__ == "__main__":
    unittest.main()
