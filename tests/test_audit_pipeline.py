from __future__ import annotations

import unittest
from dataclasses import replace

from helpers import bundle, context, draft

from provable_agent_reference import ProvableAgentPipeline, verify_audit_manifest
from provable_agent_reference.audit import build_audit_manifest
from provable_agent_reference.canonical import sha256_uri


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

    def test_unapproved_verification_substitution_is_detected(self) -> None:
        run_context = context()
        result = ProvableAgentPipeline().run(
            context=run_context,
            draft=draft(),
            evidence_bundle=bundle(run_context),
            approver_id="human_reviewer",
        )
        provisional = replace(
            result.verification,
            evaluated_at="2099-01-01T00:00:00Z",
            result_hash="sha256:" + "0" * 64,
        )
        substituted = replace(
            provisional,
            result_hash=sha256_uri(provisional.payload()),
        )
        manifest = build_audit_manifest(
            candidate=result.candidate,
            verification=substituted,
            approval=result.approval,
            authorization=result.authorization,
        )

        valid, errors = verify_audit_manifest(
            manifest=manifest,
            candidate=result.candidate,
            verification=substituted,
            approval=result.approval,
            authorization=result.authorization,
        )

        self.assertFalse(valid)
        self.assertIn("approval_verification_mismatch", errors)

    def test_authorization_from_another_approval_is_detected(self) -> None:
        run_context = context()
        result = ProvableAgentPipeline().run(
            context=run_context,
            draft=draft(),
            evidence_bundle=bundle(run_context),
            approver_id="human_reviewer",
        )
        provisional = replace(
            result.authorization,
            approval_id="approval_other",
            record_hash="sha256:" + "0" * 64,
        )
        substituted = replace(
            provisional,
            record_hash=sha256_uri(provisional.payload()),
        )
        manifest = build_audit_manifest(
            candidate=result.candidate,
            verification=result.verification,
            approval=result.approval,
            authorization=substituted,
        )

        valid, errors = verify_audit_manifest(
            manifest=manifest,
            candidate=result.candidate,
            verification=result.verification,
            approval=result.approval,
            authorization=substituted,
        )

        self.assertFalse(valid)
        self.assertIn("authorization_approval_mismatch", errors)


if __name__ == "__main__":
    unittest.main()
