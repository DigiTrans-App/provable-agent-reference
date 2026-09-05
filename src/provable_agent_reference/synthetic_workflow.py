from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .canonical import sha256_uri
from .contracts import EvidenceBundle, EvidenceRecord, SemanticDraft, TrustedRunContext
from .control_plane.models import CapabilityGrant
from .pipeline import PipelineResult, ProvableAgentPipeline


class GovernedAdapterError(PermissionError):
    """A synthetic adapter request failed closed at an authority boundary."""


@dataclass(frozen=True)
class SyntheticMemoryRecord:
    evidence_id: str
    tenant_id: str
    case_id: str
    text: str
    summary: str
    classification: str = "internal"


class PrivacyBoundedMemory:
    """In-memory synthetic evidence adapter that releases minimized references only."""

    def __init__(self, records: list[SyntheticMemoryRecord]) -> None:
        self._records = tuple(records)

    def query(
        self,
        *,
        context: TrustedRunContext,
        grant: CapabilityGrant,
        query: str,
        limit: int = 10,
    ) -> tuple[tuple[EvidenceRecord, ...], dict[str, Any]]:
        _require_grant(context, grant, "memory.read")
        if not query or not 1 <= limit <= 100:
            raise ValueError("a bounded memory query is required")
        scoped = [
            record
            for record in self._records
            if (record.tenant_id, record.case_id) == (context.tenant_id, context.case_id)
        ]
        selected = scoped[:limit]
        evidence = tuple(
            EvidenceRecord.from_text(
                evidence_id=record.evidence_id,
                tenant_id=record.tenant_id,
                case_id=record.case_id,
                text=record.text,
                source_uri=f"synthetic://memory/{record.evidence_id}",
                classification=record.classification,  # type: ignore[arg-type]
                summary=record.summary,
            )
            for record in selected
        )
        references = [
            {
                "reference_id": item.evidence_id,
                "content_commitment": item.content_hash,
                "source_ref": item.source_uri,
                "provenance_ref": f"synthetic:fixture:{item.evidence_id}",
                "classification": item.classification,
                "freshness_status": "current",
                "integrity_status": "verified",
            }
            for item in evidence
        ]
        activity = {
            "body_type": "memory_access",
            "memory_provider": "embedded synthetic fixture",
            "store_id": "store_synthetic_vendor_assurance",
            "namespace": f"{context.tenant_id}/{context.case_id}",
            "adapter": {
                "adapter_id": "adapter.synthetic_memory",
                "adapter_version": "0.1.0",
            },
            "access_purpose": context.purpose,
            "allowed_classifications": [context.classification],
            "filters_commitment": sha256_uri(
                {"tenant_id": context.tenant_id, "case_id": context.case_id}
            ),
            "result_limit": limit,
            "query_commitment": sha256_uri({"query": query}),
            "commitment_key_ref": "synthetic:unkeyed-development-commitment",
            "result_set_commitment": sha256_uri(references),
            "result_count": len(evidence),
            "truncated": len(scoped) > limit,
            "results": references,
            "disclosure_mode": "reference",
            "minimization_decision": "minimized",
            "retention_class": "synthetic_ephemeral",
            "access_decision": "allow",
            "evidence_object_refs": [item.evidence_id for item in evidence],
            "errors": [],
        }
        return evidence, activity


class PolicyEnforcingToolGateway:
    """Capability and budget gate for deterministic, non-networked synthetic tools."""

    def __init__(self) -> None:
        self._calls: dict[tuple[str, str], int] = {}

    def invoke(
        self,
        *,
        context: TrustedRunContext,
        grant: CapabilityGrant,
        tool_id: str,
        request: dict[str, Any],
        idempotency_key: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        _require_grant(context, grant, f"tool.{tool_id}")
        if tool_id != "control_lookup":
            raise GovernedAdapterError("tool is not on the synthetic allowlist")
        if not idempotency_key or len(idempotency_key) > 500:
            raise ValueError("a bounded idempotency key is required")
        budget_key = (context.run_id, context.agent_id)
        calls = self._calls.get(budget_key, 0)
        if calls >= grant.max_tool_calls:
            raise GovernedAdapterError("tool-call budget exhausted")
        self._calls[budget_key] = calls + 1
        result = {
            "control_id": str(request.get("control_id", "CTL-SYNTHETIC-UNKNOWN")),
            "status": "synthetic_pass",
            "source": "embedded_synthetic_fixture",
        }
        activity = {
            "body_type": "tool_activity",
            "phase": "completed",
            "tool_id": "control_lookup",
            "tool_version": "0.1.0",
            "capability_id": f"tool.{tool_id}",
            "request_hash": sha256_uri(request),
            "idempotency_key_commitment": sha256_uri({"key": idempotency_key}),
            "result_hash": sha256_uri(result),
            "result_status": "succeeded",
            "completeness": "complete",
        }
        return result, activity


@dataclass(frozen=True)
class SyntheticWorkflowResult:
    pipeline: PipelineResult
    activities: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline": self.pipeline.to_dict(),
            "activities": list(self.activities),
            "limitations": [
                "Synthetic evidence and identities only.",
                "No network destination or external effect is reachable.",
                "Agent outputs are proposals; trusted code assigns authority and scope.",
            ],
        }


class SyntheticVendorAssuranceWorkflow:
    """Deterministic first PR C slice spanning specialist adapters and the v0.3 chain."""

    def __init__(self, memory: PrivacyBoundedMemory) -> None:
        self.memory = memory
        self.gateway = PolicyEnforcingToolGateway()

    def run(
        self,
        *,
        context: TrustedRunContext,
        specialist_grant: CapabilityGrant,
        question: str,
        approver_id: str,
    ) -> SyntheticWorkflowResult:
        evidence, memory_activity = self.memory.query(
            context=context, grant=specialist_grant, query=question, limit=10
        )
        if not evidence:
            raise GovernedAdapterError("no in-scope evidence is available")
        tool_result, tool_activity = self.gateway.invoke(
            context=context,
            grant=specialist_grant,
            tool_id="control_lookup",
            request={"control_id": "CTL-SYNTHETIC-ACCESS-REVIEW"},
            idempotency_key=f"{context.run_id}:control-lookup",
        )
        selected = evidence[0]
        draft = SemanticDraft(
            claim_text="The synthetic access-review control has supporting test evidence.",
            selected_evidence_id=selected.evidence_id,
            limitations=("Synthetic evidence only; no production control is assessed.",),
            assurance_statement=(
                "Synthetic access-review evidence was located and the embedded control fixture "
                f"reported {tool_result['status']}."
            ),
        )
        bundle = EvidenceBundle.create(
            bundle_id="bundle_" + sha256_uri([item.to_dict() for item in evidence])[7:31],
            tenant_id=context.tenant_id,
            case_id=context.case_id,
            records=evidence,
        )
        pipeline = ProvableAgentPipeline().run(
            context=context,
            draft=draft,
            evidence_bundle=bundle,
            approver_id=approver_id,
        )
        return SyntheticWorkflowResult(pipeline, (memory_activity, tool_activity))


def _require_grant(
    context: TrustedRunContext, grant: CapabilityGrant, capability: str
) -> None:
    now = datetime.now(UTC)
    if grant.valid_until <= now:
        raise GovernedAdapterError("capability grant is expired")
    if (grant.tenant_id, grant.case_id) != (context.tenant_id, context.case_id):
        raise GovernedAdapterError("capability grant is outside the trusted run scope")
    if capability not in grant.capabilities:
        raise GovernedAdapterError("required capability is not granted")
