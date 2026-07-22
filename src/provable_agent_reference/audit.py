from __future__ import annotations

from .canonical import sha256_uri
from .contracts import (
    ApprovalRecord,
    AuditManifest,
    AuthorizationResult,
    CanonicalCandidate,
    VerificationResult,
)


def build_audit_manifest(
    *,
    candidate: CanonicalCandidate,
    verification: VerificationResult,
    approval: ApprovalRecord,
    authorization: AuthorizationResult,
) -> AuditManifest:
    manifest_id = "audit_" + sha256_uri(
        {
            "candidate_hash": candidate.candidate_hash,
            "verification_hash": verification.result_hash,
            "approval_hash": approval.record_hash,
            "authorization_hash": authorization.record_hash,
        }
    ).split(":", 1)[1][:24]
    provisional = AuditManifest(
        manifest_id=manifest_id,
        candidate_hash=candidate.candidate_hash,
        verification_result_hash=verification.result_hash,
        approval_record_hash=approval.record_hash,
        authorization_record_hash=authorization.record_hash,
        generated_at=authorization.authorized_at,
        manifest_hash="sha256:" + "0" * 64,
    )
    return AuditManifest(
        **{**provisional.__dict__, "manifest_hash": sha256_uri(provisional.payload())}
    )


def verify_audit_manifest(
    *,
    manifest: AuditManifest,
    candidate: CanonicalCandidate,
    verification: VerificationResult,
    approval: ApprovalRecord,
    authorization: AuthorizationResult,
) -> tuple[bool, tuple[str, ...]]:
    errors: list[str] = []
    if not candidate.verify_hash():
        errors.append("candidate_hash_invalid")
    if not verification.verify_hash():
        errors.append("verification_hash_invalid")
    if not approval.verify_hash():
        errors.append("approval_hash_invalid")
    if not authorization.verify_hash():
        errors.append("authorization_hash_invalid")
    if not manifest.verify_hash():
        errors.append("manifest_hash_invalid")
    if manifest.candidate_hash != candidate.candidate_hash:
        errors.append("candidate_binding_mismatch")
    if manifest.verification_result_hash != verification.result_hash:
        errors.append("verification_binding_mismatch")
    if manifest.approval_record_hash != approval.record_hash:
        errors.append("approval_binding_mismatch")
    if manifest.authorization_record_hash != authorization.record_hash:
        errors.append("authorization_binding_mismatch")
    if verification.candidate_hash != candidate.candidate_hash:
        errors.append("verification_candidate_mismatch")
    if approval.candidate_hash != candidate.candidate_hash:
        errors.append("approval_candidate_mismatch")
    if authorization.candidate_hash != candidate.candidate_hash:
        errors.append("authorization_candidate_mismatch")
    return not errors, tuple(errors)
