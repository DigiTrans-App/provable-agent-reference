from __future__ import annotations

import unittest
from dataclasses import replace

from provable_agent_reference import ProvableAgentPipeline, verify_audit_manifest

from helpers import bundle, context, draft


class AuditPipelineTests(unittest.TestCase):
    def test_end_to_end_pipeline_is_auditable(self) -> None:
        run_context = context()
        evidence_bundle = bundle(run_context)
        result = ProvableAgentPipeline().run(
            context=run_context,
            draft=draft(),
            evidence_bundle=evidence_bundle,
            approver_id="human_reviewer",
        )
        self.assertEqual(result.verification.status, "pass")
        self.assertTrue(result.authorization.authorized)
        self.assertTrue(result.audit_valid)
        self.assertEqual(result.audit_errors, ())

    def test_manifest_substitution_is_detected(self) -> None:
        run_context = context()
        result = ProvableAgentPipeline().run(
            context=run_context,
            draft=draft(),
            evidence_bundle=bundle(run_context),
            approver_id="human_reviewer",
        )
        tampered_manifest = replace(
            result.audit_manifest,
            authorization_record_hash="sha256:" + "0" * 64,
        )
        valid, errors = verify_audit_manifest(
            manifest=tampered_manifest,
            candidate=result.candidate,
            verification=result.verification,
            approval=result.approval,
            authorization=result.authorization,
        )
        self.assertFalse(valid)
        self.assertIn("authorization_binding_mismatch", errors)


if __name__ == "__main__":
    unittest.main()
