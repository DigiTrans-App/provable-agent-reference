from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _bounded(value: str, name: str, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{name} must contain 1..{maximum} characters")
    return value


@dataclass(frozen=True)
class CapabilityGrant:
    capabilities: frozenset[str]
    tenant_id: str
    case_id: str
    allowed_effects: frozenset[str]
    max_tool_calls: int
    max_model_calls: int
    valid_until: datetime
    delegation_depth: int

    def __post_init__(self) -> None:
        _bounded(self.tenant_id, "tenant_id", 200)
        _bounded(self.case_id, "case_id", 200)
        if not self.capabilities or any(not item for item in self.capabilities):
            raise ValueError("capabilities must not be empty")
        if min(self.max_tool_calls, self.max_model_calls, self.delegation_depth) < 0:
            raise ValueError("budgets and delegation_depth must be non-negative")
        if self.valid_until.tzinfo is None:
            raise ValueError("valid_until must be timezone-aware")

    def permits_child(self, child: CapabilityGrant) -> bool:
        return (
            child.capabilities <= self.capabilities
            and child.tenant_id == self.tenant_id
            and child.case_id == self.case_id
            and child.allowed_effects <= self.allowed_effects
            and child.max_tool_calls <= self.max_tool_calls
            and child.max_model_calls <= self.max_model_calls
            and child.valid_until <= self.valid_until
            and child.delegation_depth < self.delegation_depth
        )


@dataclass(frozen=True)
class RunRequest:
    tenant_id: str
    case_id: str
    requester_subject: str
    purpose: str
    audience: str
    risk_tier: int
    policy_version: str

    def __post_init__(self) -> None:
        for name in ("tenant_id", "case_id", "requester_subject", "policy_version"):
            _bounded(getattr(self, name), name, 500)
        _bounded(self.purpose, "purpose", 2000)
        _bounded(self.audience, "audience", 1000)
        if self.risk_tier not in range(5):
            raise ValueError("risk_tier must be between 0 and 4")

    def journal_body(self) -> dict[str, Any]:
        return {
            "audience": self.audience,
            "policy_version": self.policy_version,
            "purpose": self.purpose,
            "requester_subject": self.requester_subject,
            "risk_tier": self.risk_tier,
        }


def utc_now() -> datetime:
    return datetime.now(UTC)
