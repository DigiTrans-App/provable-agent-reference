from __future__ import annotations

import unittest

from helpers import bundle, context, draft

from provable_agent_reference import (
    DeterministicVerifier,
    TrustedCompiler,
    authorize_exact_use,
    record_approval,
)
from provable_agent_reference.errors import ApprovalError


class ApprovalAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = context()
        self.bundle = bundle(self.context)
        self.candidate = TrustedCompiler().compile(
            context=self.context,
            draft=draft(),
            evidence_bundle=self.bundle,
        )
        self.verification = DeterministicVerifier().verify(
            candidate=self.candidate,
            evidence_bundle=self.bundle,
        )

    def test_approval_and_exact_use_authorization(self) -> None:
        approval = record_approval(
            candidate=self.candidate,
            verification=self.verification,
            approver_id="human_reviewer",
        )
        authorization = authorize_exact_use(
            candidate=self.candidate,
            approval=approval,
            purpose=self.context.purpose,
            audience=self.context.audience,
            output={
                "assurance_statement": self.candidate.assurance_statement,
                "limitations": list(self.candidate.limitations),
            },
        )
        self.assertTrue(authorization.authorized)
        self.assertTrue(authorization.verify_hash())

    def test_output_substitution_is_not_authorized(self) -> None:
        approval = record_approval(
            candidate=self.candidate,
            verification=self.verification,
            approver_id="human_reviewer",
        )
        authorization = authorize_exact_use(
            candidate=self.candidate,
            approval=approval,
            purpose=self.context.purpose,
            audience=self.context.audience,
            output={"assurance_statement": "Different.", "limitations": []},
        )
        self.assertFalse(authorization.authorized)
        self.assertEqual(authorization.reason, "EXACT_USE_MISMATCH")

    def test_failed_verification_cannot_be_approved(self) -> None:
        failed_candidate = TrustedCompiler().compile(
            context=self.context,
            draft=draft(content_categories=("secret",), redacted=False),
            evidence_bundle=self.bundle,
        )
        failed_verification = DeterministicVerifier().verify(
            candidate=failed_candidate,
            evidence_bundle=self.bundle,
        )
        with self.assertRaises(ApprovalError):
            record_approval(
                candidate=failed_candidate,
                verification=failed_verification,
                approver_id="human_reviewer",
            )


if __name__ == "__main__":
    unittest.main()
