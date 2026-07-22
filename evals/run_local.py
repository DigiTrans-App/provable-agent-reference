from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from graders import grade  # noqa: E402

from provable_agent_reference import (  # noqa: E402
    DeterministicVerifier,
    EvidenceBundle,
    EvidenceRecord,
    ProvableAgentPipeline,
    SemanticDraft,
    TrustedCompiler,
    TrustedRunContext,
    authorize_exact_use,
    record_approval,
    verify_audit_manifest,
)
from provable_agent_reference.errors import ContractError  # noqa: E402


def fixture() -> tuple[TrustedRunContext, EvidenceBundle, SemanticDraft]:
    context = TrustedRunContext(
        tenant_id="tenant_eval",
        case_id="case_eval",
        run_id="run_eval",
        agent_id="agent_eval",
        purpose="Prepare a bounded synthetic evaluation statement.",
        audience="synthetic reviewer",
        classification="internal",
        created_at="2026-01-01T00:00:00Z",
    )
    evidence = EvidenceRecord.from_text(
        evidence_id="evidence_eval",
        tenant_id=context.tenant_id,
        case_id=context.case_id,
        text="Synthetic evaluation evidence.",
        source_uri="synthetic://evals/control/001",
        classification="internal",
        summary="Synthetic evaluation evidence.",
    )
    bundle = EvidenceBundle.create(
        bundle_id="bundle_eval",
        tenant_id=context.tenant_id,
        case_id=context.case_id,
        records=[evidence],
    )
    draft = SemanticDraft(
        claim_text="A synthetic control was evaluated.",
        selected_evidence_id=evidence.evidence_id,
        limitations=("Synthetic evidence only.",),
        assurance_statement="Synthetic evidence indicates that the control was evaluated.",
        content_categories=(),
        redacted=False,
    )
    return context, bundle, draft


def compiled() -> tuple[Any, Any, Any]:
    context, bundle, draft = fixture()
    candidate = TrustedCompiler().compile(
        context=context,
        draft=draft,
        evidence_bundle=bundle,
    )
    verification = DeterministicVerifier().verify(
        candidate=candidate,
        evidence_bundle=bundle,
    )
    return context, candidate, verification


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_id = case["id"]
    context, bundle, draft = fixture()

    if case_id == "happy_path":
        result = ProvableAgentPipeline().run(
            context=context,
            draft=draft,
            evidence_bundle=bundle,
            approver_id="human_eval_reviewer",
        )
        return {
            "status": "completed" if result.audit_valid else "failed",
            "verification": result.verification.status,
            "authorized": result.authorization.authorized,
        }

    if case_id == "unknown_evidence":
        invalid = replace(draft, selected_evidence_id="evidence_unknown")
        try:
            TrustedCompiler().compile(
                context=context,
                draft=invalid,
                evidence_bundle=bundle,
            )
        except ContractError:
            return {"status": "compilation_error"}

    if case_id == "forbidden_disclosure":
        unsafe = replace(draft, content_categories=("credential",), redacted=False)
        candidate = TrustedCompiler().compile(
            context=context,
            draft=unsafe,
            evidence_bundle=bundle,
        )
        verification = DeterministicVerifier().verify(
            candidate=candidate,
            evidence_bundle=bundle,
        )
        return {
            "status": "verification_failed" if verification.status == "fail" else "failed",
            "finding_codes": [
                finding.code for finding in verification.findings if not finding.passed
            ],
        }

    if case_id in {"output_substitution", "purpose_drift"}:
        current_context, candidate, verification = compiled()
        approval = record_approval(
            candidate=candidate,
            verification=verification,
            approver_id="human_eval_reviewer",
        )
        output = {
            "assurance_statement": candidate.assurance_statement,
            "limitations": list(candidate.limitations),
        }
        purpose = current_context.purpose
        if case_id == "output_substitution":
            output["assurance_statement"] = "Substituted output."
        else:
            purpose = "Different unapproved purpose."
        authorization = authorize_exact_use(
            candidate=candidate,
            approval=approval,
            purpose=purpose,
            audience=current_context.audience,
            output=output,
        )
        return {
            "status": "authorization_denied" if not authorization.authorized else "failed"
        }

    if case_id == "audit_manifest_tamper":
        result = ProvableAgentPipeline().run(
            context=context,
            draft=draft,
            evidence_bundle=bundle,
            approver_id="human_eval_reviewer",
        )
        tampered = replace(
            result.audit_manifest,
            authorization_record_hash="sha256:" + "0" * 64,
        )
        valid, errors = verify_audit_manifest(
            manifest=tampered,
            candidate=result.candidate,
            verification=result.verification,
            approval=result.approval,
            authorization=result.authorization,
        )
        return {
            "status": "completed" if valid else "audit_failure",
            "errors": list(errors),
        }

    raise RuntimeError(f"unknown evaluation case: {case_id}")


def main() -> int:
    cases = [
        json.loads(line)
        for line in (Path(__file__).parent / "cases.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    results: list[dict[str, Any]] = []
    for case in cases:
        result = run_case(case)
        result["id"] = case["id"]
        result["grade"] = grade(case, result)
        results.append(result)
    summary = {
        "suite": "provable-agent-reference-local-0.1",
        "case_count": len(results),
        "passed": all(item["grade"]["passed"] for item in results),
        "cases": results,
    }
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    (results_dir / "latest.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"case_count": len(results), "passed": summary["passed"]}))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
