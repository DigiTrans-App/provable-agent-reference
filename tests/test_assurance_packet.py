from __future__ import annotations

import json
import unittest
from dataclasses import replace
from pathlib import Path

from helpers import bundle, context, draft, evidence

from provable_agent_reference import (
    ASSURANCE_PACKET_PROTOCOL_VERSION,
    SUPPORTED_ASSURANCE_PROFILES,
    EvidenceBundle,
    ProvableAgentPipeline,
    build_assurance_packet,
    build_audit_manifest,
    load_assurance_packet,
    verify_assurance_packet,
)
from provable_agent_reference.canonical import sha256_uri
from provable_agent_reference.errors import ContractError


class AssurancePacketTests(unittest.TestCase):
    def build_packet(self):
        run_context = context()
        evidence_bundle = bundle(run_context)
        result = ProvableAgentPipeline().run(
            context=run_context,
            draft=draft(),
            evidence_bundle=evidence_bundle,
            approver_id="human_reviewer",
        )
        return build_assurance_packet(
            evidence_bundle=evidence_bundle,
            result=result,
            limitations=(
                "Digest bindings do not authenticate the producer or prove source completeness.",
            ),
        )

    def rebind_approval(self, packet, **changes):
        approval_provisional = replace(
            packet.approval,
            **changes,
            record_hash="sha256:" + "0" * 64,
        )
        approval = replace(
            approval_provisional,
            record_hash=sha256_uri(approval_provisional.payload()),
        )
        manifest = build_audit_manifest(
            candidate=packet.candidate,
            verification=packet.verification,
            approval=approval,
            authorization=packet.authorization,
        )
        identity_payload = {
            "protocol_version": ASSURANCE_PACKET_PROTOCOL_VERSION,
            "candidate_hash": packet.candidate.candidate_hash,
            "manifest_hash": manifest.manifest_hash,
            "evidence_bundle_hash": packet.evidence_bundle.bundle_hash,
        }
        provisional = replace(
            packet,
            approval=approval,
            audit_manifest=manifest,
            packet_id="packet_"
            + sha256_uri(identity_payload).split(":", 1)[1][:24],
            packet_hash="sha256:" + "0" * 64,
        )
        return replace(provisional, packet_hash=sha256_uri(provisional.payload()))

    def test_packet_is_deterministic_and_verifiable(self) -> None:
        first = self.build_packet()
        second = self.build_packet()

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.claimed_profiles, SUPPORTED_ASSURANCE_PROFILES)
        self.assertEqual(verify_assurance_packet(first), (True, ()))

    def test_published_example_matches_reference_builder(self) -> None:
        expected = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "examples"
                / "records"
                / "assurance-packet.example.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(self.build_packet().to_dict(), expected)
        self.assertEqual(load_assurance_packet(expected).to_dict(), expected)

    def test_loader_rejects_unexpected_fields(self) -> None:
        value = self.build_packet().to_dict()
        value["untrusted_extension"] = "must not be ignored"

        with self.assertRaisesRegex(ContractError, "unexpected=untrusted_extension"):
            load_assurance_packet(value)

    def test_authorized_output_mutation_is_detected(self) -> None:
        packet = self.build_packet()
        provisional = replace(
            packet,
            authorized_output={
                **packet.authorized_output,
                "assurance_statement": "Substituted output.",
            },
        )
        mutated = replace(provisional, packet_hash=sha256_uri(provisional.payload()))

        valid, errors = verify_assurance_packet(mutated)

        self.assertFalse(valid)
        self.assertNotIn("packet_hash_invalid", errors)
        self.assertIn("authorized_output_candidate_mismatch", errors)
        self.assertIn("authorized_output_hash_mismatch", errors)

    def test_evidence_bundle_substitution_is_detected(self) -> None:
        packet = self.build_packet()
        other_record = evidence(
            packet.candidate.run_context,
            evidence_id="evidence_other",
            text="Different synthetic evidence.",
        )
        other_bundle = EvidenceBundle.create(
            bundle_id=packet.evidence_bundle.bundle_id,
            tenant_id=packet.evidence_bundle.tenant_id,
            case_id=packet.evidence_bundle.case_id,
            records=[other_record],
        )
        provisional = replace(packet, evidence_bundle=other_bundle)
        substituted = replace(provisional, packet_hash=sha256_uri(provisional.payload()))

        valid, errors = verify_assurance_packet(substituted)

        self.assertFalse(valid)
        self.assertNotIn("packet_hash_invalid", errors)
        self.assertIn("packet_id_invalid", errors)
        self.assertIn("candidate_bundle_binding_mismatch", errors)
        self.assertIn("candidate_evidence_missing", errors)

    def test_non_cumulative_profile_claim_is_rejected(self) -> None:
        packet = self.build_packet()
        invalid = replace(
            packet,
            claimed_profiles=("par.core.v1", "par.exact-use.v1"),
        )

        valid, errors = verify_assurance_packet(invalid)

        self.assertFalse(valid)
        self.assertIn("profile_claim_not_cumulative", errors)

    def test_non_canonicalizable_output_fails_closed(self) -> None:
        packet = self.build_packet()
        invalid = replace(
            packet,
            authorized_output={
                **packet.authorized_output,
                "unexpected": float("nan"),
            },
        )

        valid, errors = verify_assurance_packet(invalid)

        self.assertFalse(valid)
        self.assertIn("packet_payload_not_canonicalizable", errors)
        self.assertIn("authorized_output_not_canonicalizable", errors)

    def test_packet_limitations_respect_schema_bound(self) -> None:
        packet = self.build_packet()
        limitations = tuple(f"Synthetic limitation {index}." for index in range(21))

        with self.assertRaisesRegex(ContractError, "between 1 and 20"):
            build_assurance_packet(
                evidence_bundle=packet.evidence_bundle,
                result=ProvableAgentPipeline().run(
                    context=packet.candidate.run_context,
                    draft=draft(),
                    evidence_bundle=packet.evidence_bundle,
                    approver_id="human_reviewer",
                ),
                limitations=limitations,
            )

        provisional = replace(packet, limitations=limitations)
        invalid = replace(provisional, packet_hash=sha256_uri(provisional.payload()))
        valid, errors = verify_assurance_packet(invalid)

        self.assertFalse(valid)
        self.assertIn("packet_limitations_invalid", errors)

    def test_semantically_false_rehashed_verification_is_detected(self) -> None:
        packet = self.build_packet()
        candidate_provisional = replace(
            packet.candidate,
            content_categories=("secret",),
            redacted=False,
            candidate_hash="sha256:" + "0" * 64,
        )
        candidate = replace(
            candidate_provisional,
            candidate_hash=sha256_uri(candidate_provisional.payload()),
        )
        verification_provisional = replace(
            packet.verification,
            candidate_hash=candidate.candidate_hash,
            result_hash="sha256:" + "0" * 64,
        )
        verification = replace(
            verification_provisional,
            result_hash=sha256_uri(verification_provisional.payload()),
        )
        approval_provisional = replace(
            packet.approval,
            candidate_hash=candidate.candidate_hash,
            verification_result_hash=verification.result_hash,
            record_hash="sha256:" + "0" * 64,
        )
        approval = replace(
            approval_provisional,
            record_hash=sha256_uri(approval_provisional.payload()),
        )
        authorization_provisional = replace(
            packet.authorization,
            candidate_hash=candidate.candidate_hash,
            record_hash="sha256:" + "0" * 64,
        )
        authorization = replace(
            authorization_provisional,
            record_hash=sha256_uri(authorization_provisional.payload()),
        )
        manifest = build_audit_manifest(
            candidate=candidate,
            verification=verification,
            approval=approval,
            authorization=authorization,
        )
        identity_payload = {
            "protocol_version": ASSURANCE_PACKET_PROTOCOL_VERSION,
            "candidate_hash": candidate.candidate_hash,
            "manifest_hash": manifest.manifest_hash,
            "evidence_bundle_hash": packet.evidence_bundle.bundle_hash,
        }
        provisional = replace(
            packet,
            candidate=candidate,
            verification=verification,
            approval=approval,
            authorization=authorization,
            audit_manifest=manifest,
            packet_id="packet_"
            + sha256_uri(identity_payload).split(":", 1)[1][:24],
            packet_hash="sha256:" + "0" * 64,
        )
        invalid = replace(
            provisional,
            packet_hash=sha256_uri(provisional.payload()),
        )

        valid, errors = verify_assurance_packet(invalid)

        self.assertFalse(valid)
        self.assertIn("verification_findings_mismatch", errors)
        self.assertNotIn("packet_hash_invalid", errors)
        self.assertFalse(any(error.startswith("audit_") for error in errors))

    def test_governed_profile_rejects_agent_self_approval(self) -> None:
        run_context = context()
        evidence_bundle = bundle(run_context)
        result = ProvableAgentPipeline().run(
            context=run_context,
            draft=draft(),
            evidence_bundle=evidence_bundle,
            approver_id=run_context.agent_id,
        )

        with self.assertRaisesRegex(ContractError, "separation_of_duties"):
            build_assurance_packet(
                evidence_bundle=evidence_bundle,
                result=result,
                limitations=("Synthetic test only.",),
            )

    def test_governed_profile_requires_visible_approval_metadata(self) -> None:
        packet = self.build_packet()
        invalid = self.rebind_approval(packet, approver_id="", rationale="")

        valid, errors = verify_assurance_packet(invalid)

        self.assertFalse(valid)
        self.assertNotIn("packet_hash_invalid", errors)
        self.assertFalse(any(error.startswith("audit_") for error in errors))
        self.assertIn("approval_identity_missing", errors)
        self.assertIn("approval_rationale_missing", errors)

    def test_governed_profile_rejects_case_variant_self_approval(self) -> None:
        packet = self.build_packet()
        invalid = self.rebind_approval(
            packet,
            approver_id=packet.candidate.run_context.agent_id.upper(),
        )

        valid, errors = verify_assurance_packet(invalid)

        self.assertFalse(valid)
        self.assertIn("approval_separation_of_duties_failed", errors)


if __name__ == "__main__":
    unittest.main()
