from __future__ import annotations

import json
from pathlib import Path

from provable_agent_reference import EvidenceBundle, EvidenceRecord, SemanticDraft, TrustedRunContext
from provable_agent_reference.demo import run_demo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "records"


def main() -> None:
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
    result = run_demo()
    records = {
        "semantic-draft.example.json": draft.to_dict(),
        "evidence-record.example.json": evidence.to_dict(),
        "evidence-bundle.example.json": bundle.to_dict(),
        "canonical-candidate.example.json": result.candidate.to_dict(),
        "verification-result.example.json": result.verification.to_dict(),
        "approval-record.example.json": result.approval.to_dict(),
        "authorization-result.example.json": result.authorization.to_dict(),
        "audit-manifest.example.json": result.audit_manifest.to_dict(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for name, value in records.items():
        (OUT / name).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
