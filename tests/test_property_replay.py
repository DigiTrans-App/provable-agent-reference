from __future__ import annotations

import json
import unittest
from dataclasses import fields, replace
from typing import Any

from hypothesis import given
from test_hypothesis_setup import ACTIVE_PROFILE  # noqa: F401
from test_property_strategies import (
    PipelineCase,
    alternate_classification,
    alternate_hash,
    alternate_identifier,
    alternate_text,
    case_label,
    mutate_scalar_field,
    pipeline_cases,
    run_contexts,
    two_record_bundles,
)

from provable_agent_reference import (
    EvidenceBundle,
    EvidenceRecord,
    PipelineResult,
    ProvableAgentPipeline,
    SemanticDraft,
    TrustedRunContext,
    authorize_exact_use,
    build_audit_manifest,
    record_approval,
    verify_audit_manifest,
)
from provable_agent_reference.adapters import AdapterContext, CodexEvidenceAdapter
from provable_agent_reference.assurance_packet import (
    build_assurance_packet,
    verify_assurance_packet,
)
from provable_agent_reference.canonical import sha256_uri
from provable_agent_reference.compiler import TrustedCompiler
from provable_agent_reference.contracts import CanonicalCandidate
from provable_agent_reference.errors import (
    ApprovalError,
    AuthorizationError,
    CompilationError,
    ContractError,
)
from provable_agent_reference.verification import DeterministicVerifier

APPROVER = "human_property_reviewer"
RUN_CONTEXT_FIELDS = tuple(field.name for field in fields(TrustedRunContext))
EVIDENCE_FIELDS = tuple(field.name for field in fields(EvidenceRecord))
CANDIDATE_PAYLOAD_FIELDS = (
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
# Fields whose values link one lifecycle record to another. Each is substituted with a
# well-formed foreign value and the record hash is recomputed, as an attacker could.
RELATIONAL_BINDINGS = {
    "verification": ("candidate_id", "candidate_hash"),
    "approval": ("candidate_id", "candidate_hash", "verification_result_hash", "decision"),
    "authorization": (
        "candidate_id",
        "candidate_hash",
        "approval_id",
        "purpose",
        "audience",
        "output_hash",
        "reason",
    ),
}
MANIFEST_BINDINGS = (
    "candidate_hash",
    "verification_result_hash",
    "approval_record_hash",
    "authorization_record_hash",
)
ADAPTER_CONTEXT_FIELDS = ("tenant_id", "case_id", "run_id", "created_at", "classification")
OUTPUT_REPLAYS = (
    "assurance_statement_changed",
    "limitation_changed",
    "limitation_added",
    "limitations_reordered",
    "field_added",
    "field_removed",
)


def exact_output(result: PipelineResult) -> dict[str, object]:
    return {
        "assurance_statement": result.candidate.assurance_statement,
        "limitations": list(result.candidate.limitations),
    }


def rerun_in_other_run(case: PipelineCase) -> tuple[TrustedRunContext, PipelineResult]:
    context = replace(case.context, run_id=alternate_identifier(case.context.run_id))
    result = ProvableAgentPipeline().run(
        context=context,
        draft=case.draft,
        evidence_bundle=case.bundle,
        approver_id=APPROVER,
    )
    return context, result


def mutate_nested(value: Any, name: str) -> Any:
    """Mutate one field of a frozen record while keeping it syntactically valid."""

    return replace(value, **{name: mutate_scalar_field(name, getattr(value, name))})


def rehash(record: Any) -> Any:
    """Recompute a lifecycle record's own hash, as an attacker controlling storage could."""

    if hasattr(record, "result_hash"):
        return replace(record, result_hash=sha256_uri(record.payload()))
    if hasattr(record, "manifest_hash"):
        return replace(record, manifest_hash=sha256_uri(record.payload()))
    return replace(record, record_hash=sha256_uri(record.payload()))


def audit(records: dict[str, Any], manifest: Any | None = None) -> tuple[bool, tuple[str, ...]]:
    manifest = manifest or build_audit_manifest(
        candidate=records["candidate"],
        verification=records["verification"],
        approval=records["approval"],
        authorization=records["authorization"],
    )
    return verify_audit_manifest(manifest=manifest, **records)


def records_of(result: PipelineResult) -> dict[str, Any]:
    return {
        "candidate": result.candidate,
        "verification": result.verification,
        "approval": result.approval,
        "authorization": result.authorization,
    }


class IntegrityBindingPropertyTests(unittest.TestCase):
    def test_candidate_field_enumeration_matches_the_record_contract(self) -> None:
        declared = {field.name for field in fields(CanonicalCandidate)} - {"candidate_hash"}

        self.assertEqual(set(CANDIDATE_PAYLOAD_FIELDS), declared)

    @given(pipeline_cases())
    def test_every_candidate_field_mutation_invalidates_its_hash_and_is_rejected(
        self,
        case: PipelineCase,
    ) -> None:
        result = case.run()
        candidate = result.candidate
        self.assertTrue(candidate.verify_hash())
        self.assertEqual(set(candidate.payload()), set(CANDIDATE_PAYLOAD_FIELDS))

        mutations: dict[str, Any] = {}
        for name in CANDIDATE_PAYLOAD_FIELDS:
            value = getattr(candidate, name)
            if name == "run_context":
                for nested in RUN_CONTEXT_FIELDS:
                    mutations[f"run_context.{nested}"] = replace(
                        candidate, run_context=mutate_nested(value, nested)
                    )
            elif name == "evidence":
                for nested in EVIDENCE_FIELDS:
                    mutations[f"evidence.{nested}"] = replace(
                        candidate, evidence=mutate_nested(value, nested)
                    )
            elif name == "limitations":
                mutations["limitations.added"] = replace(
                    candidate, limitations=(*value, "Synthetic mutation.")
                )
                mutations["limitations.changed"] = replace(
                    candidate, limitations=(alternate_text(value[0]), *value[1:])
                )
            elif name == "content_categories":
                mutations["content_categories.added"] = replace(
                    candidate, content_categories=(*value, "other")
                )
            else:
                mutations[name] = replace(candidate, **{name: mutate_scalar_field(name, value)})
        mutations["candidate_hash"] = replace(
            candidate, candidate_hash=alternate_hash(candidate.candidate_hash)
        )

        for label, mutated in mutations.items():
            with case_label(field=label):
                self.assertFalse(mutated.verify_hash())
                with self.assertRaisesRegex(ApprovalError, "candidate hash is invalid"):
                    record_approval(
                        candidate=mutated,
                        verification=result.verification,
                        approver_id=APPROVER,
                    )
                with self.assertRaisesRegex(AuthorizationError, "candidate hash is invalid"):
                    authorize_exact_use(
                        candidate=mutated,
                        approval=result.approval,
                        purpose=candidate.run_context.purpose,
                        audience=candidate.run_context.audience,
                        output=exact_output(result),
                    )

    @given(pipeline_cases())
    def test_every_lifecycle_record_field_mutation_invalidates_its_hash(
        self,
        case: PipelineCase,
    ) -> None:
        result = case.run()
        self.assertTrue(result.audit_valid, result.audit_errors)
        records = {
            "verification": result.verification,
            "approval": result.approval,
            "authorization": result.authorization,
            "manifest": result.audit_manifest,
        }
        for record_type, record in records.items():
            self.assertTrue(record.verify_hash(), record_type)
            for name in record.payload():
                with case_label(record=record_type, field=name):
                    if name == "findings":
                        first = record.findings[0]
                        changed = replace(first, message=alternate_text(first.message))
                        mutated = replace(record, findings=(changed, *record.findings[1:]))
                    elif name == "status":
                        # The record constructor rejects a status that contradicts findings.
                        with self.assertRaises(ContractError):
                            replace(record, status="fail" if record.status == "pass" else "pass")
                        continue
                    else:
                        mutated = mutate_nested(record, name)
                    self.assertFalse(mutated.verify_hash())
            stored_hash = next(
                name for name in ("result_hash", "record_hash", "manifest_hash")
                if hasattr(record, name)
            )
            mutated_hash = replace(
                record, **{stored_hash: alternate_hash(getattr(record, stored_hash))}
            )
            self.assertFalse(mutated_hash.verify_hash(), record_type)

    @given(two_record_bundles())
    def test_evidence_sequence_changes_are_bound_and_detected_by_verification(
        self,
        generated: tuple[TrustedRunContext, EvidenceRecord, EvidenceRecord, EvidenceBundle],
    ) -> None:
        context, first, second, original = generated
        third = replace(second, evidence_id="evidence_property_third")

        def bundle(records: tuple[EvidenceRecord, ...]) -> EvidenceBundle:
            return EvidenceBundle.create(
                bundle_id=original.bundle_id,
                tenant_id=context.tenant_id,
                case_id=context.case_id,
                records=records,
            )

        variants = {
            "inserted": bundle((first, second, third)),
            "removed_first": bundle((second,)),
            "removed_second": bundle((first,)),
            "reordered": bundle((second, first)),
            "substituted_content": bundle(
                (first, replace(second, content_hash=alternate_hash(second.content_hash)))
            ),
            "substituted_record": bundle((first, third)),
            "altered_summary": bundle((first, replace(second, summary=alternate_text(second.summary)))),
            "altered_source": bundle(
                (first, replace(second, source_uri=alternate_text(second.source_uri)))
            ),
        }
        rebuilt = bundle((first, second))
        self.assertEqual(rebuilt.bundle_hash, original.bundle_hash)

        compiler = TrustedCompiler()
        verifier = DeterministicVerifier()
        draft_case = PipelineCase(context=context, bundle=original, draft=_draft_for(first))
        candidate = compiler.compile(context=context, draft=draft_case.draft, evidence_bundle=original)
        baseline = verifier.verify(candidate=candidate, evidence_bundle=original)
        self.assertEqual(baseline.status, "pass")

        for label, variant in variants.items():
            with case_label(variant=label):
                self.assertNotEqual(variant.bundle_hash, original.bundle_hash)
                replayed = verifier.verify(candidate=candidate, evidence_bundle=variant)
                self.assertEqual(replayed.status, "fail")
                failed = {item.code for item in replayed.findings if not item.passed}
                self.assertIn("EVIDENCE_BUNDLE_BOUND", failed)

        for duplicate in ((first, first), (first, second, first)):
            with case_label(variant="duplicated", size=len(duplicate)):
                with self.assertRaisesRegex(ContractError, "duplicate evidence"):
                    bundle(duplicate)
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            replace(original, records=(second, first))

    @given(run_contexts())
    def test_cross_tenant_and_case_evidence_is_rejected(self, context: TrustedRunContext) -> None:
        record = EvidenceRecord.from_text(
            evidence_id="evidence_cross_scope",
            tenant_id=context.tenant_id,
            case_id=context.case_id,
            text="Synthetic property-test evidence.",
            source_uri="synthetic://property/cross-scope",
            classification=context.classification,
            summary="Synthetic cross-scope property test.",
        )
        in_scope = EvidenceBundle.create(
            bundle_id="bundle_cross_scope",
            tenant_id=context.tenant_id,
            case_id=context.case_id,
            records=(record,),
        )
        self.assertEqual(in_scope.records, (record,))

        for dimension in ("tenant_id", "case_id"):
            other = {
                "tenant_id": context.tenant_id,
                "case_id": context.case_id,
                dimension: alternate_identifier(getattr(context, dimension)),
            }
            with case_label(dimension=dimension, layer="bundle"):
                with self.assertRaisesRegex(ContractError, "cross-scope"):
                    EvidenceBundle.create(bundle_id="bundle_cross_scope", records=(record,), **other)
            with case_label(dimension=dimension, layer="compiler"):
                foreign = EvidenceBundle.create(
                    bundle_id="bundle_cross_scope",
                    records=(replace(record, **other),),
                    **other,
                )
                with self.assertRaisesRegex(CompilationError, "outside the trusted run scope"):
                    TrustedCompiler().compile(
                        context=context, draft=_draft_for(record), evidence_bundle=foreign
                    )


class ReplayResistancePropertyTests(unittest.TestCase):
    @given(pipeline_cases())
    def test_cross_run_reuse_produces_distinct_bindings(self, case: PipelineCase) -> None:
        first = case.run()
        _, second = rerun_in_other_run(case)

        self.assertTrue(first.audit_valid and second.audit_valid)
        self.assertNotEqual(first.candidate.candidate_id, second.candidate.candidate_id)
        self.assertNotEqual(first.candidate.candidate_hash, second.candidate.candidate_hash)
        self.assertNotEqual(first.candidate.claim_id, second.candidate.claim_id)
        self.assertNotEqual(first.verification.result_hash, second.verification.result_hash)
        self.assertNotEqual(first.approval.approval_id, second.approval.approval_id)
        self.assertNotEqual(first.authorization.record_hash, second.authorization.record_hash)

    @given(pipeline_cases())
    def test_verification_approval_and_authorization_cannot_cross_candidates(
        self,
        case: PipelineCase,
    ) -> None:
        first = case.run()
        second_context, second = rerun_in_other_run(case)

        # Baseline: each run's own records are accepted.
        record_approval(
            candidate=second.candidate, verification=second.verification, approver_id=APPROVER
        )
        with self.assertRaisesRegex(ApprovalError, "different candidate"):
            record_approval(
                candidate=second.candidate,
                verification=first.verification,
                approver_id=APPROVER,
            )
        with self.assertRaisesRegex(AuthorizationError, "different candidate"):
            authorize_exact_use(
                candidate=second.candidate,
                approval=first.approval,
                purpose=second_context.purpose,
                audience=second_context.audience,
                output=exact_output(second),
            )

    @given(pipeline_cases(min_limitations=2))
    def test_exact_use_authorization_rejects_every_scope_and_output_replay(
        self,
        case: PipelineCase,
    ) -> None:
        result = case.run()
        purpose = result.candidate.run_context.purpose
        audience = result.candidate.run_context.audience
        baseline = authorize_exact_use(
            candidate=result.candidate,
            approval=result.approval,
            purpose=purpose,
            audience=audience,
            output=exact_output(result),
        )
        self.assertTrue(baseline.authorized)
        self.assertEqual(baseline.record_hash, result.authorization.record_hash)

        attempts: dict[str, tuple[str, str, dict[str, object]]] = {
            "purpose": (alternate_text(purpose), audience, exact_output(result)),
            "audience": (purpose, alternate_text(audience), exact_output(result)),
        }
        for label in OUTPUT_REPLAYS:
            output: dict[str, Any] = exact_output(result)
            limitations = list(output["limitations"])  # type: ignore[arg-type]
            if label == "assurance_statement_changed":
                output["assurance_statement"] = alternate_text(str(output["assurance_statement"]))
            elif label == "limitation_changed":
                output["limitations"] = [alternate_text(limitations[0]), *limitations[1:]]
            elif label == "limitation_added":
                output["limitations"] = [*limitations, "Synthetic extra limitation."]
            elif label == "limitations_reordered":
                # Order-only change: the same approved limitations, reversed.
                reordered = limitations[::-1]
                self.assertGreaterEqual(len(limitations), 2)
                self.assertEqual(len(reordered), len(limitations))
                self.assertEqual(sorted(reordered), sorted(limitations))
                self.assertNotEqual(reordered, limitations)
                output["limitations"] = reordered
            elif label == "field_added":
                output["extra"] = "Synthetic extra field."
            else:
                del output["limitations"]
            attempts[label] = (purpose, audience, output)

        for label, (attempt_purpose, attempt_audience, attempt_output) in attempts.items():
            with case_label(dimension=label):
                replay = authorize_exact_use(
                    candidate=result.candidate,
                    approval=result.approval,
                    purpose=attempt_purpose,
                    audience=attempt_audience,
                    output=attempt_output,
                )
                self.assertFalse(replay.authorized)
                self.assertEqual(replay.reason, "EXACT_USE_MISMATCH")
                self.assertNotEqual(replay.record_hash, result.authorization.record_hash)

    @given(pipeline_cases())
    def test_non_approved_decisions_cannot_authorize(self, case: PipelineCase) -> None:
        result = case.run()
        for decision in ("rejected", "changes_requested"):
            with case_label(decision=decision):
                approval = record_approval(
                    candidate=result.candidate,
                    verification=result.verification,
                    approver_id=APPROVER,
                    decision=decision,
                )
                with self.assertRaisesRegex(AuthorizationError, "approved decision"):
                    authorize_exact_use(
                        candidate=result.candidate,
                        approval=approval,
                        purpose=result.candidate.run_context.purpose,
                        audience=result.candidate.run_context.audience,
                        output=exact_output(result),
                    )

    @given(pipeline_cases())
    def test_rehashed_linked_record_substitution_fails_audit(self, case: PipelineCase) -> None:
        first = case.run()
        _, second = rerun_in_other_run(case)
        self.assertEqual(audit(records_of(first)), (True, ()))

        # Whole-record substitution from another valid run.
        for stage in ("candidate", "verification", "approval", "authorization"):
            with case_label(substitution="record", stage=stage):
                records = records_of(first)
                records[stage] = records_of(second)[stage]
                self.assertTrue(records[stage].verify_hash())
                valid, errors = audit(records)
                self.assertFalse(valid)
                self.assertTrue(errors)

        # Single relational field substitution with the record hash recomputed.
        for stage, names in RELATIONAL_BINDINGS.items():
            for name in names:
                with case_label(substitution="field", stage=stage, field=name):
                    records = records_of(first)
                    original = getattr(records[stage], name)
                    foreign = getattr(records_of(second)[stage], name)
                    value = foreign if foreign != original else mutate_scalar_field(name, original)
                    forged = rehash(replace(records[stage], **{name: value}))
                    records[stage] = forged
                    self.assertTrue(forged.verify_hash())
                    valid, errors = audit(records)
                    self.assertFalse(valid)
                    self.assertTrue(errors)

        # Manifest binding substitution with the manifest hash recomputed.
        for name in MANIFEST_BINDINGS:
            with case_label(substitution="manifest", field=name):
                forged = rehash(
                    replace(first.audit_manifest, **{name: getattr(second.audit_manifest, name)})
                )
                self.assertTrue(forged.verify_hash())
                valid, errors = audit(records_of(first), manifest=forged)
                self.assertFalse(valid)
                self.assertTrue(any("binding_mismatch" in error for error in errors), errors)

    @given(pipeline_cases())
    def test_assurance_packet_rejects_rehashed_authorized_output_substitution(
        self,
        case: PipelineCase,
    ) -> None:
        result = case.run()
        packet = build_assurance_packet(
            evidence_bundle=case.bundle,
            result=result,
            limitations=("Synthetic packet limitation.",),
        )
        self.assertEqual(verify_assurance_packet(packet), (True, ()))

        substituted = exact_output(result)
        substituted["assurance_statement"] = alternate_text(result.candidate.assurance_statement)
        authorization = rehash(
            replace(result.authorization, output_hash=sha256_uri(substituted))
        )
        manifest = build_audit_manifest(
            candidate=result.candidate,
            verification=result.verification,
            approval=result.approval,
            authorization=authorization,
        )
        for label, output in (("hash_only", packet.authorized_output), ("hash_and_output", substituted)):
            with case_label(variant=label):
                forged = replace(
                    packet,
                    authorization=authorization,
                    audit_manifest=manifest,
                    authorized_output=output,
                )
                forged = replace(forged, packet_hash=sha256_uri(forged.payload()))
                valid, errors = verify_assurance_packet(forged)
                self.assertFalse(valid)
                expected = (
                    "authorized_output_hash_mismatch"
                    if label == "hash_only"
                    else "authorized_output_candidate_mismatch"
                )
                self.assertIn(expected, errors)

    @given(run_contexts())
    def test_adapter_output_is_bound_to_every_trusted_context_field(
        self,
        context: TrustedRunContext,
    ) -> None:
        adapter = CodexEvidenceAdapter()
        base_context = AdapterContext(
            tenant_id=context.tenant_id,
            case_id=context.case_id,
            run_id=context.run_id,
            created_at=context.created_at,
            classification=context.classification,
        )
        self.assertEqual(
            set(base_context.to_dict()), set(ADAPTER_CONTEXT_FIELDS)
        )
        stream = json.dumps({"type": "thread.started", "thread_id": "thread_property_test"})
        first = adapter.build_evidence(context=base_context, execution_jsonl=stream)
        repeat = adapter.build_evidence(context=base_context, execution_jsonl=stream)
        self.assertEqual(first.to_dict(), repeat.to_dict())

        for name in ADAPTER_CONTEXT_FIELDS:
            with case_label(dimension=name):
                value = getattr(base_context, name)
                if name == "classification":
                    changed_value = alternate_classification(value)
                elif name == "created_at":
                    changed_value = alternate_text(value)
                else:
                    changed_value = alternate_identifier(value)
                changed = replace(base_context, **{name: changed_value})
                replay = adapter.build_evidence(context=changed, execution_jsonl=stream)

                self.assertNotEqual(
                    first.evidence_bundle.bundle_hash, replay.evidence_bundle.bundle_hash
                )
                self.assertEqual(replay.context, changed)
                for record in replay.evidence_bundle.records:
                    self.assertEqual(
                        (record.tenant_id, record.case_id, record.classification),
                        (changed.tenant_id, changed.case_id, changed.classification),
                    )


def _draft_for(record: EvidenceRecord) -> SemanticDraft:
    return SemanticDraft(
        claim_text="Synthetic property claim.",
        selected_evidence_id=record.evidence_id,
        limitations=("Synthetic property limitation.",),
        assurance_statement="Synthetic property assurance statement.",
    )


if __name__ == "__main__":
    unittest.main()