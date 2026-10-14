from __future__ import annotations

import unittest

from provable_agent_reference.readiness import (
    canonicalization_baseline,
    phase1_conformance_report,
    verify_phase1_conformance_report,
)


class ReadinessTests(unittest.TestCase):
    def test_fixed_benchmark_is_bound_and_measured(self) -> None:
        result = canonicalization_baseline(iterations=100, rounds=3)
        self.assertEqual(result["benchmark"], "canonical-json-fixed-record-v1")
        self.assertEqual(len(result["operations_per_second"]), 3)
        self.assertGreater(result["median_operations_per_second"], 0)

    def test_report_is_self_issued_bounded_and_hash_verified(self) -> None:
        benchmark = canonicalization_baseline(iterations=100, rounds=3)
        report = phase1_conformance_report(
            source_revision="a" * 40,
            test_count=100,
            benchmark=benchmark,
            generated_at="2026-09-05T20:00:00Z",
        )
        self.assertEqual(report["claim_scope"], "core_profiles_only")
        self.assertTrue(report["self_issued"])
        self.assertEqual(report["storage_assurance"]["level"], "S0")
        self.assertEqual(report["storage_assurance"]["status"], "incomplete")
        self.assertTrue(verify_phase1_conformance_report(report))
        report["core_profile_status"] = "fail"
        self.assertFalse(verify_phase1_conformance_report(report))

    def test_report_rejects_short_revision_and_fewer_than_100_tests(self) -> None:
        benchmark = canonicalization_baseline(iterations=100, rounds=3)
        with self.assertRaises(ValueError):
            phase1_conformance_report(
                source_revision="short",
                test_count=100,
                benchmark=benchmark,
                generated_at="2026-09-05T20:00:00Z",
            )
        with self.assertRaises(ValueError):
            phase1_conformance_report(
                source_revision="a" * 40,
                test_count=99,
                benchmark=benchmark,
                generated_at="2026-09-05T20:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
