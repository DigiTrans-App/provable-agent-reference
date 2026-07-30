from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol

from ..contracts import Classification, EvidenceBundle

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
_VERSION = re.compile(r"^[0-9][0-9A-Za-z_.-]{0,63}$")
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
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
        if self.status not in {"available", "partial", "unavailable"}:
            raise AdapterValidationError("coverage status is not supported")
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
    """Privacy-minimized evidence and coverage metadata from a runtime adapter."""

    runtime: str
    adapter_version: str
    context: AdapterContext
    evidence_bundle: EvidenceBundle
    coverage: tuple[CoverageFinding, ...]
    accepted_event_count: int
    ignored_event_count: int
    source_stream_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.runtime):
            raise AdapterValidationError("runtime is not a valid identifier")
        if not _VERSION.fullmatch(self.adapter_version):
            raise AdapterValidationError("adapter_version is not valid")
        if (self.evidence_bundle.tenant_id, self.evidence_bundle.case_id) != (
            self.context.tenant_id,
            self.context.case_id,
        ):
            raise AdapterValidationError("evidence bundle does not match adapter context scope")
        capabilities = [finding.capability for finding in self.coverage]
        if len(capabilities) != len(set(capabilities)):
            raise AdapterValidationError("coverage contains duplicate capabilities")
        if self.accepted_event_count < 0 or self.ignored_event_count < 0:
            raise AdapterValidationError("event counts must not be negative")
        if not self.source_stream_hashes:
            raise AdapterValidationError("at least one source stream hash is required")
        if any(not _HASH.fullmatch(value) for value in self.source_stream_hashes):
            raise AdapterValidationError("source stream hash is not a valid sha256 URI")

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
        """Normalize runtime streams into deterministic privacy-minimized evidence."""

        ...
