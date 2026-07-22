from __future__ import annotations

from .canonical import sha256_uri
from .contracts import ApprovalRecord, CanonicalCandidate, VerificationResult
from .errors import ApprovalError


def record_approval(
    *,
    candidate: CanonicalCandidate,
    verification: VerificationResult,
    approver_id: str,
    decision: str = "approved",
    rationale: str = "Verified candidate approved for the requested exact use.",
) -> ApprovalRecord:
    if verification.candidate_hash != candidate.candidate_hash:
        raise ApprovalError("verification is bound to a different candidate")
    if not verification.verify_hash():
        raise ApprovalError("verification record hash is invalid")
    if verification.status != "pass" and decision == "approved":
        raise ApprovalError("a failed candidate cannot be approved")
    if decision not in {"approved", "rejected", "changes_requested"}:
        raise ApprovalError("unsupported approval decision")
    if not approver_id:
        raise ApprovalError("approver_id is required")

    approval_id = "approval_" + sha256_uri(
        {
            "candidate_hash": candidate.candidate_hash,
            "verification_hash": verification.result_hash,
            "approver_id": approver_id,
            "decision": decision,
        }
    ).split(":", 1)[1][:24]
    provisional = ApprovalRecord(
        approval_id=approval_id,
        candidate_id=candidate.candidate_id,
        candidate_hash=candidate.candidate_hash,
        verification_result_hash=verification.result_hash,
        decision=decision,  # type: ignore[arg-type]
        approver_id=approver_id,
        rationale=rationale,
        decided_at=verification.evaluated_at,
        record_hash="sha256:" + "0" * 64,
    )
    return ApprovalRecord(
        **{**provisional.__dict__, "record_hash": sha256_uri(provisional.payload())}
    )
