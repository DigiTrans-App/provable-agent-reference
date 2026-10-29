from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def s0_report(source_revision: str) -> dict[str, Any]:
    if not source_revision or len(source_revision) > 200:
        raise ValueError("source_revision is required")
    return {
        "level": "S0",
        "status": "incomplete",
        "self_issued": True,
        "tested_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_revision": source_revision,
        "controls": {
            "append_only_logical": "implemented",
            "artifact_digest_verification": "implemented",
            "backup_restore": "not_demonstrated",
            "external_immutability": "not_claimed",
            "independent_attestation": "not_claimed",
            "transactional_outbox": "implemented",
        },
        "limitations": [
            "Self-issued synthetic S0 report; it is not production storage assurance.",
            "Database administrators remain inside the trusted local boundary.",
        ],
    }
