from __future__ import annotations

from provable_agent_reference import (
    EvidenceBundle,
    EvidenceRecord,
    SemanticDraft,
    TrustedRunContext,
)


def context(**changes: object) -> TrustedRunContext:
    values = {
        "tenant_id": "tenant_test",
        "case_id": "case_test",
        "run_id": "run_test",
        "agent_id": "agent_test",
        "purpose": "Prepare a synthetic assurance statement.",
        "audience": "security reviewer",
        "classification": "internal",
        "created_at": "2026-01-01T00:00:00Z",
    }
    values.update(changes)
    return TrustedRunContext(**values)  # type: ignore[arg-type]


def evidence(
    run_context: TrustedRunContext | None = None,
    **changes: object,
) -> EvidenceRecord:
    run_context = run_context or context()
    values = {
        "evidence_id": "evidence_test_001",
        "tenant_id": run_context.tenant_id,
        "case_id": run_context.case_id,
        "text": "Synthetic control test completed.",
        "source_uri": "synthetic://control-test/001",
        "classification": "internal",
        "summary": "Synthetic control-test evidence.",
    }
    values.update(changes)
    return EvidenceRecord.from_text(**values)  # type: ignore[arg-type]


def bundle(
    run_context: TrustedRunContext | None = None,
    record: EvidenceRecord | None = None,
) -> EvidenceBundle:
    run_context = run_context or context()
    record = record or evidence(run_context)
    return EvidenceBundle.create(
        bundle_id="bundle_test",
        tenant_id=run_context.tenant_id,
        case_id=run_context.case_id,
        records=[record],
    )


def draft(evidence_id: str = "evidence_test_001", **changes: object) -> SemanticDraft:
    values = {
        "claim_text": "The synthetic control was tested.",
        "selected_evidence_id": evidence_id,
        "limitations": ("Synthetic evidence only.",),
        "assurance_statement": "A synthetic control test was completed.",
        "content_categories": (),
        "redacted": False,
    }
    values.update(changes)
    return SemanticDraft(**values)  # type: ignore[arg-type]
