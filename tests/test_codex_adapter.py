from __future__ import annotations

import json
import unittest
from pathlib import Path

from provable_agent_reference.adapters import (
    AdapterContext,
    AdapterValidationError,
    CodexEvidenceAdapter,
    CoverageFinding,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "codex_evidence_adapter" / "fixtures"


class CodexEvidenceAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = CodexEvidenceAdapter()
        self.context = AdapterContext(
            tenant_id="tenant_demo",
            case_id="case_demo",
            run_id="run_codex_demo",
            created_at="2026-07-30T00:00:00Z",
            classification="internal",
        )
        self.execution_jsonl = (FIXTURES / "codex_exec.synthetic.jsonl").read_text(
            encoding="utf-8"
        )
        self.telemetry_jsonl = (FIXTURES / "codex_otel.synthetic.jsonl").read_text(
            encoding="utf-8"
        )

    def build(self, **changes: str):
        values = {
            "context": self.context,
            "execution_jsonl": self.execution_jsonl,
            "telemetry_jsonl": self.telemetry_jsonl,
        }
        values.update(changes)
        return self.adapter.build_evidence(**values)  # type: ignore[arg-type]

    def test_builds_deterministic_privacy_minimized_evidence(self) -> None:
        first = self.build()
        second = self.build()

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.accepted_event_count, 9)
        self.assertEqual(first.ignored_event_count, 1)
        self.assertEqual(len(first.evidence_bundle.records), 3)
        self.assertEqual(
            first.evidence_bundle.bundle_hash,
            first.evidence_bundle.compute_hash(),
        )

        serialized = json.dumps(first.to_dict(), sort_keys=True)
        for raw_value in (
            "python -m unittest discover -s tests -v",
            "Ran 24 tests",
            "src/synthetic_example.py",
            "review_evidence",
            "The synthetic validation completed.",
            "Inspect the synthetic repository",
        ):
            self.assertNotIn(raw_value, serialized)

        coverage = {item.capability: item.status for item in first.coverage}
        self.assertEqual(coverage["exec_event_stream"], "available")
        self.assertEqual(coverage["command_and_file_activity"], "available")
        self.assertEqual(coverage["multi_agent_lifecycle"], "available")
        self.assertEqual(coverage["multi_agent_readable_task_text"], "unavailable")
        self.assertEqual(coverage["offered_tool_catalog"], "unavailable")
        self.assertEqual(coverage["offered_skill_catalog"], "unavailable")
        self.assertEqual(coverage["permissions_profile"], "unavailable")

    def test_fixture_matches_published_compatibility_vectors(self) -> None:
        result = self.build()
        expected_dir = ROOT / "examples" / "codex_evidence_adapter" / "expected"
        expected_bundle = json.loads(
            (expected_dir / "codex_evidence_bundle.expected.json").read_text(encoding="utf-8")
        )
        expected_coverage = json.loads(
            (expected_dir / "codex_coverage.expected.json").read_text(encoding="utf-8")
        )
        self.assertEqual(result.evidence_bundle.to_dict(), expected_bundle)
        self.assertEqual([item.to_dict() for item in result.coverage], expected_coverage)

    def test_discards_unrecognized_numeric_usage_fields(self) -> None:
        baseline = self.build(
            execution_jsonl='{"type":"turn.completed","usage":{"input_tokens":1}}\n',
            telemetry_jsonl="",
        )
        extra = self.build(
            execution_jsonl=(
                '{"type":"turn.completed","usage":'
                '{"input_tokens":1,"employee_id":123456}}\n'
            ),
            telemetry_jsonl="",
        )
        baseline_record = next(
            record
            for record in baseline.evidence_bundle.records
            if record.evidence_id == "evidence_codex_exec"
        )
        extra_record = next(
            record
            for record in extra.evidence_bundle.records
            if record.evidence_id == "evidence_codex_exec"
        )
        self.assertEqual(baseline_record.content_hash, extra_record.content_hash)

    def test_rejects_invalid_coverage_status_at_runtime(self) -> None:
        with self.assertRaisesRegex(AdapterValidationError, "coverage status"):
            CoverageFinding(
                capability="runtime_test",
                status="unknown",  # type: ignore[arg-type]
                detail="Synthetic invalid status.",
            )

    def test_rejects_malformed_json(self) -> None:
        with self.assertRaisesRegex(AdapterValidationError, "not valid JSON"):
            self.build(execution_jsonl='{"type":"thread.started"')

    def test_rejects_stream_without_supported_events(self) -> None:
        with self.assertRaisesRegex(AdapterValidationError, "no supported Codex events"):
            self.build(
                execution_jsonl='{"type":"unknown"}\n',
                telemetry_jsonl="",
            )

    def test_rejects_duplicate_terminal_item_event(self) -> None:
        line = (
            '{"type":"item.completed","item":{"id":"item_001",'
            '"type":"agent_message","text":"synthetic"}}\n'
        )
        with self.assertRaisesRegex(AdapterValidationError, "duplicate item.completed"):
            self.build(execution_jsonl=line + line, telemetry_jsonl="")

    def test_rejects_receive_without_send(self) -> None:
        telemetry = (
            '{"event.name":"codex.agent_communication",'
            '"communication_id":"communication_orphan",'
            '"state":"receive"}\n'
        )
        with self.assertRaisesRegex(AdapterValidationError, "no corresponding send"):
            self.build(telemetry_jsonl=telemetry)

    def test_rejects_credential_like_material_before_hashing(self) -> None:
        token = "sk-proj-" + "abcdefghijklmnopqrstuvwxyz123456"
        execution = json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "id": "item_secret",
                    "type": "agent_message",
                    "text": token,
                },
            }
        )
        with self.assertRaisesRegex(AdapterValidationError, "credential-like"):
            self.build(execution_jsonl=execution, telemetry_jsonl="")

    def test_reports_unmatched_send_as_partial_without_inventing_delivery(self) -> None:
        telemetry = (
            '{"event.name":"codex.agent_communication",'
            '"communication_id":"communication_pending",'
            '"kind":"message","state":"send",'
            '"sender_thread_id":"thread_a","receiver_thread_id":"thread_b",'
            '"content":"Synthetic pending message."}\n'
        )
        result = self.build(telemetry_jsonl=telemetry)
        coverage = {item.capability: item.status for item in result.coverage}
        self.assertEqual(coverage["multi_agent_lifecycle"], "partial")
        telemetry_record = next(
            record
            for record in result.evidence_bundle.records
            if record.evidence_id == "evidence_codex_telemetry"
        )
        self.assertIn("1 unmatched sends", telemetry_record.summary)

    def test_future_explicit_catalog_and_plaintext_audit_signals_are_supported(self) -> None:
        execution = "\n".join(
            (
                '{"type":"thread.started","thread_id":"thread_catalog"}',
                '{"type":"session.catalog","tools":["shell",{"name":"mcp__demo"}],'
                '"skills":["review"],"permissions_profile":"sandbox"}',
            )
        )
        telemetry = "\n".join(
            (
                '{"event.name":"codex.agent_communication",'
                '"communication_id":"communication_plaintext",'
                '"kind":"spawn","state":"send",'
                '"sender_thread_id":"thread_catalog",'
                '"receiver_thread_id":"thread_child",'
                '"content":"Synthetic readable task.",'
                '"content_format":"plaintext_audit"}',
                '{"event.name":"codex.agent_communication",'
                '"communication_id":"communication_plaintext","state":"receive"}',
            )
        )
        result = self.build(execution_jsonl=execution, telemetry_jsonl=telemetry)
        coverage = {item.capability: item.status for item in result.coverage}
        self.assertEqual(coverage["offered_tool_catalog"], "available")
        self.assertEqual(coverage["offered_skill_catalog"], "available")
        self.assertEqual(coverage["permissions_profile"], "available")
        self.assertEqual(coverage["multi_agent_readable_task_text"], "available")
        self.assertNotIn("Synthetic readable task.", json.dumps(result.to_dict()))


if __name__ == "__main__":
    unittest.main()
