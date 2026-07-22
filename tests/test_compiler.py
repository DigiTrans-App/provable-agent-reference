from __future__ import annotations

import unittest

from helpers import bundle, context, draft, evidence

from provable_agent_reference import TrustedCompiler
from provable_agent_reference.errors import CompilationError, ContractError


class CompilerTests(unittest.TestCase):
    def test_compiles_semantic_draft_into_canonical_candidate(self) -> None:
        run_context = context()
        candidate = TrustedCompiler().compile(
            context=run_context,
            draft=draft(),
            evidence_bundle=bundle(run_context),
        )
        self.assertTrue(candidate.verify_hash())
        self.assertEqual(candidate.run_context, run_context)
        self.assertEqual(candidate.evidence.evidence_id, "evidence_test_001")
        self.assertEqual(candidate.compiler_version, "0.1.0")

    def test_compilation_is_deterministic(self) -> None:
        run_context = context()
        evidence_bundle = bundle(run_context)
        first = TrustedCompiler().compile(
            context=run_context,
            draft=draft(),
            evidence_bundle=evidence_bundle,
        )
        second = TrustedCompiler().compile(
            context=run_context,
            draft=draft(),
            evidence_bundle=evidence_bundle,
        )
        self.assertEqual(first, second)

    def test_unknown_evidence_fails_compilation(self) -> None:
        run_context = context()
        with self.assertRaises(ContractError):
            TrustedCompiler().compile(
                context=run_context,
                draft=draft("evidence_unknown"),
                evidence_bundle=bundle(run_context),
            )

    def test_cross_scope_bundle_fails_compilation(self) -> None:
        run_context = context()
        other_context = context(tenant_id="tenant_other")
        with self.assertRaises(CompilationError):
            TrustedCompiler().compile(
                context=run_context,
                draft=draft(),
                evidence_bundle=bundle(other_context, evidence(other_context)),
            )

    def test_classification_ceiling_is_enforced(self) -> None:
        run_context = context(classification="internal")
        record = evidence(run_context, classification="restricted")
        with self.assertRaises(CompilationError):
            TrustedCompiler().compile(
                context=run_context,
                draft=draft(),
                evidence_bundle=bundle(run_context, record),
            )


if __name__ == "__main__":
    unittest.main()
