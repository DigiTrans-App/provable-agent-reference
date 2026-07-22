from __future__ import annotations

from dataclasses import dataclass

from .canonical import sha256_uri
from .contracts import (
    SENSITIVE_CATEGORIES,
    CanonicalCandidate,
    EvidenceBundle,
    VerificationFinding,
    VerificationResult,
)


@dataclass(frozen=True)
class DeterministicVerifier:
    verifier_id: str = "provable_agent_reference.verifier"
    verifier_version: str = "0.1.0"

    def verify(
        self,
        *,
        candidate: CanonicalCandidate,
        evidence_bundle: EvidenceBundle,
    ) -> VerificationResult:
        findings: list[VerificationFinding] = []

        findings.append(
            VerificationFinding(
                code="CANDIDATE_HASH_VALID",
                severity="error",
                passed=candidate.verify_hash(),
                message="Canonical candidate hash must match its deterministic payload.",
            )
        )
        findings.append(
            VerificationFinding(
                code="EVIDENCE_BUNDLE_BOUND",
                severity="error",
                passed=(
                    candidate.evidence_bundle_hash == evidence_bundle.bundle_hash
                    and evidence_bundle.compute_hash() == evidence_bundle.bundle_hash
                ),
                message="Candidate must bind the exact authorized evidence bundle.",
            )
        )
        try:
            evidence = evidence_bundle.require(candidate.evidence.evidence_id)
            evidence_present = evidence == candidate.evidence
        except Exception:
            evidence_present = False
        findings.append(
            VerificationFinding(
                code="EVIDENCE_REFERENCE_VALID",
                severity="error",
                passed=evidence_present,
                message="Candidate evidence must resolve exactly in the authorized bundle.",
            )
        )
        findings.append(
            VerificationFinding(
                code="SCOPE_MATCH",
                severity="error",
                passed=(
                    candidate.evidence.tenant_id == candidate.run_context.tenant_id
                    and candidate.evidence.case_id == candidate.run_context.case_id
                    and evidence_bundle.tenant_id == candidate.run_context.tenant_id
                    and evidence_bundle.case_id == candidate.run_context.case_id
                ),
                message="Run, evidence, and bundle scopes must match.",
            )
        )
        sensitive = set(candidate.content_categories) & SENSITIVE_CATEGORIES
        findings.append(
            VerificationFinding(
                code="DISCLOSURE_SAFE",
                severity="error",
                passed=not sensitive or candidate.redacted,
                message="Sensitive categories require explicit redaction intent.",
            )
        )
        findings.append(
            VerificationFinding(
                code="LIMITATION_PRESENT",
                severity="warning",
                passed=bool(candidate.limitations),
                message="Consequential outputs must state at least one limitation.",
            )
        )

        status = (
            "pass"
            if all(item.passed for item in findings if item.severity == "error")
            else "fail"
        )
        result_id = "verification_" + sha256_uri(
            {
                "candidate_hash": candidate.candidate_hash,
                "findings": [item.to_dict() for item in findings],
            }
        ).split(":", 1)[1][:24]
        provisional = VerificationResult(
            result_id=result_id,
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.candidate_hash,
            status=status,
            findings=tuple(findings),
            evaluated_at=candidate.created_at,
            result_hash="sha256:" + "0" * 64,
        )
        return VerificationResult(
            **{**provisional.__dict__, "result_hash": sha256_uri(provisional.payload())}
        )
