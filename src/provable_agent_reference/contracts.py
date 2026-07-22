from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any, Literal

from .canonical import sha256_uri
from .errors import ContractError

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
Classification = Literal["public", "internal", "confidential", "restricted", "regulated"]
Decision = Literal["approved", "rejected", "changes_requested"]
Severity = Literal["info", "warning", "error"]

CLASSIFICATION_ORDER = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
    "regulated": 4,
}

SENSITIVE_CATEGORIES = {
    "secret",
    "credential",
    "authentication_token",
    "private_key",
    "raw_prompt",
    "system_prompt",
    "raw_tool_input",
    "raw_tool_output",
    "raw_evidence",
    "pii",
    "phi",
    "payment_data",
}


def _identifier(value: str, name: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ContractError(f"{name} is not a valid identifier")
    return value


def _hash_uri(value: str, name: str) -> str:
    if not _HASH.fullmatch(value):
        raise ContractError(f"{name} is not a valid sha256 URI")
    return value


def _bounded(value: str, name: str, maximum: int) -> str:
    if not value or len(value) > maximum:
        raise ContractError(f"{name} must contain between 1 and {maximum} characters")
    return value


def _unique(values: Iterable[str], name: str) -> tuple[str, ...]:
    result = tuple(values)
    if len(result) != len(set(result)):
        raise ContractError(f"{name} must not contain duplicates")
    return result


@dataclass(frozen=True)
class TrustedRunContext:
    tenant_id: str
    case_id: str
    run_id: str
    agent_id: str
    purpose: str
    audience: str
    classification: Classification
    created_at: str

    def __post_init__(self) -> None:
        for name in ("tenant_id", "case_id", "run_id", "agent_id"):
            _identifier(getattr(self, name), name)
        _bounded(self.purpose, "purpose", 1000)
        _bounded(self.audience, "audience", 500)
        _bounded(self.created_at, "created_at", 100)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticDraft:
    claim_text: str
    selected_evidence_id: str
    limitations: tuple[str, ...] | list[str]
    assurance_statement: str
    content_categories: tuple[str, ...] | list[str] = ()
    redacted: bool = False

    def __post_init__(self) -> None:
        _bounded(self.claim_text, "claim_text", 4000)
        _identifier(self.selected_evidence_id, "selected_evidence_id")
        limitations = _unique(self.limitations, "limitations")
        if not limitations or len(limitations) > 20:
            raise ContractError("limitations must contain between 1 and 20 items")
        for value in limitations:
            _bounded(value, "limitation", 2000)
        categories = _unique(self.content_categories, "content_categories")
        if len(categories) > 20:
            raise ContractError("content_categories must contain at most 20 items")
        _bounded(self.assurance_statement, "assurance_statement", 8000)
        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "content_categories", categories)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_text": self.claim_text,
            "selected_evidence_id": self.selected_evidence_id,
            "limitations": list(self.limitations),
            "assurance_statement": self.assurance_statement,
            "content_categories": list(self.content_categories),
            "redacted": self.redacted,
        }


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    tenant_id: str
    case_id: str
    content_hash: str
    source_uri: str
    classification: Classification
    summary: str

    def __post_init__(self) -> None:
        for name in ("evidence_id", "tenant_id", "case_id"):
            _identifier(getattr(self, name), name)
        _hash_uri(self.content_hash, "content_hash")
        _bounded(self.source_uri, "source_uri", 2000)
        _bounded(self.summary, "summary", 2000)

    @classmethod
    def from_text(
        cls,
        *,
        evidence_id: str,
        tenant_id: str,
        case_id: str,
        text: str,
        source_uri: str,
        classification: Classification,
        summary: str,
    ) -> EvidenceRecord:
        return cls(
            evidence_id=evidence_id,
            tenant_id=tenant_id,
            case_id=case_id,
            content_hash=sha256_uri(text.encode("utf-8")),
            source_uri=source_uri,
            classification=classification,
            summary=summary,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceBundle:
    bundle_id: str
    tenant_id: str
    case_id: str
    records: tuple[EvidenceRecord, ...]
    bundle_hash: str

    def __post_init__(self) -> None:
        for name in ("bundle_id", "tenant_id", "case_id"):
            _identifier(getattr(self, name), name)
        _hash_uri(self.bundle_hash, "bundle_hash")
        if not self.records:
            raise ContractError("evidence bundle must contain at least one record")
        identities: set[str] = set()
        for record in self.records:
            if record.evidence_id in identities:
                raise ContractError("evidence bundle contains duplicate evidence identifiers")
            identities.add(record.evidence_id)
            if (record.tenant_id, record.case_id) != (self.tenant_id, self.case_id):
                raise ContractError("evidence bundle contains a cross-scope record")
        if self.bundle_hash != self.compute_hash():
            raise ContractError("evidence bundle hash mismatch")

    @classmethod
    def create(
        cls,
        *,
        bundle_id: str,
        tenant_id: str,
        case_id: str,
        records: Iterable[EvidenceRecord],
    ) -> EvidenceBundle:
        record_tuple = tuple(records)
        provisional = {
            "bundle_id": bundle_id,
            "tenant_id": tenant_id,
            "case_id": case_id,
            "records": [record.to_dict() for record in record_tuple],
        }
        return cls(
            bundle_id=bundle_id,
            tenant_id=tenant_id,
            case_id=case_id,
            records=record_tuple,
            bundle_hash=sha256_uri(provisional),
        )

    def compute_hash(self) -> str:
        return sha256_uri(
            {
                "bundle_id": self.bundle_id,
                "tenant_id": self.tenant_id,
                "case_id": self.case_id,
                "records": [record.to_dict() for record in self.records],
            }
        )

    def require(self, evidence_id: str) -> EvidenceRecord:
        for record in self.records:
            if record.evidence_id == evidence_id:
                return record
        raise ContractError("selected evidence is not present in the authorized bundle")

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "records": [record.to_dict() for record in self.records],
            "bundle_hash": self.bundle_hash,
        }


@dataclass(frozen=True)
class CanonicalCandidate:
    schema_version: str
    candidate_id: str
    compiler_id: str
    compiler_version: str
    run_context: TrustedRunContext
    claim_id: str
    claim_text: str
    evidence: EvidenceRecord
    evidence_bundle_hash: str
    limitations: tuple[str, ...]
    assurance_statement: str
    content_categories: tuple[str, ...]
    redacted: bool
    created_at: str
    candidate_hash: str

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "compiler_id": self.compiler_id,
            "compiler_version": self.compiler_version,
            "run_context": self.run_context.to_dict(),
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "evidence": self.evidence.to_dict(),
            "evidence_bundle_hash": self.evidence_bundle_hash,
            "limitations": list(self.limitations),
            "assurance_statement": self.assurance_statement,
            "content_categories": list(self.content_categories),
            "redacted": self.redacted,
            "created_at": self.created_at,
        }

    def verify_hash(self) -> bool:
        return self.candidate_hash == sha256_uri(self.payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "candidate_hash": self.candidate_hash}


@dataclass(frozen=True)
class VerificationFinding:
    code: str
    severity: Severity
    passed: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationResult:
    result_id: str
    candidate_id: str
    candidate_hash: str
    status: Literal["pass", "fail"]
    findings: tuple[VerificationFinding, ...]
    evaluated_at: str
    result_hash: str

    def payload(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "candidate_id": self.candidate_id,
            "candidate_hash": self.candidate_hash,
            "status": self.status,
            "findings": [finding.to_dict() for finding in self.findings],
            "evaluated_at": self.evaluated_at,
        }

    def verify_hash(self) -> bool:
        return self.result_hash == sha256_uri(self.payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "result_hash": self.result_hash}


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    candidate_id: str
    candidate_hash: str
    verification_result_hash: str
    decision: Decision
    approver_id: str
    rationale: str
    decided_at: str
    record_hash: str

    def payload(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "candidate_id": self.candidate_id,
            "candidate_hash": self.candidate_hash,
            "verification_result_hash": self.verification_result_hash,
            "decision": self.decision,
            "approver_id": self.approver_id,
            "rationale": self.rationale,
            "decided_at": self.decided_at,
        }

    def verify_hash(self) -> bool:
        return self.record_hash == sha256_uri(self.payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "record_hash": self.record_hash}


@dataclass(frozen=True)
class AuthorizationResult:
    authorization_id: str
    candidate_id: str
    candidate_hash: str
    approval_id: str
    purpose: str
    audience: str
    output_hash: str
    authorized: bool
    reason: str
    authorized_at: str
    record_hash: str

    def payload(self) -> dict[str, Any]:
        return {
            "authorization_id": self.authorization_id,
            "candidate_id": self.candidate_id,
            "candidate_hash": self.candidate_hash,
            "approval_id": self.approval_id,
            "purpose": self.purpose,
            "audience": self.audience,
            "output_hash": self.output_hash,
            "authorized": self.authorized,
            "reason": self.reason,
            "authorized_at": self.authorized_at,
        }

    def verify_hash(self) -> bool:
        return self.record_hash == sha256_uri(self.payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "record_hash": self.record_hash}


@dataclass(frozen=True)
class AuditManifest:
    manifest_id: str
    candidate_hash: str
    verification_result_hash: str
    approval_record_hash: str
    authorization_record_hash: str
    generated_at: str
    manifest_hash: str

    def payload(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "candidate_hash": self.candidate_hash,
            "verification_result_hash": self.verification_result_hash,
            "approval_record_hash": self.approval_record_hash,
            "authorization_record_hash": self.authorization_record_hash,
            "generated_at": self.generated_at,
        }

    def verify_hash(self) -> bool:
        return self.manifest_hash == sha256_uri(self.payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "manifest_hash": self.manifest_hash}
