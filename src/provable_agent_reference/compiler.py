from __future__ import annotations

from dataclasses import dataclass

from .canonical import sha256_uri
from .contracts import (
    CLASSIFICATION_ORDER,
    CanonicalCandidate,
    EvidenceBundle,
    SemanticDraft,
    TrustedRunContext,
)
from .errors import CompilationError


@dataclass(frozen=True)
class TrustedCompiler:
    compiler_id: str = "provable_agent_reference.compiler"
    compiler_version: str = "0.1.0"

    def compile(
        self,
        *,
        context: TrustedRunContext,
        draft: SemanticDraft,
        evidence_bundle: EvidenceBundle,
    ) -> CanonicalCandidate:
        if (evidence_bundle.tenant_id, evidence_bundle.case_id) != (
            context.tenant_id,
            context.case_id,
        ):
            raise CompilationError("evidence bundle is outside the trusted run scope")

        evidence = evidence_bundle.require(draft.selected_evidence_id)
        if CLASSIFICATION_ORDER[evidence.classification] > CLASSIFICATION_ORDER[context.classification]:
            raise CompilationError("evidence classification exceeds the trusted context ceiling")

        claim_id = "claim_" + sha256_uri(
            {
                "run_id": context.run_id,
                "claim_text": draft.claim_text,
                "evidence_id": evidence.evidence_id,
            }
        ).split(":", 1)[1][:24]
        candidate_id = "candidate_" + sha256_uri(
            {
                "run_id": context.run_id,
                "draft": draft.to_dict(),
                "bundle_hash": evidence_bundle.bundle_hash,
                "compiler_version": self.compiler_version,
            }
        ).split(":", 1)[1][:24]
        provisional = CanonicalCandidate(
            schema_version="0.1",
            candidate_id=candidate_id,
            compiler_id=self.compiler_id,
            compiler_version=self.compiler_version,
            run_context=context,
            claim_id=claim_id,
            claim_text=draft.claim_text,
            evidence=evidence,
            evidence_bundle_hash=evidence_bundle.bundle_hash,
            limitations=tuple(draft.limitations),
            assurance_statement=draft.assurance_statement,
            content_categories=tuple(draft.content_categories),
            redacted=draft.redacted,
            created_at=context.created_at,
            candidate_hash="sha256:" + "0" * 64,
        )
        return CanonicalCandidate(
            **{**provisional.__dict__, "candidate_hash": sha256_uri(provisional.payload())}
        )
