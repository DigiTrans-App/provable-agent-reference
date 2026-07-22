from __future__ import annotations

import unittest
from dataclasses import replace

from provable_agent_reference import DeterministicVerifier, TrustedCompiler

from helpers import bundle, context, draft


class VerificationTests(unittest.TestCase):
    def test_happy_candidate_passes(self) -> None:
        run_context = context()
        evidence_bundle = bundle(run_context)
        candidate = TrustedCompiler().compile(
            context=run_context,
            draft=draft(),
            evidence_bundle=evidence_bundle,
        )
        result = DeterministicVerifier().verify(
            candidate=candidate,
            evidence_bundle=evidence_bundle,
        )
        self.assertEqual(result.status, "pass")
        self.assertTrue(result.verify_hash())

    def test_sensitive_unredacted_output_fails(self) -> None:
        run_context = context()
        evidence_bundle = bundle(run_context)
        candidate = TrustedCompiler().compile(
            context=run_context,
            draft=draft(content_categories=("secret",), redacted=False),
            evidence_bundle=evidence_bundle,
        )
        result = DeterministicVerifier().verify(
            candidate=candidate,
            evidence_bundle=evidence_bundle,
        )
        self.assertEqual(result.status, "fail")
        self.assertIn(
            "DISCLOSURE_SAFE",
            [finding.code for finding in result.findings if not finding.passed],
        )

    def test_candidate_tampering_is_detected(self) -> None:
        run_context = context()
        evidence_bundle = bundle(run_context)
        candidate = TrustedCompiler().compile(
            context=run_context,
            draft=draft(),
            evidence_bundle=evidence_bundle,
        )
        tampered = replace(candidate, assurance_statement="Substituted output.")
        result = DeterministicVerifier().verify(
            candidate=tampered,
            evidence_bundle=evidence_bundle,
        )
        self.assertEqual(result.status, "fail")


if __name__ == "__main__":
    unittest.main()
