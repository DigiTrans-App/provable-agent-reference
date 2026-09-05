from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .canonical import sha256_uri
from .contracts import EvidenceBundle, EvidenceRecord, SemanticDraft, TrustedRunContext
from .control_plane.models import CapabilityGrant
from .pipeline import PipelineResult, ProvableAgentPipeline
from .synthetic_effects import (
    SYNTHETIC_TARGET,
    AuthorizationLifecycle,
    SyntheticEffectExecutor,
)


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
    receipt: dict[str, Any]
    reconciliation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline": self.pipeline.to_dict(),
            "activities": list(self.activities),
            "receipt": self.receipt,
            "reconciliation": self.reconciliation,
            "limitations": [
                "Synthetic evidence and identities only.",
                "No network destination or external effect is reachable.",
                "Agent outputs are proposals; trusted code assigns authority and scope.",
            ],
        }


class SyntheticVendorAssuranceWorkflow:
    """Deterministic first PR C slice spanning specialist adapters and the v0.3 chain."""

    def __init__(self, memory: PrivacyBoundedMemory, activity_store=None) -> None:
        self.memory = memory
        self.gateway = PolicyEnforcingToolGateway()
        self.effects = SyntheticEffectExecutor()
        self.lifecycle = AuthorizationLifecycle()
        self.activity_store = activity_store

    def run(
        self,
        *,
        context: TrustedRunContext,
        specialist_grant: CapabilityGrant,
        question: str,
        approver_id: str,
    ) -> SyntheticWorkflowResult:
        builder = ActivityRecordBuilder(context)
        delegation = builder.append(
            "delegation.granted",
            {
                "body_type": "delegation",
                "delegation_id": f"delegation_{context.run_id}",
                "parent_subject": "agent:synthetic-orchestrator",
                "child_subject": f"agent:{context.agent_id}",
                "task": question,
                "capability_grant": sorted(specialist_grant.capabilities),
                "budget": {
                    "max_tool_calls": specialist_grant.max_tool_calls,
                    "max_model_calls": specialist_grant.max_model_calls,
                },
                "valid_until": specialist_grant.valid_until.isoformat(),
                "status": "granted",
            },
            actor_subject="agent:synthetic-orchestrator",
            actor_type="agent",
        )
        evidence, memory_body = self.memory.query(
            context=context, grant=specialist_grant, query=question, limit=10
        )
        memory_activity = builder.append(
            "memory.accessed",
            memory_body,
            actor_subject=f"agent:{context.agent_id}",
            actor_type="agent",
        )
        if not evidence:
            raise GovernedAdapterError("no in-scope evidence is available")
        tool_result, tool_body = self.gateway.invoke(
            context=context,
            grant=specialist_grant,
            tool_id="control_lookup",
            request={"control_id": "CTL-SYNTHETIC-ACCESS-REVIEW"},
            idempotency_key=f"{context.run_id}:control-lookup",
        )
        tool_activity = builder.append(
            "tool.completed",
            tool_body,
            actor_subject="gateway:synthetic-tool",
            actor_type="tool_gateway",
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
        lifecycle_body = self.lifecycle.transition(
            pipeline.authorization, "consumed", effective_at=context.created_at
        )
        lifecycle_activity = builder.append(
            "authorization.consumed",
            lifecycle_body,
            actor_subject="control-plane:synthetic",
            actor_type="control_plane",
        )
        output = {
            "assurance_statement": pipeline.candidate.assurance_statement,
            "limitations": list(pipeline.candidate.limitations),
        }
        receipt = self.effects.execute(
            context=context,
            authorization=pipeline.authorization,
            output=output,
            target_ref=SYNTHETIC_TARGET,
            outcome="acknowledged",
        )
        reconciliation = self.effects.reconcile(
            receipt, observed_effect=True, reconciled_at=context.created_at
        )
        activities = (delegation, memory_activity, tool_activity, lifecycle_activity)
        if self.activity_store is not None:
            self.activity_store.append_agent_activities(list(activities))
        return SyntheticWorkflowResult(pipeline, activities, receipt, reconciliation)


class ActivityRecordBuilder:
    """Assign trusted identity, ordering, and hashes around untrusted activity bodies."""

    def __init__(self, context: TrustedRunContext) -> None:
        self.context = context
        self.previous_hash: str | None = None
        self.sequence = 0

    def append(
        self,
        event_type: str,
        body: dict[str, Any],
        *,
        actor_subject: str,
        actor_type: str,
    ) -> dict[str, Any]:
        body_hash = sha256_uri(body)
        event_id = "event_" + sha256_uri(
            {
                "run_id": self.context.run_id,
                "sequence": self.sequence,
                "event_type": event_type,
                "body_hash": body_hash,
            }
        )[7:31]
        payload = {
            "$schema": (
                "https://digitrans.app/schemas/provable-agent-reference/"
                "agent-activity-record.schema.json"
            ),
            "event_version": "0.1-draft",
            "record_type": "agent_activity",
            "event_id": event_id,
            "event_type": event_type,
            "tenant_id": self.context.tenant_id,
            "case_id": self.context.case_id,
            "run_id": self.context.run_id,
            "parent_run_id": None,
            "sequence": self.sequence,
            "actor": {
                "subject": actor_subject,
                "issuer": "synthetic://local-test-issuer",
                "actor_type": actor_type,
            },
            "policy_version": "policy:synthetic:1",
            "occurred_at": self.context.created_at,
            "occurred_at_assurance": "source_declared",
            "observed_at": self.context.created_at,
            "observed_at_assurance": "control_plane_observed",
            "previous_event_hash": self.previous_hash,
            "correlation_id": f"correlation_{self.context.run_id}",
            "operation_id": None,
            "attempt_id": None,
            "body": body,
            "body_hash": body_hash,
            "limitations": ["Synthetic activity with development-only time assurance."],
        }
        record = {**payload, "record_hash": sha256_uri(payload)}
        self.sequence += 1
        self.previous_hash = record["record_hash"]
        return record


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
