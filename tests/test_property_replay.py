from __future__ import annotations

import json
import unittest
from dataclasses import replace

from hypothesis import given
from hypothesis import strategies as st
from test_hypothesis_setup import ACTIVE_PROFILE  # noqa: F401
from test_property_strategies import (
    alternate_identifier,
    alternate_text,
    pipeline_cases,
    run_contexts,
    two_record_bundles,
)

from provable_agent_reference import (
    EvidenceBundle,
    EvidenceRecord,
    ProvableAgentPipeline,
    authorize_exact_use,
    build_audit_manifest,
    record_approval,
    verify_audit_manifest,
)
from provable_agent_reference.adapters import (
    AdapterContext,
    CodexEvidenceAdapter,
)
from provable_agent_reference.canonical import sha256_uri
from provable_agent_reference.errors import ApprovalError, AuthorizationError, ContractError


class IntegrityBindingPropertyTests(unittest.TestCase):
    @given(
        pipeline_cases(),
        st.sampled_from(
            (
                "schema_version",
                "candidate_id",
                "compiler_id",
                "compiler_version",
                "run_context",
                "claim_id",
                "claim_text",
                "evidence",
                "evidence_bundle_hash",
                "limitations",
                "assurance_statement",
                "content_categories",
                "redacted",
                "created_at",
            )
        ),
    )
    def test_any_candidate_payload_mutation_invalidates_its_hash(
        self,
        case,
        field: str,
    ) -> None:
        candidate = case.run().candidate
        if field == "schema_version":
            mutated = replace(
                candidate,
                schema_version=alternate_text(candidate.schema_version),
            )
        elif field == "candidate_id":
            mutated = replace(
                candidate,
                candidate_id=alternate_identifier(candidate.candidate_id),
            )
        elif field == "compiler_id":
            mutated = replace(
                candidate,
                compiler_id=alternate_identifier(candidate.compiler_id),
            )
        elif field == "compiler_version":
            mutated = replace(
                candidate,
                compiler_version=alternate_text(candidate.compiler_version),
            )
        elif field == "run_context":
            mutated_context = replace(
                candidate.run_context,
                run_id=alternate_identifier(candidate.run_context.run_id),
            )
            mutated = replace(candidate, run_context=mutated_context)
        elif field == "claim_id":
            mutated = replace(
                candidate,
                claim_id=alternate_identifier(candidate.claim_id),
            )
        elif field == "claim_text":
            mutated = replace(candidate, claim_text=alternate_text(candidate.claim_text))
        elif field == "evidence":
            mutated_evidence = replace(
                candidate.evidence,
                summary=alternate_text(candidate.evidence.summary),
            )
            mutated = replace(candidate, evidence=mutated_evidence)
        elif field == "evidence_bundle_hash":
            mutated = replace(
                candidate,
                evidence_bundle_hash=sha256_uri(
                    {"other": candidate.evidence_bundle_hash}
                ),
            )
        elif field == "limitations":
            mutated = replace(
                candidate,
                limitations=(*candidate.limitations, "Synthetic mutation."),
            )
        elif field == "assurance_statement":
            mutated = replace(
                candidate,
                assurance_statement=alternate_text(candidate.assurance_statement),
            )
        elif field == "content_categories":
            mutated = replace(
                candidate,
                content_categories=(*candidate.content_categories, "other"),
            )
        elif field == "redacted":
            mutated = replace(candidate, redacted=not candidate.redacted)
        else:
            mutated = replace(
                candidate,
                created_at=alternate_text(candidate.created_at),
            )

        self.assertFalse(mutated.verify_hash())

    @given(
        pipeline_cases(),
        st.sampled_from(
            ("candidate", "verification", "approval", "authorization", "manifest")
        ),
    )
    def test_each_lifecycle_record_rejects_payload_mutation(
        self,
        case,
        record_type: str,
    ) -> None:
        result = case.run()
        if record_type == "candidate":
            mutated = replace(
                result.candidate,
                claim_id=alternate_identifier(result.candidate.claim_id),
            )
        elif record_type == "verification":
            mutated = replace(
                result.verification,
                result_id=alternate_identifier(result.verification.result_id),
            )
        elif record_type == "approval":
            mutated = replace(
                result.approval,
                rationale=alternate_text(result.approval.rationale),
            )
        elif record_type == "authorization":
            mutated = replace(
                result.authorization,
                purpose=alternate_text(result.authorization.purpose),
            )
        else:
            mutated = replace(
                result.audit_manifest,
                generated_at=alternate_text(result.audit_manifest.generated_at),
            )

        self.assertFalse(mutated.verify_hash())

    @given(two_record_bundles())
    def test_evidence_insertion_removal_reordering_and_duplication_are_bound(
        self,
        generated,
    ) -> None:
        context, first, second, original = generated
        removed = EvidenceBundle.create(
            bundle_id=original.bundle_id,
            tenant_id=context.tenant_id,
            case_id=context.case_id,
            records=(first,),
        )
        reordered = EvidenceBundle.create(
            bundle_id=original.bundle_id,
            tenant_id=context.tenant_id,
            case_id=context.case_id,
            records=(second, first),
        )
        altered_second = replace(second, summary=alternate_text(second.summary))
        altered = EvidenceBundle.create(
            bundle_id=original.bundle_id,
            tenant_id=context.tenant_id,
            case_id=context.case_id,
            records=(first, altered_second),
        )

        self.assertNotEqual(original.bundle_hash, removed.bundle_hash)
        self.assertNotEqual(original.bundle_hash, reordered.bundle_hash)
        self.assertNotEqual(original.bundle_hash, altered.bundle_hash)
        with self.assertRaisesRegex(ContractError, "duplicate evidence"):
            EvidenceBundle.create(
                bundle_id=original.bundle_id,
                tenant_id=context.tenant_id,
                case_id=context.case_id,
                records=(first, first),
            )

    @given(run_contexts())
    def test_cross_tenant_and_case_evidence_is_rejected(self, context) -> None:
        record = EvidenceRecord.from_text(
            evidence_id="evidence_cross_scope",
            tenant_id=context.tenant_id,
            case_id=context.case_id,
            text="Synthetic property-test evidence.",
            source_uri="synthetic://property/cross-scope",
            classification=context.classification,
            summary="Synthetic cross-scope property test.",
        )

        with self.assertRaisesRegex(ContractError, "cross-scope"):
            EvidenceBundle.create(
                bundle_id="bundle_cross_scope",
                tenant_id=alternate_identifier(context.tenant_id),
                case_id=context.case_id,
                records=(record,),
            )
        with self.assertRaisesRegex(ContractError, "cross-scope"):
            EvidenceBundle.create(
                bundle_id="bundle_cross_scope",
                tenant_id=context.tenant_id,
                case_id=alternate_identifier(context.case_id),
                records=(record,),
            )


class ReplayResistancePropertyTests(unittest.TestCase):
    @given(pipeline_cases())
    def test_approval_and_authorization_cannot_cross_candidate_boundaries(self, case) -> None:
        first = case.run()
        second_context = replace(
            case.context,
            run_id=alternate_identifier(case.context.run_id),
        )
        second = ProvableAgentPipeline().run(
            context=second_context,
            draft=case.draft,
            evidence_bundle=case.bundle,
            approver_id="human_property_reviewer",
        )

        with self.assertRaisesRegex(ApprovalError, "different candidate"):
            record_approval(
                candidate=second.candidate,
                verification=first.verification,
                approver_id="human_property_reviewer",
            )
        with self.assertRaisesRegex(AuthorizationError, "different candidate"):
            authorize_exact_use(
                candidate=second.candidate,
                approval=first.approval,
                purpose=second_context.purpose,
                audience=second_context.audience,
                output={
                    "assurance_statement": second.candidate.assurance_statement,
                    "limitations": list(second.candidate.limitations),
                },
            )

    @given(
        pipeline_cases(),
        st.sampled_from(("purpose", "audience", "output")),
    )
    def test_exact_use_authorization_rejects_scope_and_output_replay(
        self,
        case,
        replay_dimension: str,
    ) -> None:
        result = case.run()
        purpose = result.candidate.run_context.purpose
        audience = result.candidate.run_context.audience
        output: dict[str, object] = {
            "assurance_statement": result.candidate.assurance_statement,
            "limitations": list(result.candidate.limitations),
        }
        if replay_dimension == "purpose":
            purpose = alternate_text(purpose)
        elif replay_dimension == "audience":
            audience = alternate_text(audience)
        else:
            output["assurance_statement"] = alternate_text(
                result.candidate.assurance_statement
            )

        replay = authorize_exact_use(
            candidate=result.candidate,
            approval=result.approval,
            purpose=purpose,
            audience=audience,
            output=output,
        )

        self.assertFalse(replay.authorized)
        self.assertEqual(replay.reason, "EXACT_USE_MISMATCH")
        self.assertNotEqual(replay.record_hash, result.authorization.record_hash)

    @given(
        pipeline_cases(),
        st.sampled_from(("candidate", "verification", "approval", "authorization")),
    )
    def test_total_rehash_substitution_still_fails_audit_relationships(
        self,
        case,
        substituted_stage: str,
    ) -> None:
        first = case.run()
        second_context = replace(
            case.context,
            run_id=alternate_identifier(case.context.run_id),
        )
        second = ProvableAgentPipeline().run(
            context=second_context,
            draft=case.draft,
            evidence_bundle=case.bundle,
            approver_id="human_property_reviewer",
        )
        candidate = second.candidate if substituted_stage == "candidate" else first.candidate
        verification = (
            second.verification if substituted_stage == "verification" else first.verification
        )
        approval = second.approval if substituted_stage == "approval" else first.approval
        authorization = (
            second.authorization
            if substituted_stage == "authorization"
            else first.authorization
        )
        manifest = build_audit_manifest(
            candidate=candidate,
            verification=verification,
            approval=approval,
            authorization=authorization,
        )

        valid, errors = verify_audit_manifest(
            manifest=manifest,
            candidate=candidate,
            verification=verification,
            approval=approval,
            authorization=authorization,
        )

        self.assertTrue(candidate.verify_hash())
        self.assertTrue(verification.verify_hash())
        self.assertTrue(approval.verify_hash())
        self.assertTrue(authorization.verify_hash())
        self.assertTrue(manifest.verify_hash())
        self.assertFalse(valid)
        self.assertTrue(errors)

    @given(
        run_contexts(),
        st.sampled_from(("tenant_id", "case_id", "run_id")),
    )
    def test_adapter_rebuild_changes_bindings_across_trusted_contexts(
        self,
        context,
        replay_dimension: str,
    ) -> None:
        adapter = CodexEvidenceAdapter()
        base_context = AdapterContext(
            tenant_id=context.tenant_id,
            case_id=context.case_id,
            run_id=context.run_id,
            created_at=context.created_at,
            classification=context.classification,
        )
        changed_context = replace(
            base_context,
            **{
                replay_dimension: alternate_identifier(
                    getattr(base_context, replay_dimension)
                )
            },
        )
        stream = json.dumps(
            {
                "type": "thread.started",
                "thread_id": "thread_property_test",
            }
        )

        first = adapter.build_evidence(
            context=base_context,
            execution_jsonl=stream,
        )
        replay = adapter.build_evidence(
            context=changed_context,
            execution_jsonl=stream,
        )

        self.assertNotEqual(
            first.evidence_bundle.bundle_hash,
            replay.evidence_bundle.bundle_hash,
        )
        self.assertNotEqual(first.to_dict(), replay.to_dict())


if __name__ == "__main__":
    unittest.main()
