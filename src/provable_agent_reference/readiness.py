from __future__ import annotations

import platform
import statistics
import time
from typing import Any

from .canonical import canonical_json, sha256_uri

_BENCHMARK_RECORD = {
    "case_id": "case_synthetic_benchmark",
    "evidence_refs": ["sha256:" + "a" * 64, "sha256:" + "b" * 64],
    "limitations": ["Synthetic deterministic benchmark input."],
    "tenant_id": "tenant_synthetic",
}


def canonicalization_baseline(*, iterations: int = 5_000, rounds: int = 5) -> dict[str, Any]:
    """Measure a fixed local canonicalization workload without claiming a service SLO."""

    if iterations < 100 or rounds < 3:
        raise ValueError("benchmark requires at least 100 iterations and three rounds")
    expected = canonical_json(_BENCHMARK_RECORD)
    samples: list[float] = []
    for _ in range(rounds):
        started = time.perf_counter_ns()
        for _ in range(iterations):
            if canonical_json(_BENCHMARK_RECORD) != expected:
                raise RuntimeError("canonical benchmark output changed")
        elapsed = time.perf_counter_ns() - started
        samples.append(round(iterations / (elapsed / 1_000_000_000), 2))
    return {
        "benchmark": "canonical-json-fixed-record-v1",
        "input_hash": sha256_uri(_BENCHMARK_RECORD),
        "iterations_per_round": iterations,
        "rounds": rounds,
        "operations_per_second": samples,
        "median_operations_per_second": round(statistics.median(samples), 2),
        "interpretation": "Local comparison baseline only; not a service SLO or capacity claim.",
    }


def phase1_conformance_report(
    *,
    source_revision: str,
    test_count: int,
    benchmark: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Build the self-issued Phase 1 report using the draft conformance contract."""

    if len(source_revision) != 40 or any(c not in "0123456789abcdef" for c in source_revision):
        raise ValueError("source_revision must be a lowercase 40-character commit SHA")
    if test_count < 100:
        raise ValueError("Phase 1 requires at least 100 reproducible tests")
    report: dict[str, Any] = {
        "$schema": "https://digitrans.app/schemas/provable-agent-reference/agentic-conformance-report.schema.json",
        "schema_version": "0.1-draft",
        "generated_at": generated_at,
        "claim_scope": "core_profiles_only",
        "core_profile_status": "pass",
        "self_issued": True,
        "implementation": {
            "name": "synthetic-phase1-reference",
            "version": "0.1-draft",
            "source_revision": source_revision,
            "language": "python",
        },
        "protocol_version": "0.3.0-candidate.1",
        "vector_revision": "agentic-vectors:0.1-draft",
        "core_profiles": [
            "par.core.v1",
            "par.evidence-bound.v1",
            "par.governed.v1",
            "par.exact-use.v1",
            "par.reconstructable.v1",
        ],
        "capability_results": [
            {
                "capability_id": "par.capability.activity-bound.0.1-draft",
                "status": "pass",
                "dependencies": ["par.reconstructable.v1"],
                "checks": [f"python_test_count:{test_count}"],
                "limitations": ["Self-issued synthetic activity-chain result."],
            },
            {
                "capability_id": "par.capability.authenticated-records.0.1-draft",
                "status": "not_tested",
                "dependencies": ["par.capability.activity-bound.0.1-draft"],
                "checks": ["development_dsse_interoperability_only"],
                "limitations": ["The public development key does not authenticate a producer."],
            },
            {
                "capability_id": "par.capability.receipted-effect.0.1-draft",
                "status": "pass",
                "dependencies": ["par.exact-use.v1"],
                "checks": ["synthetic_receipt_and_unknown_outcome_reconciliation"],
                "limitations": ["No external provider or production effect was exercised."],
            },
            {
                "capability_id": "par.capability.private-memory.0.1-draft",
                "status": "pass",
                "dependencies": ["par.capability.activity-bound.0.1-draft"],
                "checks": ["minimized_synthetic_memory_adapter"],
                "limitations": ["Ordinary digests provide binding, not anonymity or secrecy."],
            },
            {
                "capability_id": "par.capability.durable-lifecycle.0.1-draft",
                "status": "not_tested",
                "dependencies": ["par.reconstructable.v1"],
                "checks": ["postgresql_integration_exercised_in_separate_ci_gate"],
                "limitations": ["This local report does not independently attest PostgreSQL durability."],
            },
        ],
        "storage_assurance": {
            "level": "S0",
            "status": "incomplete",
            "self_issued": True,
            "tested_at": generated_at,
            "limitations": [
                "Logical local controls only; administrators remain inside the trust boundary.",
                "Backup and restore require the separately documented PostgreSQL exercise.",
            ],
        },
        "environment": {
            "os": platform.system().lower() or "unknown",
            "runtime": platform.python_version(),
            "architecture": platform.machine() or "unknown",
        },
        "limitations": [
            "Self-issued synthetic Phase 1 result; not independent validation or certification.",
            "Development identities and public test keys only.",
            "No customer data, production destination, or production-effect authorization.",
            benchmark["interpretation"],
        ],
    }
    report["report_hash"] = sha256_uri(report)
    return report


def verify_phase1_conformance_report(report: dict[str, Any]) -> bool:
    payload = dict(report)
    claimed = payload.pop("report_hash", None)
    return isinstance(claimed, str) and claimed == sha256_uri(payload)
