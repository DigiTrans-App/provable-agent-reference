from __future__ import annotations

import unittest

from provable_agent_reference.authorization import authorize_exact_use
from provable_agent_reference.demo import run_demo
from provable_agent_reference.synthetic_effects import (
    SYNTHETIC_TARGET,
    AuthorizationLifecycle,
    SyntheticEffectError,
    SyntheticEffectExecutor,
)


class SyntheticEffectTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = run_demo()
        self.context = self.pipeline.candidate.run_context
        self.authorization = self.pipeline.authorization
        self.output = {
            "assurance_statement": self.pipeline.candidate.assurance_statement,
            "limitations": list(self.pipeline.candidate.limitations),
        }

    def test_acknowledgement_is_not_upgraded_to_effect_success(self):
        receipt = SyntheticEffectExecutor().execute(
            context=self.context,
            authorization=self.authorization,
            output=self.output,
            target_ref=SYNTHETIC_TARGET,
            outcome="acknowledged",
        )
        self.assertEqual(receipt["submission_status"], "acknowledged")
        self.assertEqual(receipt["effect_status"], "not_observed")
        self.assertTrue(receipt["reconciliation_required"])
        self.assertEqual(receipt["provider_evidence"]["effect_semantics"], "acknowledgement_only")

    def test_unknown_outcome_reconciles_without_unsafe_retry(self):
        executor = SyntheticEffectExecutor()
        receipt = executor.execute(
            context=self.context,
            authorization=self.authorization,
            output=self.output,
            target_ref=SYNTHETIC_TARGET,
            outcome="unknown",
        )
        self.assertEqual(receipt["effect_status"], "unknown")
        reconciliation = executor.reconcile(
            receipt, observed_effect=True, reconciled_at=self.context.created_at
        )
        self.assertEqual(reconciliation["effect_status"], "succeeded")
        self.assertEqual(reconciliation["receipt_hash"], receipt["record_hash"])

    def test_external_target_and_mutated_output_fail_closed(self):
        executor = SyntheticEffectExecutor()
        with self.assertRaisesRegex(SyntheticEffectError, "synthetic target"):
            executor.execute(
                context=self.context,
                authorization=self.authorization,
                output=self.output,
                target_ref="https://example.com/live",
                outcome="observed",
            )
        with self.assertRaisesRegex(SyntheticEffectError, "differs"):
            executor.execute(
                context=self.context,
                authorization=self.authorization,
                output={**self.output, "unexpected": True},
                target_ref=SYNTHETIC_TARGET,
                outcome="observed",
            )

    def test_authorization_is_single_use_and_lifecycle_is_explicit(self):
        lifecycle = AuthorizationLifecycle()
        consumed = lifecycle.transition(
            self.authorization, "consumed", effective_at=self.context.created_at
        )
        self.assertEqual(consumed["status"], "consumed")
        with self.assertRaisesRegex(SyntheticEffectError, "no longer consumable"):
            lifecycle.transition(
                self.authorization, "consumed", effective_at=self.context.created_at
            )
        superseded = AuthorizationLifecycle().transition(
            self.authorization,
            "superseded",
            effective_at=self.context.created_at,
            successor_ref="authorization_synthetic_successor",
        )
        self.assertEqual(superseded["successor_ref"], "authorization_synthetic_successor")

    def test_denied_authorization_cannot_be_consumed(self):
        denied = authorize_exact_use(
            candidate=self.pipeline.candidate,
            approval=self.pipeline.approval,
            purpose="different purpose",
            audience=self.context.audience,
            output=self.output,
        )
        with self.assertRaisesRegex(SyntheticEffectError, "invalid or denied"):
            AuthorizationLifecycle().transition(
                denied, "revoked", effective_at=self.context.created_at
            )


if __name__ == "__main__":
    unittest.main()
