from __future__ import annotations

from .contracts import EvidenceBundle, EvidenceRecord, SemanticDraft, TrustedRunContext
from .pipeline import PipelineResult, ProvableAgentPipeline


def run_demo() -> PipelineResult:
    context = TrustedRunContext(
        tenant_id="tenant_demo",
        case_id="case_demo",
        run_id="run_demo",
        agent_id="agent_demo",
        purpose="Prepare a synthetic assurance statement.",
        audience="security reviewer",
        classification="internal",
        created_at="2026-01-01T00:00:00Z",
    )
    evidence = EvidenceRecord.from_text(
        evidence_id="evidence_control_001",
        tenant_id=context.tenant_id,
        case_id=context.case_id,
        text="Synthetic access review control test completed successfully.",
        source_uri="synthetic://control-test/001",
        classification="internal",
        summary="Synthetic access-review control-test evidence.",
    )
    bundle = EvidenceBundle.create(
        bundle_id="bundle_demo",
        tenant_id=context.tenant_id,
        case_id=context.case_id,
        records=[evidence],
    )
    draft = SemanticDraft(
        claim_text="The synthetic access-review control was tested.",
        selected_evidence_id=evidence.evidence_id,
        limitations=("Synthetic evidence only; no production control is assessed.",),
        assurance_statement="A synthetic access-review control test was completed.",
        content_categories=(),
        redacted=False,
    )
    return ProvableAgentPipeline().run(
        context=context,
        draft=draft,
        evidence_bundle=bundle,
        approver_id="human_reviewer",
    )
