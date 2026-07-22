from __future__ import annotations

import unittest

from provable_agent_reference import EvidenceBundle, SemanticDraft
from provable_agent_reference.errors import ContractError

from helpers import context, evidence


class ContractTests(unittest.TestCase):
    def test_semantic_draft_accepts_bounded_content(self) -> None:
        value = SemanticDraft(
            claim_text="Claim.",
            selected_evidence_id="evidence_001",
            limitations=("Synthetic only.",),
            assurance_statement="Statement.",
        )
        self.assertEqual(value.selected_evidence_id, "evidence_001")

    def test_semantic_draft_rejects_duplicate_limitations(self) -> None:
        with self.assertRaises(ContractError):
            SemanticDraft(
                claim_text="Claim.",
                selected_evidence_id="evidence_001",
                limitations=("Same.", "Same."),
                assurance_statement="Statement.",
            )

    def test_semantic_draft_rejects_authority_fields(self) -> None:
        with self.assertRaises(TypeError):
            SemanticDraft(
                claim_text="Claim.",
                selected_evidence_id="evidence_001",
                limitations=("Synthetic only.",),
                assurance_statement="Statement.",
                tenant_id="tenant_forbidden",  # type: ignore[call-arg]
            )

    def test_evidence_bundle_hash_is_deterministic(self) -> None:
        run_context = context()
        record = evidence(run_context)
        first = EvidenceBundle.create(
            bundle_id="bundle_001",
            tenant_id=run_context.tenant_id,
            case_id=run_context.case_id,
            records=[record],
        )
        second = EvidenceBundle.create(
            bundle_id="bundle_001",
            tenant_id=run_context.tenant_id,
            case_id=run_context.case_id,
            records=[record],
        )
        self.assertEqual(first.bundle_hash, second.bundle_hash)

    def test_bundle_rejects_cross_scope_evidence(self) -> None:
        run_context = context()
        record = evidence(run_context, tenant_id="tenant_other")
        with self.assertRaises(ContractError):
            EvidenceBundle.create(
                bundle_id="bundle_001",
                tenant_id=run_context.tenant_id,
                case_id=run_context.case_id,
                records=[record],
            )


if __name__ == "__main__":
    unittest.main()
