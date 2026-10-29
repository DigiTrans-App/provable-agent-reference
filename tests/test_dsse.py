from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from provable_agent_reference.canonical import sha256_uri
from provable_agent_reference.dsse import (
    ASSURANCE_PACKET_PAYLOAD_TYPE,
    DSSEVerificationError,
    development_public_key_base64,
    sign_assurance_packet,
    verify_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
TRUST = json.loads((ROOT / "trust/development-trust-bundle.json").read_text())
VERIFY_AT = datetime(2027, 1, 1, tzinfo=UTC)


def packet() -> dict[str, object]:
    value: dict[str, object] = {
        "authorized_output": {"assurance_statement": "Synthetic verification passed."},
        "claimed_profiles": ["par.core.v1"],
        "created_at": "2026-01-01T00:00:00Z",
        "limitations": ["Synthetic data and development signature only."],
        "packet_id": "packet_dsse_vector_001",
        "protocol_version": "0.3.0-candidate.1",
    }
    value["packet_hash"] = sha256_uri(value)
    return value


class DSSETests(unittest.TestCase):
    def test_development_key_matches_pinned_bundle(self) -> None:
        self.assertEqual(development_public_key_base64(), TRUST["keys"][0]["public_key_base64"])

    def test_round_trip_and_exact_payload(self) -> None:
        envelope = sign_assurance_packet(packet())
        result = verify_envelope(envelope, TRUST, verification_time=VERIFY_AT)
        self.assertEqual(result["packet"], packet())
        self.assertFalse(result["trusted_signing_time"])
        self.assertEqual(envelope["payloadType"], ASSURANCE_PACKET_PAYLOAD_TYPE)

    def test_mutations_and_untrusted_metadata_fail_closed(self) -> None:
        envelope = sign_assurance_packet(packet())
        cases: list[tuple[dict[str, object], dict[str, object]]] = []
        bad_signature = copy.deepcopy(envelope)
        bad_signature["signatures"][0]["sig"] = "A" + bad_signature["signatures"][0]["sig"][1:]
        cases.append((bad_signature, TRUST))
        wrong_type = copy.deepcopy(envelope)
        wrong_type["payloadType"] = "application/json"
        cases.append((wrong_type, TRUST))
        wrong_key = copy.deepcopy(envelope)
        wrong_key["signatures"][0]["keyid"] = "unknown"
        cases.append((wrong_key, TRUST))
        for field, value in (("role", "approver"), ("algorithm", "Ed448"), ("status", "disabled")):
            trust = copy.deepcopy(TRUST)
            trust["keys"][0][field] = value
            cases.append((envelope, trust))
        revoked = copy.deepcopy(TRUST)
        revoked["keys"][0]["revoked_at"] = "2026-12-01T00:00:00Z"
        cases.append((envelope, revoked))
        for candidate_envelope, candidate_trust in cases:
            with self.subTest(candidate_envelope=candidate_envelope, candidate_trust=candidate_trust):
                with self.assertRaises(DSSEVerificationError):
                    verify_envelope(candidate_envelope, candidate_trust, verification_time=VERIFY_AT)

    def test_cross_language_typescript_verifier(self) -> None:
        if subprocess.run(["node", "--version"], capture_output=True).returncode != 0:
            self.skipTest("Node.js is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "envelope.json"
            path.write_text(json.dumps(sign_assurance_packet(packet())), encoding="utf-8")
            completed = subprocess.run(
                ["node", str(ROOT / "typescript/verifier.ts"), str(path), str(ROOT / "trust/development-trust-bundle.json")],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_committed_vector_is_reproducible_and_cross_language(self) -> None:
        vector_packet = json.loads((ROOT / "vectors/dsse/packet.json").read_text())
        vector_envelope = json.loads((ROOT / "vectors/dsse/envelope.json").read_text())
        self.assertEqual(sign_assurance_packet(vector_packet), vector_envelope)
        self.assertEqual(
            verify_envelope(vector_envelope, TRUST, verification_time=VERIFY_AT)["packet"],
            vector_packet,
        )
        completed = subprocess.run(
            [
                "node",
                str(ROOT / "typescript/verifier.ts"),
                str(ROOT / "vectors/dsse/envelope.json"),
                str(ROOT / "trust/development-trust-bundle.json"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_non_interoperable_numbers_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            sign_assurance_packet({"value": 1.5})
        with self.assertRaises(ValueError):
            sign_assurance_packet({"value": 2**53})


if __name__ == "__main__":
    unittest.main()
