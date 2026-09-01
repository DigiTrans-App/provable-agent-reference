from __future__ import annotations

import string
from dataclasses import dataclass

from hypothesis import strategies as st

from provable_agent_reference import (
    EvidenceBundle,
    EvidenceRecord,
    PipelineResult,
    ProvableAgentPipeline,
    SemanticDraft,
    TrustedRunContext,
)

IDENTIFIER_ALPHABET = string.ascii_lowercase + string.digits
IDENTIFIER_SUFFIXES = st.text(
    alphabet=IDENTIFIER_ALPHABET,
    min_size=3,
    max_size=18,
)
SAFE_TEXT = st.text(
    alphabet=st.characters(exclude_categories=("Cs",)),
    min_size=1,
    max_size=80,
)
CLASSIFICATIONS = st.sampled_from(
    ("public", "internal", "confidential", "restricted", "regulated")
)
JSON_SCALARS = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**53) + 1, max_value=(2**53) - 1),
    st.floats(
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
    st.text(
        alphabet=st.characters(exclude_categories=("Cs",)),
        max_size=40,
    ),
)
JSON_VALUES = st.recursive(
    JSON_SCALARS,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(
            st.text(
                alphabet=st.characters(exclude_categories=("Cs",)),
                max_size=20,
            ),
            children,
            max_size=5,
        ),
    ),
    max_leaves=20,
)


@dataclass(frozen=True)
class PipelineCase:
    context: TrustedRunContext
    bundle: EvidenceBundle
    draft: SemanticDraft

    def run(self) -> PipelineResult:
        return ProvableAgentPipeline().run(
            context=self.context,
            draft=self.draft,
            evidence_bundle=self.bundle,
            approver_id="human_property_reviewer",
        )


@st.composite
def run_contexts(draw: st.DrawFn) -> TrustedRunContext:
    suffix = draw(IDENTIFIER_SUFFIXES)
    return TrustedRunContext(
        tenant_id=f"tenant_{suffix}",
        case_id=f"case_{suffix}",
        run_id=f"run_{suffix}",
        agent_id=f"agent_{suffix}",
        purpose=draw(SAFE_TEXT),
        audience=draw(SAFE_TEXT),
        classification=draw(CLASSIFICATIONS),  # type: ignore[arg-type]
        created_at=f"2026-01-01T00:00:{draw(st.integers(0, 59)):02d}Z",
    )


@st.composite
def pipeline_cases(draw: st.DrawFn) -> PipelineCase:
    context = draw(run_contexts())
    evidence_text = draw(SAFE_TEXT)
    record = EvidenceRecord.from_text(
        evidence_id="evidence_property_primary",
        tenant_id=context.tenant_id,
        case_id=context.case_id,
        text=evidence_text,
        source_uri=f"synthetic://property/{draw(IDENTIFIER_SUFFIXES)}",
        classification=context.classification,
        summary=draw(SAFE_TEXT),
    )
    bundle = EvidenceBundle.create(
        bundle_id=f"bundle_{draw(IDENTIFIER_SUFFIXES)}",
        tenant_id=context.tenant_id,
        case_id=context.case_id,
        records=(record,),
    )
    draft = SemanticDraft(
        claim_text=draw(SAFE_TEXT),
        selected_evidence_id=record.evidence_id,
        limitations=(draw(SAFE_TEXT),),
        assurance_statement=draw(SAFE_TEXT),
        content_categories=(),
        redacted=False,
    )
    return PipelineCase(context=context, bundle=bundle, draft=draft)


@st.composite
def two_record_bundles(
    draw: st.DrawFn,
) -> tuple[TrustedRunContext, EvidenceRecord, EvidenceRecord, EvidenceBundle]:
    context = draw(run_contexts())
    first = EvidenceRecord.from_text(
        evidence_id="evidence_property_first",
        tenant_id=context.tenant_id,
        case_id=context.case_id,
        text=draw(SAFE_TEXT),
        source_uri="synthetic://property/first",
        classification=context.classification,
        summary=draw(SAFE_TEXT),
    )
    second_text = draw(SAFE_TEXT)
    second = EvidenceRecord.from_text(
        evidence_id="evidence_property_second",
        tenant_id=context.tenant_id,
        case_id=context.case_id,
        text=second_text,
        source_uri="synthetic://property/second",
        classification=context.classification,
        summary=draw(SAFE_TEXT),
    )
    bundle = EvidenceBundle.create(
        bundle_id="bundle_property_pair",
        tenant_id=context.tenant_id,
        case_id=context.case_id,
        records=(first, second),
    )
    return context, first, second, bundle


def alternate_identifier(value: str) -> str:
    alternate = f"{value}_other"
    if len(alternate) <= 127:
        return alternate
    return "other_" + value[:120]


def alternate_text(value: str) -> str:
    return value + " [other]"
