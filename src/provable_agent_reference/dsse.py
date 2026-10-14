from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from .canonical import canonical_json, sha256_uri

ASSURANCE_PACKET_PAYLOAD_TYPE = (
    "application/vnd.digitrans.provable-agent.assurance-packet+json;"
    "version=0.3.0-candidate.1"
)
DEVELOPMENT_KEY_ID = "development:packet-issuer:ed25519:v1"
_DEVELOPMENT_SEED_LABEL = b"provable-agent-reference-development-ed25519-v1"


class DSSEVerificationError(ValueError):
    """Raised when an envelope or its verifier-pinned trust metadata fails closed."""


def _validate_interoperable_json(value: Any, path: str = "$") -> None:
    if isinstance(value, float):
        raise ValueError(f"floating-point numbers are not supported at {path}")
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) > 2**53 - 1:
        raise ValueError(f"integer exceeds the interoperable safe range at {path}")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_interoperable_json(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            _validate_interoperable_json(item, f"{path}.{key}")


def pae(payload_type: str, payload: bytes) -> bytes:
    """Return DSSE v1 pre-authentication encoding using UTF-8 byte lengths."""

    if not isinstance(payload_type, str) or not payload_type:
        raise ValueError("payload_type must be a non-empty string")
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    type_bytes = payload_type.encode("utf-8")
    return b"DSSEv1 %d %s %d %s" % (
        len(type_bytes),
        type_bytes,
        len(payload),
        payload,
    )


def _crypto() -> tuple[Any, Any, Any, Any]:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    except ImportError as exc:  # pragma: no cover - exercised by minimal installations
        raise RuntimeError("DSSE signing requires the optional 'signing' dependency") from exc
    return InvalidSignature, Ed25519PrivateKey, Encoding, PublicFormat


def development_public_key_base64() -> str:
    """Return the public half of the reproducible, non-secret development key."""

    _, private_key_type, encoding, public_format = _crypto()
    seed = hashlib.sha256(_DEVELOPMENT_SEED_LABEL).digest()
    public_bytes = private_key_type.from_private_bytes(seed).public_key().public_bytes(
        encoding.Raw, public_format.Raw
    )
    return base64.b64encode(public_bytes).decode("ascii")


def sign_assurance_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Sign exact canonical packet bytes with the development-only Ed25519 key."""

    if not isinstance(packet, dict):
        raise TypeError("packet must be a JSON object")
    _validate_interoperable_json(packet)
    _, private_key_type, _, _ = _crypto()
    payload = canonical_json(packet).encode("utf-8")
    seed = hashlib.sha256(_DEVELOPMENT_SEED_LABEL).digest()
    signature = private_key_type.from_private_bytes(seed).sign(
        pae(ASSURANCE_PACKET_PAYLOAD_TYPE, payload)
    )
    return {
        "payloadType": ASSURANCE_PACKET_PAYLOAD_TYPE,
        "payload": base64.b64encode(payload).decode("ascii"),
        "signatures": [
            {"keyid": DEVELOPMENT_KEY_ID, "sig": base64.b64encode(signature).decode("ascii")}
        ],
    }


def _decode_base64(value: Any, field: str) -> bytes:
    if not isinstance(value, str):
        raise DSSEVerificationError(f"{field} must be base64 text")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise DSSEVerificationError(f"{field} is not canonical base64") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise DSSEVerificationError(f"{field} is not canonical base64")
    return decoded


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DSSEVerificationError(f"{field} must be a UTC RFC3339 timestamp")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise DSSEVerificationError(f"{field} is invalid") from exc


def verify_envelope(
    envelope: dict[str, Any],
    trust_bundle: dict[str, Any],
    *,
    verification_time: datetime | None = None,
) -> dict[str, Any]:
    """Verify a DSSE packet against external, pinned development trust metadata."""

    if set(envelope) != {"payloadType", "payload", "signatures"}:
        raise DSSEVerificationError("envelope fields do not match the DSSE profile")
    if envelope["payloadType"] != ASSURANCE_PACKET_PAYLOAD_TYPE:
        raise DSSEVerificationError("unexpected payload type")
    signatures = envelope["signatures"]
    if not isinstance(signatures, list) or len(signatures) != 1:
        raise DSSEVerificationError("the development profile requires exactly one signature")
    signature = signatures[0]
    if not isinstance(signature, dict) or set(signature) != {"keyid", "sig"}:
        raise DSSEVerificationError("invalid signature entry")

    keys = trust_bundle.get("keys") if isinstance(trust_bundle, dict) else None
    if not isinstance(keys, list):
        raise DSSEVerificationError("trust bundle keys are missing")
    matches = [key for key in keys if key.get("keyid") == signature["keyid"]]
    if len(matches) != 1:
        raise DSSEVerificationError("key is not uniquely pinned")
    key = matches[0]
    if key.get("algorithm") != "Ed25519" or key.get("role") != "packet_issuer":
        raise DSSEVerificationError("pinned key algorithm or role is not authorized")
    if key.get("status") != "active" or key.get("revoked_at") is not None:
        raise DSSEVerificationError("pinned key is disabled or revoked")

    now = verification_time or datetime.now(UTC)
    if now.tzinfo is None:
        raise DSSEVerificationError("verification_time must be timezone-aware")
    if not (_parse_time(key.get("not_before"), "not_before") <= now <= _parse_time(key.get("not_after"), "not_after")):
        raise DSSEVerificationError("pinned key is outside its verification validity window")

    payload = _decode_base64(envelope["payload"], "payload")
    signature_bytes = _decode_base64(signature["sig"], "signature")
    public_key = _decode_base64(key.get("public_key_base64"), "public key")
    if len(public_key) != 32:
        raise DSSEVerificationError("Ed25519 public key must be 32 bytes")
    invalid_signature, _, _, _ = _crypto()
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature_bytes, pae(envelope["payloadType"], payload)
        )
    except (invalid_signature, ValueError) as exc:
        raise DSSEVerificationError("signature verification failed") from exc

    try:
        packet = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DSSEVerificationError("payload is not UTF-8 JSON") from exc
    if not isinstance(packet, dict) or canonical_json(packet).encode("utf-8") != payload:
        raise DSSEVerificationError("payload is not the exact canonical packet representation")
    try:
        _validate_interoperable_json(packet)
    except ValueError as exc:
        raise DSSEVerificationError(str(exc)) from exc
    if "packet_hash" in packet:
        unsigned_packet = dict(packet)
        claimed_hash = unsigned_packet.pop("packet_hash")
        if claimed_hash != sha256_uri(unsigned_packet):
            raise DSSEVerificationError("packet_hash does not bind the canonical packet")

    return {
        "packet": packet,
        "issuer": key.get("issuer"),
        "keyid": key["keyid"],
        "algorithm": key["algorithm"],
        "role": key["role"],
        "trusted_signing_time": False,
        "limitations": [
            "The development key is public and provides interoperability testing only.",
            "DSSE does not provide an independently trusted signing time.",
        ],
    }
