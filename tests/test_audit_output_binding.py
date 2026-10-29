from __future__ import annotations

import unittest
from dataclasses import replace

from helpers import bundle, context, draft

from provable_agent_reference import (
    ProvableAgentPipeline,
    authorize_exact_use,
    build_audit_manifest,
    verify_audit_manifest,
)
from provable_agent_reference.canonical import sha256_uri

OUTPUT_MISMATCH = "authorization_output_mismatch"


def run_pipeline():
    run_context = context()
    return ProvableAgentPipeline().run(
        context=run_context,
        draft=draft(limitations=("First synthetic limitation.", "Second synthetic limitation.")),
        evidence_bundle=bundle(run_context),
        approver_id="human_reviewer",
    )


def approved_output(result) -> dict[str, object]:
    return {
        "assurance_statement": result.candidate.assurance_statement,
        "limitations": list(result.candidate.limitations),
    }


def rehash(authorization):
    return replace(authorization, record_hash=sha256_uri(authorization.payload()))


def audit(result, authorization):
    manifest = build_audit_manifest(
        candidate=result.candidate,
        verification=result.verification,
        approval=result.approval,
        authorization=authorization,
    )
    return manifest, verify_audit_manifest(
        manifest=manifest,
        candidate=result.candidate,
        verification=result.verification,
        approval=result.approval,
        authorization=authorization,
    )


class AuditOutputBindingTests(unittest.TestCase):
    def test_valid_records_remain_accepted(self) -> None:
        result = run_pipeline()

        self.assertTrue(result.authorization.authorized)
        self.assertEqual(result.authorization.output_hash, sha256_uri(approved_output(result)))
        self.assertEqual((result.audit_valid, result.audit_errors), (True, ()))
        _, outcome = audit(result, result.authorization)
        self.assertEqual(outcome, (True, ()))

    def test_rehashed_output_substitution_is_rejected(self) -> None:
        result = run_pipeline()
        approved = approved_output(result)
        limitations = list(approved["limitations"])  # type: ignore[arg-type]
        substitutions = {
            "statement_changed": {**approved, "assurance_statement": "Substituted statement."},
            "limitation_changed": {**approved, "limitations": ["Substituted.", *limitations[1:]]},
            "limitations_reordered": {**approved, "limitations": limitations[::-1]},
            "field_added": {**approved, "extra": "Substituted field."},
        }
        for label, output in substitutions.items():
            with self.subTest(substitution=label):
                forged = rehash(replace(result.authorization, output_hash=sha256_uri(output)))
                manifest, (valid, errors) = audit(result, forged)

                self.assertTrue(forged.authorized)
                self.assertTrue(forged.verify_hash())
                self.assertTrue(manifest.verify_hash())
                self.assertFalse(valid)
                self.assertEqual(errors, (OUTPUT_MISMATCH,))

    def test_legitimate_denied_records_remain_auditable(self) -> None:
        result = run_pipeline()
        context_ = result.candidate.run_context
        approved = approved_output(result)
        requests = {
            "output": (context_.purpose, context_.audience, {**approved, "assurance_statement": "Other."}),
            "purpose": (context_.purpose + " [other]", context_.audience, approved),
            "audience": (context_.purpose, context_.audience + " [other]", approved),
        }
        for label, (purpose, audience, output) in requests.items():
            with self.subTest(denied_for=label):
                denied = authorize_exact_use(
                    candidate=result.candidate,
                    approval=result.approval,
                    purpose=purpose,
                    audience=audience,
                    output=output,
                )
                _, outcome = audit(result, denied)

                self.assertFalse(denied.authorized)
                self.assertEqual(denied.reason, "EXACT_USE_MISMATCH")
                self.assertEqual(outcome, (True, ()))

    def test_denied_record_rewritten_as_authorized_is_rejected(self) -> None:
        result = run_pipeline()
        context_ = result.candidate.run_context
        denied = authorize_exact_use(
            candidate=result.candidate,
            approval=result.approval,
            purpose=context_.purpose,
            audience=context_.audience,
            output={**approved_output(result), "assurance_statement": "Other."},
        )
        forged = rehash(replace(denied, authorized=True, reason="EXACT_USE_AUTHORIZED"))
        _, (valid, errors) = audit(result, forged)

        self.assertFalse(valid)
        self.assertEqual(errors, (OUTPUT_MISMATCH,))


if __name__ == "__main__":
    unittest.main()
