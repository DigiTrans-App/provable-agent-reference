from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from provable_agent_reference.contracts import TrustedRunContext
from provable_agent_reference.control_plane.models import CapabilityGrant
from provable_agent_reference.synthetic_workflow import (
    GovernedAdapterError,
    PrivacyBoundedMemory,
    SyntheticMemoryRecord,
    SyntheticVendorAssuranceWorkflow,
)


class SyntheticWorkflowTests(unittest.TestCase):
    def context(self, **changes):
        values = {
            "tenant_id": "tenant_synthetic",
            "case_id": "case_vendor_review",
            "run_id": "run_synthetic_vendor_review",
            "agent_id": "agent_evidence_specialist",
            "purpose": "Prepare a synthetic vendor-assurance response.",
            "audience": "synthetic_customer_reviewer",
            "classification": "internal",
            "created_at": "2026-09-05T00:00:00Z",
        }
        values.update(changes)
        return TrustedRunContext(**values)

    def grant(self, **changes):
        values = {
            "capabilities": frozenset({"memory.read", "tool.control_lookup"}),
            "tenant_id": "tenant_synthetic",
            "case_id": "case_vendor_review",
            "allowed_effects": frozenset({"draft"}),
            "max_tool_calls": 1,
            "max_model_calls": 0,
            "valid_until": datetime.now(UTC) + timedelta(hours=1),
            "delegation_depth": 1,
        }
        values.update(changes)
        return CapabilityGrant(**values)

    def memory(self):
        return PrivacyBoundedMemory(
            [
                SyntheticMemoryRecord(
                    evidence_id="evidence_access_review",
                    tenant_id="tenant_synthetic",
                    case_id="case_vendor_review",
                    text="Synthetic quarterly access review completed.",
                    summary="Synthetic access-review test evidence.",
                ),
                SyntheticMemoryRecord(
                    evidence_id="evidence_other_tenant",
                    tenant_id="tenant_other",
                    case_id="case_vendor_review",
                    text="Must never cross the tenant boundary.",
                    summary="Out-of-scope record.",
                ),
            ]
        )

    def test_workflow_integrates_minimized_adapters_with_existing_control_chain(self):
        result = SyntheticVendorAssuranceWorkflow(self.memory()).run(
            context=self.context(),
            specialist_grant=self.grant(),
            question="Does the synthetic vendor perform access reviews?",
            approver_id="reviewer_synthetic",
        )
        self.assertTrue(result.pipeline.audit_valid)
        self.assertTrue(result.pipeline.authorization.authorized)
        self.assertEqual(result.activities[0]["event_type"], "delegation.granted")
        self.assertEqual(result.activities[1]["body"]["result_count"], 1)
        self.assertNotIn("text", result.activities[1]["body"]["results"][0])
        self.assertEqual(result.activities[1]["body"]["minimization_decision"], "minimized")
        self.assertEqual(result.activities[2]["body"]["result_status"], "succeeded")
        self.assertEqual(result.activities[1]["previous_event_hash"], result.activities[0]["record_hash"])
        self.assertEqual(result.activities[3]["event_type"], "authorization.consumed")
        self.assertEqual(result.receipt["effect_status"], "not_observed")
        self.assertEqual(result.reconciliation["effect_status"], "succeeded")
        self.assertEqual(
            result.audit_export["packet_hash"], result.customer_safe_packet["packet_hash"]
        )
        packet_text = str(result.customer_safe_packet)
        self.assertNotIn("Synthetic quarterly access review completed.", packet_text)
        self.assertIn("Synthetic evidence", packet_text)

    def test_trusted_activity_envelope_ignores_adapter_identity_fields(self):
        class FakeStore:
            def __init__(self):
                self.records = []

            def append_agent_activities(self, records):
                self.records.extend(records)

        store = FakeStore()
        workflow = SyntheticVendorAssuranceWorkflow(self.memory(), activity_store=store)
        workflow.run(
            context=self.context(),
            specialist_grant=self.grant(),
            question="synthetic question",
            approver_id="reviewer_synthetic",
        )
        self.assertEqual(len(store.records), 4)
        self.assertTrue(all(item["tenant_id"] == "tenant_synthetic" for item in store.records))
        self.assertEqual([item["sequence"] for item in store.records], [0, 1, 2, 3])

    def test_cross_scope_memory_grant_fails_closed(self):
        with self.assertRaisesRegex(GovernedAdapterError, "outside"):
            self.memory().query(
                context=self.context(),
                grant=self.grant(tenant_id="tenant_other"),
                query="synthetic question",
            )

    def test_missing_tool_capability_and_budget_exhaustion_fail_closed(self):
        workflow = SyntheticVendorAssuranceWorkflow(self.memory())
        with self.assertRaisesRegex(GovernedAdapterError, "not granted"):
            workflow.run(
                context=self.context(),
                specialist_grant=self.grant(capabilities=frozenset({"memory.read"})),
                question="synthetic question",
                approver_id="reviewer_synthetic",
            )
        workflow.run(
            context=self.context(),
            specialist_grant=self.grant(),
            question="synthetic question",
            approver_id="reviewer_synthetic",
        )
        with self.assertRaisesRegex(GovernedAdapterError, "budget exhausted"):
            workflow.run(
                context=self.context(),
                specialist_grant=self.grant(),
                question="synthetic question",
                approver_id="reviewer_synthetic",
            )

    def test_expired_grant_fails_closed(self):
        with self.assertRaisesRegex(GovernedAdapterError, "expired"):
            self.memory().query(
                context=self.context(),
                grant=self.grant(valid_until=datetime.now(UTC) - timedelta(seconds=1)),
                query="synthetic question",
            )


if __name__ == "__main__":
    unittest.main()
