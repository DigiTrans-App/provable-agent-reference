from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .audit import verify_audit_manifest
from .canonical import sha256_uri
from .contracts import (
    CLASSIFICATION_ORDER,
    ApprovalRecord,
    AuditManifest,
    AuthorizationResult,
    CanonicalCandidate,
    EvidenceBundle,
    EvidenceRecord,
    TrustedRunContext,
    VerificationFinding,
    VerificationResult,
)
from .errors import ContractError
from .pipeline import PipelineResult
from .verification import DeterministicVerifier

ASSURANCE_PACKET_SCHEMA_URI = (
    "https://digitrans.app/schemas/provable-agent-reference/"
    "assurance-packet.schema.json"
)
ASSURANCE_PACKET_PROTOCOL_VERSION = "0.3.0-candidate.1"
SUPPORTED_ASSURANCE_PROFILES = (
    "par.core.v1",
    "par.evidence-bound.v1",
    "par.governed.v1",
    "par.exact-use.v1",
    "par.reconstructable.v1",
)


def _packet_identity(
    *,
    candidate_hash: str,
    manifest_hash: str,
    evidence_bundle_hash: str,
) -> str:
    payload = {
        "protocol_version": ASSURANCE_PACKET_PROTOCOL_VERSION,
        "candidate_hash": candidate_hash,
        "manifest_hash": manifest_hash,
        "evidence_bundle_hash": evidence_bundle_hash,
    }
    return "packet_" + sha256_uri(payload).split(":", 1)[1][:24]


def _profile_errors(profiles: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    if not profiles:
        return ["profile_claim_empty"]
    if any(not isinstance(profile, str) for profile in profiles):
        return ["profile_claim_invalid_type"]
    if len(profiles) != len(set(profiles)):
        errors.append("profile_claim_duplicate")
    expected = SUPPORTED_ASSURANCE_PROFILES[: len(profiles)]
    if profiles != expected:
        errors.append("profile_claim_not_cumulative")
    if any(profile not in SUPPORTED_ASSURANCE_PROFILES for profile in profiles):
        errors.append("profile_claim_unknown")
    return errors


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{name} must be a JSON object")
    return value


def _array(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{name} must be a JSON array")
    return value


def _exact_fields(value: dict[str, Any], name: str, fields: set[str]) -> None:
    actual = set(value)
    if actual != fields:
        missing = sorted(fields - actual)
        unexpected = sorted(actual - fields)
        details = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if unexpected:
            details.append("unexpected=" + ",".join(unexpected))
        raise ContractError(f"{name} fields are invalid: " + "; ".join(details))


def _evidence_record_from_dict(value: Any) -> EvidenceRecord:
    record = _object(value, "evidence record")
    _exact_fields(
        record,
        "evidence record",
        {
            "evidence_id",
            "tenant_id",
            "case_id",
            "content_hash",
            "source_uri",
            "classification",
            "summary",
        },
    )
    return EvidenceRecord(**record)


@dataclass(frozen=True)
class AssurancePacket:
    protocol_version: str
    packet_id: str
    claimed_profiles: tuple[str, ...]
    lifecycle_state: Literal["reconstructed"]
    evidence_bundle: EvidenceBundle
    candidate: CanonicalCandidate
    verification: VerificationResult
    approval: ApprovalRecord
    authorization: AuthorizationResult
    audit_manifest: AuditManifest
    authorized_output: dict[str, Any]
    limitations: tuple[str, ...]
    created_at: str
    packet_hash: str

    def payload(self) -> dict[str, Any]:
        return {
            "$schema": ASSURANCE_PACKET_SCHEMA_URI,
            "protocol_version": self.protocol_version,
            "packet_id": self.packet_id,
            "claimed_profiles": list(self.claimed_profiles),
            "lifecycle": {"state": self.lifecycle_state},
            "evidence_bundle": self.evidence_bundle.to_dict(),
            "records": {
                "candidate": self.candidate.to_dict(),
                "verification": self.verification.to_dict(),
                "approval": self.approval.to_dict(),
                "authorization": self.authorization.to_dict(),
                "audit_manifest": self.audit_manifest.to_dict(),
            },
            "authorized_output": self.authorized_output,
            "limitations": list(self.limitations),
            "created_at": self.created_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "packet_hash": self.packet_hash}


def load_assurance_packet(value: Any) -> AssurancePacket:
    """Parse and verify a JSON-compatible Assurance Packet candidate."""

    try:
        root = _object(value, "assurance packet")
        _exact_fields(
            root,
            "assurance packet",
            {
                "$schema",
                "protocol_version",
                "packet_id",
                "claimed_profiles",
                "lifecycle",
                "evidence_bundle",
                "records",
                "authorized_output",
                "limitations",
                "created_at",
                "packet_hash",
            },
        )
        if root["$schema"] != ASSURANCE_PACKET_SCHEMA_URI:
            raise ContractError("assurance packet schema URI is unsupported")

        lifecycle = _object(root["lifecycle"], "lifecycle")
        _exact_fields(lifecycle, "lifecycle", {"state"})
        output = _object(root["authorized_output"], "authorized output")
        _exact_fields(
            output,
            "authorized output",
            {"assurance_statement", "limitations"},
        )
        _array(output["limitations"], "authorized output limitations")

        bundle_value = _object(root["evidence_bundle"], "evidence bundle")
        _exact_fields(
            bundle_value,
            "evidence bundle",
            {"bundle_id", "tenant_id", "case_id", "records", "bundle_hash"},
        )
        evidence_bundle = EvidenceBundle(
            bundle_id=bundle_value["bundle_id"],
            tenant_id=bundle_value["tenant_id"],
            case_id=bundle_value["case_id"],
            records=tuple(
                _evidence_record_from_dict(record)
                for record in _array(bundle_value["records"], "evidence records")
            ),
            bundle_hash=bundle_value["bundle_hash"],
        )

        records = _object(root["records"], "records")
        _exact_fields(
            records,
            "records",
            {
                "candidate",
                "verification",
                "approval",
                "authorization",
                "audit_manifest",
            },
        )

        candidate_value = _object(records["candidate"], "candidate")
        _exact_fields(
            candidate_value,
            "candidate",
            {
                "schema_version",
                "candidate_id",
                "compiler_id",
                "compiler_version",
                "run_context",
                "claim_id",
                "claim_text",
                "evidence",
                "evidence_bundle_hash",
                "limitations",
                "assurance_statement",
                "content_categories",
                "redacted",
                "created_at",
                "candidate_hash",
            },
        )
        context_value = _object(candidate_value["run_context"], "run context")
        _exact_fields(
            context_value,
            "run context",
            {
                "tenant_id",
                "case_id",
                "run_id",
                "agent_id",
                "purpose",
                "audience",
                "classification",
                "created_at",
            },
        )
        candidate = CanonicalCandidate(
            **{
                **candidate_value,
                "run_context": TrustedRunContext(**context_value),
                "evidence": _evidence_record_from_dict(candidate_value["evidence"]),
                "limitations": tuple(
                    _array(candidate_value["limitations"], "candidate limitations")
                ),
                "content_categories": tuple(
                    _array(
                        candidate_value["content_categories"],
                        "candidate content categories",
                    )
                ),
            }
        )

        verification_value = _object(records["verification"], "verification")
        _exact_fields(
            verification_value,
            "verification",
            {
                "result_id",
                "candidate_id",
                "candidate_hash",
                "verifier_id",
                "verifier_version",
                "status",
                "findings",
                "evaluated_at",
                "result_hash",
            },
        )
        findings = []
        for raw_finding in _array(verification_value["findings"], "findings"):
            finding = _object(raw_finding, "finding")
            _exact_fields(
                finding,
                "finding",
                {"code", "severity", "passed", "message"},
            )
            findings.append(VerificationFinding(**finding))
        verification = VerificationResult(
            **{**verification_value, "findings": tuple(findings)}
        )

        approval_value = _object(records["approval"], "approval")
        _exact_fields(
            approval_value,
            "approval",
            {
                "approval_id",
                "candidate_id",
                "candidate_hash",
                "verification_result_hash",
                "decision",
                "approver_id",
                "rationale",
                "decided_at",
                "record_hash",
            },
        )
        authorization_value = _object(records["authorization"], "authorization")
        _exact_fields(
            authorization_value,
            "authorization",
            {
                "authorization_id",
                "candidate_id",
                "candidate_hash",
                "approval_id",
                "purpose",
                "audience",
                "output_hash",
                "authorized",
                "reason",
                "authorized_at",
                "record_hash",
            },
        )
        manifest_value = _object(records["audit_manifest"], "audit manifest")
        _exact_fields(
            manifest_value,
            "audit manifest",
            {
                "manifest_id",
                "candidate_hash",
                "verification_result_hash",
                "approval_record_hash",
                "authorization_record_hash",
                "generated_at",
                "manifest_hash",
            },
        )

        packet = AssurancePacket(
            protocol_version=root["protocol_version"],
            packet_id=root["packet_id"],
            claimed_profiles=tuple(
                _array(root["claimed_profiles"], "claimed profiles")
            ),
            lifecycle_state=lifecycle["state"],
            evidence_bundle=evidence_bundle,
            candidate=candidate,
            verification=verification,
            approval=ApprovalRecord(**approval_value),
            authorization=AuthorizationResult(**authorization_value),
            audit_manifest=AuditManifest(**manifest_value),
            authorized_output=output,
            limitations=tuple(_array(root["limitations"], "packet limitations")),
            created_at=root["created_at"],
            packet_hash=root["packet_hash"],
        )
        valid, errors = verify_assurance_packet(packet)
        if not valid:
            raise ContractError("assurance packet failed verification: " + ", ".join(errors))
        return packet
    except ContractError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError(f"assurance packet could not be parsed: {exc}") from exc


def build_assurance_packet(
    *,
    evidence_bundle: EvidenceBundle,
    result: PipelineResult,
    limitations: tuple[str, ...] | list[str],
    claimed_profiles: tuple[str, ...] = SUPPORTED_ASSURANCE_PROFILES,
) -> AssurancePacket:
    limitation_tuple = tuple(limitations)
    if not limitation_tuple:
        raise ContractError("assurance packet must state at least one limitation")
    if len(limitation_tuple) != len(set(limitation_tuple)):
        raise ContractError("assurance packet limitations must not contain duplicates")
    if any(not value or len(value) > 2000 for value in limitation_tuple):
        raise ContractError("assurance packet limitations must contain 1 to 2000 characters")
    profile_errors = _profile_errors(claimed_profiles)
    if profile_errors:
        raise ContractError("invalid assurance profile claim: " + ", ".join(profile_errors))
    if not result.audit_valid:
        raise ContractError("cannot package an invalid audit chain")

    output = {
        "assurance_statement": result.candidate.assurance_statement,
        "limitations": list(result.candidate.limitations),
    }
    provisional = AssurancePacket(
        protocol_version=ASSURANCE_PACKET_PROTOCOL_VERSION,
        packet_id=_packet_identity(
            candidate_hash=result.candidate.candidate_hash,
            manifest_hash=result.audit_manifest.manifest_hash,
            evidence_bundle_hash=evidence_bundle.bundle_hash,
        ),
        claimed_profiles=claimed_profiles,
        lifecycle_state="reconstructed",
        evidence_bundle=evidence_bundle,
        candidate=result.candidate,
        verification=result.verification,
        approval=result.approval,
        authorization=result.authorization,
        audit_manifest=result.audit_manifest,
        authorized_output=output,
        limitations=limitation_tuple,
        created_at=result.audit_manifest.generated_at,
        packet_hash="sha256:" + "0" * 64,
    )
    packet = AssurancePacket(
        **{**provisional.__dict__, "packet_hash": sha256_uri(provisional.payload())}
    )
    valid, errors = verify_assurance_packet(packet)
    if not valid:
        raise ContractError("assurance packet failed verification: " + ", ".join(errors))
    return packet


def verify_assurance_packet(packet: AssurancePacket) -> tuple[bool, tuple[str, ...]]:
    errors: list[str] = []
    if packet.protocol_version != ASSURANCE_PACKET_PROTOCOL_VERSION:
        errors.append("protocol_version_unsupported")
    if packet.lifecycle_state != "reconstructed":
        errors.append("lifecycle_state_invalid")
    errors.extend(_profile_errors(packet.claimed_profiles))
    try:
        expected_packet_hash = sha256_uri(packet.payload())
    except (TypeError, ValueError):
        errors.append("packet_payload_not_canonicalizable")
    else:
        if packet.packet_hash != expected_packet_hash:
            errors.append("packet_hash_invalid")
    if packet.packet_id != _packet_identity(
        candidate_hash=packet.candidate.candidate_hash,
        manifest_hash=packet.audit_manifest.manifest_hash,
        evidence_bundle_hash=packet.evidence_bundle.bundle_hash,
    ):
        errors.append("packet_id_invalid")
    if not packet.limitations:
        errors.append("packet_limitations_missing")
    elif any(not isinstance(value, str) for value in packet.limitations):
        errors.append("packet_limitations_invalid")
    else:
        if len(packet.limitations) != len(set(packet.limitations)):
            errors.append("packet_limitations_duplicate")
        if any(not value or len(value) > 2000 for value in packet.limitations):
            errors.append("packet_limitations_invalid")
    if not packet.created_at:
        errors.append("packet_timestamp_missing")

    try:
        evidence_bundle_hash = packet.evidence_bundle.compute_hash()
    except (TypeError, ValueError):
        errors.append("evidence_bundle_not_canonicalizable")
    else:
        if packet.evidence_bundle.bundle_hash != evidence_bundle_hash:
            errors.append("evidence_bundle_hash_invalid")
    classifications = (
        packet.candidate.run_context.classification,
        packet.candidate.evidence.classification,
        *(record.classification for record in packet.evidence_bundle.records),
    )
    if any(
        not isinstance(classification, str)
        or classification not in CLASSIFICATION_ORDER
        for classification in classifications
    ):
        errors.append("classification_unsupported")
    if type(packet.candidate.redacted) is not bool:
        errors.append("candidate_redacted_type_invalid")
    if type(packet.authorization.authorized) is not bool:
        errors.append("authorization_flag_type_invalid")
    if packet.candidate.evidence_bundle_hash != packet.evidence_bundle.bundle_hash:
        errors.append("candidate_bundle_binding_mismatch")
    if packet.candidate.schema_version != "0.1":
        errors.append("candidate_schema_version_unsupported")
    if (
        packet.candidate.run_context.tenant_id != packet.evidence_bundle.tenant_id
        or packet.candidate.run_context.case_id != packet.evidence_bundle.case_id
    ):
        errors.append("candidate_bundle_scope_mismatch")
    try:
        bound_evidence = packet.evidence_bundle.require(packet.candidate.evidence.evidence_id)
    except ContractError:
        errors.append("candidate_evidence_missing")
    else:
        if bound_evidence != packet.candidate.evidence:
            errors.append("candidate_evidence_substitution")

    expected_output = {
        "assurance_statement": packet.candidate.assurance_statement,
        "limitations": list(packet.candidate.limitations),
    }
    if packet.authorized_output != expected_output:
        errors.append("authorized_output_candidate_mismatch")
    try:
        authorized_output_hash = sha256_uri(packet.authorized_output)
    except (TypeError, ValueError):
        errors.append("authorized_output_not_canonicalizable")
    else:
        if authorized_output_hash != packet.authorization.output_hash:
            errors.append("authorized_output_hash_mismatch")

    audit_valid, audit_errors = verify_audit_manifest(
        manifest=packet.audit_manifest,
        candidate=packet.candidate,
        verification=packet.verification,
        approval=packet.approval,
        authorization=packet.authorization,
    )
    if not audit_valid:
        errors.extend(f"audit_{error}" for error in audit_errors)
    try:
        recomputed = DeterministicVerifier().verify(
            candidate=packet.candidate,
            evidence_bundle=packet.evidence_bundle,
        )
    except (ContractError, KeyError, TypeError, ValueError):
        errors.append("verification_semantics_unverifiable")
    else:
        expected_findings = {
            finding.code: (finding.severity, finding.passed)
            for finding in recomputed.findings
        }
        packet_findings = {
            finding.code: (finding.severity, finding.passed)
            for finding in packet.verification.findings
        }
        if (
            packet_findings != expected_findings
            or packet.verification.status != recomputed.status
        ):
            errors.append("verification_findings_mismatch")
    if packet.verification.status != "pass":
        errors.append("verification_not_passing")
    if packet.approval.decision != "approved":
        errors.append("approval_not_approved")
    governed_claimed = "par.governed.v1" in packet.claimed_profiles
    if governed_claimed and (
        packet.approval.approver_id == packet.candidate.run_context.agent_id
    ):
        errors.append("approval_separation_of_duties_failed")
    if not packet.authorization.authorized:
        errors.append("exact_use_not_authorized")
    if packet.created_at != packet.audit_manifest.generated_at:
        errors.append("packet_timestamp_mismatch")

    return not errors, tuple(dict.fromkeys(errors))
