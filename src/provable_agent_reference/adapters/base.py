from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol

from ..contracts import Classification, EvidenceBundle

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
CoverageStatus = Literal["available", "partial", "unavailable"]


class AdapterValidationError(ValueError):
    """Raised when runtime evidence cannot be normalized safely."""


@dataclass(frozen=True)
class AdapterContext:
    """Trusted scope supplied by the caller, not inferred from provider events."""

    tenant_id: str
    case_id: str
    run_id: str
    created_at: str
    classification: Classification = "internal"

    def __post_init__(self) -> None:
        for name in ("tenant_id", "case_id", "run_id"):
            value = getattr(self, name)
            if not _IDENTIFIER.fullmatch(value):
                raise AdapterValidationError(f"{name} is not a valid identifier")
        if not self.created_at or len(self.created_at) > 100:
            raise AdapterValidationError("created_at must contain between 1 and 100 characters")
        if self.classification not in {
            "public",
            "internal",
            "confidential",
            "restricted",
            "regulated",
        }:
            raise AdapterValidationError("classification is not supported")

    def to_dict(self) -> dict[str, str]:
        return {
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "run_id": self.run_id,
            "created_at": self.created_at,
            "classification": self.classification,
        }


@dataclass(frozen=True)
class CoverageFinding:
    """One explicit statement about evidence the source stream did or did not expose."""

    capability: str
    status: CoverageStatus
    detail: str

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.capability):
            raise AdapterValidationError("coverage capability is not a valid identifier")
        if not self.detail or len(self.detail) > 1000:
            raise AdapterValidationError(
                "coverage detail must contain between 1 and 1000 characters"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "capability": self.capability,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class AdapterResult:
    """Privacy-safe evidence and coverage metadata produced by a runtime adapter."""

    runtime: str
    adapter_version: str
    context: AdapterContext
    evidence_bundle: EvidenceBundle
    coverage: tuple[CoverageFinding, ...]
    accepted_event_count: int
    ignored_event_count: int
    source_stream_hashes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "runtime": self.runtime,
            "adapter_version": self.adapter_version,
            "context": self.context.to_dict(),
            "evidence_bundle": self.evidence_bundle.to_dict(),
            "coverage": [finding.to_dict() for finding in self.coverage],
            "accepted_event_count": self.accepted_event_count,
            "ignored_event_count": self.ignored_event_count,
            "source_stream_hashes": list(self.source_stream_hashes),
        }


class RuntimeEvidenceAdapter(Protocol):
    """Minimal interface for optional provider/runtime evidence adapters."""

    runtime: str
    adapter_version: str

    def build_evidence(
        self,
        *,
        context: AdapterContext,
        execution_jsonl: str,
        telemetry_jsonl: str = "",
    ) -> AdapterResult:
        """Normalize runtime streams into deterministic privacy-safe evidence."""

        ...
