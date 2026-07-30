from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..canonical import canonical_json, sha256_uri
from ..contracts import EvidenceBundle, EvidenceRecord
from ._codex_common import hash_text, parse_jsonl, source_uri
from ._codex_execution import normalize_execution_events
from ._codex_telemetry import normalize_telemetry_events
from .base import AdapterContext, AdapterResult, AdapterValidationError, CoverageFinding


class CodexEvidenceAdapter:
    """Normalize Codex JSON and telemetry streams without retaining raw content."""

    runtime = "codex"
    adapter_version = "0.1.0"

    def build_evidence(
        self,
        *,
        context: AdapterContext,
        execution_jsonl: str,
        telemetry_jsonl: str = "",
    ) -> AdapterResult:
        execution_events = parse_jsonl("execution_jsonl", execution_jsonl)
        telemetry_events = parse_jsonl("telemetry_jsonl", telemetry_jsonl)

        exec_document, exec_facts = normalize_execution_events(context, execution_events)
        telemetry_document, telemetry_facts = normalize_telemetry_events(
            context, telemetry_events
        )
        accepted_count = exec_facts["accepted"] + telemetry_facts["accepted"]
        ignored_count = exec_facts["ignored"] + telemetry_facts["ignored"]
        if accepted_count == 0:
            raise AdapterValidationError("no supported Codex events were found")

        coverage = _build_coverage(exec_facts, telemetry_facts)
        coverage_document = {
            "schema_version": "runtime-evidence-coverage/v0.1",
            "runtime": self.runtime,
            "adapter_version": self.adapter_version,
            "run_id_hash": hash_text(context.run_id),
            "findings": [finding.to_dict() for finding in coverage],
        }

        execution_stream_hash = hash_text(execution_jsonl)
        telemetry_stream_hash = hash_text(telemetry_jsonl)
        execution_text = canonical_json(exec_document)
        telemetry_text = canonical_json(telemetry_document)
        coverage_text = canonical_json(coverage_document)

        records = (
            EvidenceRecord.from_text(
                evidence_id="evidence_codex_exec",
                tenant_id=context.tenant_id,
                case_id=context.case_id,
                text=execution_text,
                source_uri=source_uri("exec", execution_stream_hash),
                classification=context.classification,
                summary=(
                    "Privacy-minimized normalized Codex execution evidence with "
                    f"{exec_facts['accepted']} accepted and {exec_facts['ignored']} ignored events."
                ),
            ),
            EvidenceRecord.from_text(
                evidence_id="evidence_codex_telemetry",
                tenant_id=context.tenant_id,
                case_id=context.case_id,
                text=telemetry_text,
                source_uri=source_uri("telemetry", telemetry_stream_hash),
                classification=context.classification,
                summary=(
                    "Privacy-minimized normalized Codex telemetry evidence with "
                    f"{telemetry_facts['matched']} matched communication lifecycles and "
                    f"{telemetry_facts['unmatched_sends']} unmatched sends."
                ),
            ),
            EvidenceRecord.from_text(
                evidence_id="evidence_codex_coverage",
                tenant_id=context.tenant_id,
                case_id=context.case_id,
                text=coverage_text,
                source_uri=source_uri("coverage", hash_text(coverage_text)),
                classification=context.classification,
                summary="Explicit coverage and limitation report for the Codex evidence adapter.",
            ),
        )
        bundle_seed = {
            "runtime": self.runtime,
            "adapter_version": self.adapter_version,
            "run_id_hash": hash_text(context.run_id),
            "record_hashes": [record.content_hash for record in records],
        }
        bundle_suffix = sha256_uri(bundle_seed).removeprefix("sha256:")[:20]
        bundle = EvidenceBundle.create(
            bundle_id=f"bundle_codex_{bundle_suffix}",
            tenant_id=context.tenant_id,
            case_id=context.case_id,
            records=records,
        )
        return AdapterResult(
            runtime=self.runtime,
            adapter_version=self.adapter_version,
            context=context,
            evidence_bundle=bundle,
            coverage=coverage,
            accepted_event_count=accepted_count,
            ignored_event_count=ignored_count,
            source_stream_hashes=(execution_stream_hash, telemetry_stream_hash),
        )


def _build_coverage(
    exec_facts: Mapping[str, Any], telemetry_facts: Mapping[str, Any]
) -> tuple[CoverageFinding, ...]:
    if exec_facts["accepted"]:
        exec_status = "available"
        exec_detail = "Supported Codex execution events were normalized and hash-bound."
    else:
        exec_status = "unavailable"
        exec_detail = "No supported Codex execution events were supplied."

    if exec_facts["observed_activity"]:
        activity_status = "available"
        activity_detail = "Command, file, MCP, or web activity was observed in item events."
    else:
        activity_status = "unavailable"
        activity_detail = "No supported command, file, MCP, or web activity item was observed."

    if telemetry_facts["send_count"] == 0:
        lifecycle_status = "unavailable"
        lifecycle_detail = "No Codex agent communication send event was supplied."
    elif telemetry_facts["unmatched_sends"]:
        lifecycle_status = "partial"
        lifecycle_detail = (
            "At least one communication send lacked a correlated receive event; "
            "the adapter did not infer delivery."
        )
    else:
        lifecycle_status = "available"
        lifecycle_detail = "Every supplied communication send had a correlated receive event."

    task_count = telemetry_facts["task_message_count"]
    readable_count = telemetry_facts["readable_task_formats"]
    if task_count and readable_count == task_count:
        readable_status = "available"
        readable_detail = (
            "Every supplied task communication explicitly declared content_format=plaintext_audit; "
            "only content hashes were retained."
        )
    elif readable_count:
        readable_status = "partial"
        readable_detail = (
            "Only some task communications explicitly declared plaintext audit representation; "
            "the remainder were not interpreted."
        )
    else:
        readable_status = "unavailable"
        readable_detail = (
            "The source stream did not explicitly attest that task content was "
            "readable audit text; "
            "the adapter does not infer plaintext from a content field (see openai/codex#28058)."
        )

    return (
        CoverageFinding("exec_event_stream", exec_status, exec_detail),
        CoverageFinding("command_and_file_activity", activity_status, activity_detail),
        CoverageFinding("multi_agent_lifecycle", lifecycle_status, lifecycle_detail),
        CoverageFinding("multi_agent_readable_task_text", readable_status, readable_detail),
        CoverageFinding(
            "offered_tool_catalog",
            "available" if exec_facts["offered_tools"] else "unavailable",
            (
                "The event stream exposed a tool catalog and the adapter retained name hashes."
                if exec_facts["offered_tools"]
                else (
                    "The event stream did not expose the offered tool catalog "
                    "(see openai/codex#31088)."
                )
            ),
        ),
        CoverageFinding(
            "offered_skill_catalog",
            "available" if exec_facts["offered_skills"] else "unavailable",
            (
                "The event stream exposed a skill catalog and the adapter retained name hashes."
                if exec_facts["offered_skills"]
                else (
                    "The event stream did not expose the offered skill catalog "
                    "(see openai/codex#31088)."
                )
            ),
        ),
        CoverageFinding(
            "permissions_profile",
            "available" if exec_facts["permissions_profile"] else "unavailable",
            (
                "The event stream exposed a permissions profile and the adapter retained its hash."
                if exec_facts["permissions_profile"]
                else "The event stream did not expose an effective permissions profile."
            ),
        ),
    )
