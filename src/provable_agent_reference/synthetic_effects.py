from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical import sha256_uri
from .contracts import AuthorizationResult, TrustedRunContext

RECEIPT_SCHEMA = (
    "https://digitrans.app/schemas/provable-agent-reference/execution-receipt.schema.json"
)
RECONCILIATION_SCHEMA = (
    "https://digitrans.app/schemas/provable-agent-reference/reconciliation-record.schema.json"
)
SYNTHETIC_TARGET = "synthetic://customer-review/inbox"


class SyntheticEffectError(PermissionError):
    """A simulated effect was rejected at a trusted lifecycle boundary."""


class AuthorizationLifecycle:
    """In-process synthetic lifecycle registry enforcing single consumption."""

    def __init__(self) -> None:
        self._states: dict[str, str] = {}

    def transition(
        self,
        authorization: AuthorizationResult,
        status: str,
        *,
        effective_at: str,
        successor_ref: str | None = None,
    ) -> dict[str, Any]:
        if not authorization.authorized or not authorization.verify_hash():
            raise SyntheticEffectError("authorization is invalid or denied")
        current = self._states.get(authorization.authorization_id)
        if status == "consumed" and current is not None:
            raise SyntheticEffectError("authorization is no longer consumable")
        if status not in {"consumed", "revoked", "superseded"}:
            raise ValueError("unsupported synthetic lifecycle transition")
        if status == "superseded" and not successor_ref:
            raise ValueError("supersession requires a successor reference")
        if status != "superseded" and successor_ref is not None:
            raise ValueError("successor reference is exclusive to supersession")
        self._states[authorization.authorization_id] = status
        return {
            "body_type": "lifecycle_status",
            "target_id": authorization.authorization_id,
            "target_hash": authorization.record_hash,
            "status": status,
            "authority": {
                "subject": "control-plane:synthetic",
                "issuer": "synthetic://local-test-issuer",
                "actor_type": "control_plane",
            },
            "effective_at": effective_at,
            "reason": f"Synthetic authorization {status}.",
            "successor_ref": successor_ref,
        }


@dataclass(frozen=True)
class SyntheticEffectExecutor:
    """Non-networked adapter that emits portable draft receipts for fixed outcomes."""

    provider: str = "embedded_synthetic_effect_provider"

    def execute(
        self,
        *,
        context: TrustedRunContext,
        authorization: AuthorizationResult,
        output: dict[str, Any],
        target_ref: str,
        outcome: str,
    ) -> dict[str, Any]:
        if target_ref != SYNTHETIC_TARGET:
            raise SyntheticEffectError("only the embedded synthetic target is reachable")
        if not authorization.authorized or not authorization.verify_hash():
            raise SyntheticEffectError("authorization is invalid or denied")
        if sha256_uri(output) != authorization.output_hash:
            raise SyntheticEffectError("effect output differs from the exact-use authorization")
        if outcome not in {"acknowledged", "observed", "unknown"}:
            raise ValueError("unsupported synthetic effect outcome")
        operation_id = "operation_" + authorization.authorization_id[-24:]
        attempt_id = "attempt_" + sha256_uri({"operation_id": operation_id, "attempt": 1})[7:31]
        receipt_id = "receipt_" + sha256_uri({"attempt_id": attempt_id})[7:31]
        observed = outcome == "observed"
        acknowledged = outcome in {"acknowledged", "observed"}
        provider_evidence = None
        if acknowledged:
            evidence = {"receipt_id": receipt_id, "outcome": outcome}
            provider_evidence = {
                "evidence_type": "state_snapshot" if observed else "delivery_record",
                "provider_receipt_ref": f"synthetic:receipt:{receipt_id}",
                "evidence_hash": sha256_uri(evidence),
                "semantics_version": "0.1.0",
                "effect_semantics": "observed_effect" if observed else "acknowledgement_only",
            }
        payload = {
            "$schema": RECEIPT_SCHEMA,
            "schema_version": "0.1-draft",
            "receipt_id": receipt_id,
            "tenant_id": context.tenant_id,
            "case_id": context.case_id,
            "run_id": context.run_id,
            "operation_id": operation_id,
            "attempt_id": attempt_id,
            "correlation_id": f"correlation_{context.run_id}",
            "authorization_id": authorization.authorization_id,
            "authorization_hash": authorization.record_hash,
            "executor": {
                "subject": "executor:synthetic",
                "issuer": "synthetic://local-test-issuer",
                "actor_type": "effect_executor",
            },
            "adapter": {"adapter_id": "adapter.synthetic_effect", "adapter_version": "0.1.0"},
            "provider": self.provider,
            "operation_type": "customer_safe_packet_delivery",
            "policy_version": "policy:synthetic:1",
            "action_hash": sha256_uri({"output": output, "target_ref": target_ref}),
            "target_ref": target_ref,
            "idempotency_key_commitment": sha256_uri({"operation_id": operation_id}),
            "attempt_number": 1,
            "submitted_at": context.created_at if outcome != "unknown" else None,
            "acknowledged_at": context.created_at if acknowledged else None,
            "observed_at": context.created_at if observed else None,
            "reconciled_at": None,
            "time_assurance": {
                "submitted": "source_declared" if outcome != "unknown" else "unavailable",
                "acknowledged": "source_declared" if acknowledged else "unavailable",
                "observed": "source_declared" if observed else "unavailable",
                "reconciled": "unavailable",
            },
            "provider_evidence": provider_evidence,
            "submission_status": "acknowledged" if observed else outcome,
            "effect_status": "succeeded" if observed else ("unknown" if outcome == "unknown" else "not_observed"),
            "reconciliation_required": not observed,
            "reconciliation_method": None,
            "errors": [],
            "authenticated_record_ref": None,
            "limitations": ["Embedded synthetic effect; no external delivery occurred."],
        }
        return {**payload, "record_hash": sha256_uri(payload)}

    def reconcile(
        self,
        receipt: dict[str, Any],
        *,
        observed_effect: bool,
        reconciled_at: str,
    ) -> dict[str, Any]:
        receipt_payload = {key: value for key, value in receipt.items() if key != "record_hash"}
        if receipt.get("record_hash") != sha256_uri(receipt_payload):
            raise SyntheticEffectError("receipt integrity verification failed")
        effect_status = "succeeded" if observed_effect else "unknown"
        payload = {
            "$schema": RECONCILIATION_SCHEMA,
            "schema_version": "0.1-draft",
            "reconciliation_id": "reconciliation_" + receipt["receipt_id"][-24:],
            "tenant_id": receipt["tenant_id"],
            "case_id": receipt["case_id"],
            "run_id": receipt["run_id"],
            "receipt_id": receipt["receipt_id"],
            "receipt_hash": receipt["record_hash"],
            "method": "state_comparison",
            "effect_status": effect_status,
            "reconciled_at": reconciled_at,
            "evidence_refs": [f"synthetic:state:{receipt['operation_id']}"],
            "discrepancies": [] if observed_effect else ["Synthetic effect remains unobserved."],
            "compensating_authorization_id": None,
            "limitations": ["Synthetic state comparison; no provider system was queried."],
        }
        return {**payload, "record_hash": sha256_uri(payload)}
