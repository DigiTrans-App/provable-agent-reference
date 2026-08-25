from __future__ import annotations

from .canonical import sha256_uri
from .contracts import ApprovalRecord, AuthorizationResult, CanonicalCandidate
from .errors import AuthorizationError


def authorize_exact_use(
    *,
    candidate: CanonicalCandidate,
    approval: ApprovalRecord,
    purpose: str,
    audience: str,
    output: dict[str, object],
) -> AuthorizationResult:
    if not candidate.verify_hash():
        raise AuthorizationError("candidate hash is invalid")
    if approval.decision != "approved":
        raise AuthorizationError("candidate does not have an approved decision")
    if not approval.verify_hash():
        raise AuthorizationError("approval record hash is invalid")
    if (
        approval.candidate_id != candidate.candidate_id
        or approval.candidate_hash != candidate.candidate_hash
    ):
        raise AuthorizationError("approval is bound to a different candidate")

    expected_output = {
        "assurance_statement": candidate.assurance_statement,
        "limitations": list(candidate.limitations),
    }
    exact_scope = (
        purpose == candidate.run_context.purpose
        and audience == candidate.run_context.audience
        and output == expected_output
    )
    reason = "EXACT_USE_AUTHORIZED" if exact_scope else "EXACT_USE_MISMATCH"
    output_hash = sha256_uri(output)
    authorization_id = "authorization_" + sha256_uri(
        {
            "candidate_hash": candidate.candidate_hash,
            "approval_id": approval.approval_id,
            "purpose": purpose,
            "audience": audience,
            "output_hash": output_hash,
        }
    ).split(":", 1)[1][:24]
    provisional = AuthorizationResult(
        authorization_id=authorization_id,
        candidate_id=candidate.candidate_id,
        candidate_hash=candidate.candidate_hash,
        approval_id=approval.approval_id,
        purpose=purpose,
        audience=audience,
        output_hash=output_hash,
        authorized=exact_scope,
        reason=reason,
        authorized_at=approval.decided_at,
        record_hash="sha256:" + "0" * 64,
    )
    return AuthorizationResult(
        **{**provisional.__dict__, "record_hash": sha256_uri(provisional.payload())}
    )
