from __future__ import annotations

from dataclasses import dataclass, field

from .approvals import record_approval
from .audit import build_audit_manifest, verify_audit_manifest
from .authorization import authorize_exact_use
from .compiler import TrustedCompiler
from .contracts import (
    ApprovalRecord,
    AuditManifest,
    AuthorizationResult,
    CanonicalCandidate,
    EvidenceBundle,
    SemanticDraft,
    TrustedRunContext,
    VerificationResult,
)
from .verification import DeterministicVerifier


@dataclass(frozen=True)
class PipelineResult:
    candidate: CanonicalCandidate
    verification: VerificationResult
    approval: ApprovalRecord
    authorization: AuthorizationResult
    audit_manifest: AuditManifest
    audit_valid: bool
    audit_errors: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate": self.candidate.to_dict(),
            "verification": self.verification.to_dict(),
            "approval": self.approval.to_dict(),
            "authorization": self.authorization.to_dict(),
            "audit_manifest": self.audit_manifest.to_dict(),
            "audit_valid": self.audit_valid,
            "audit_errors": list(self.audit_errors),
        }


@dataclass(frozen=True)
class ProvableAgentPipeline:
    compiler: TrustedCompiler = field(default_factory=TrustedCompiler)
    verifier: DeterministicVerifier = field(default_factory=DeterministicVerifier)

    def run(
        self,
        *,
        context: TrustedRunContext,
        draft: SemanticDraft,
        evidence_bundle: EvidenceBundle,
        approver_id: str,
    ) -> PipelineResult:
        candidate = self.compiler.compile(
            context=context,
            draft=draft,
            evidence_bundle=evidence_bundle,
        )
        verification = self.verifier.verify(
            candidate=candidate,
            evidence_bundle=evidence_bundle,
        )
        approval = record_approval(
            candidate=candidate,
            verification=verification,
            approver_id=approver_id,
        )
        output = {
            "assurance_statement": candidate.assurance_statement,
            "limitations": list(candidate.limitations),
        }
        authorization = authorize_exact_use(
            candidate=candidate,
            approval=approval,
            purpose=context.purpose,
            audience=context.audience,
            output=output,
        )
        manifest = build_audit_manifest(
            candidate=candidate,
            verification=verification,
            approval=approval,
            authorization=authorization,
        )
        valid, errors = verify_audit_manifest(
            manifest=manifest,
            candidate=candidate,
            verification=verification,
            approval=approval,
            authorization=authorization,
        )
        return PipelineResult(
            candidate=candidate,
            verification=verification,
            approval=approval,
            authorization=authorization,
            audit_manifest=manifest,
            audit_valid=valid,
            audit_errors=errors,
        )
