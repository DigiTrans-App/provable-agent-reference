from __future__ import annotations

import os

from provable_agent_reference.control_plane.models import RunRequest
from provable_agent_reference.control_plane.security import validate_local_reset_target
from provable_agent_reference.control_plane.service import ControlPlaneService
from provable_agent_reference.control_plane.store import PostgresStore


def main() -> int:
    environment = os.environ.get("PAR_ENVIRONMENT", "")
    database_url = os.environ.get("PAR_DATABASE_URL", "")
    validate_local_reset_target(environment, database_url)
    service = ControlPlaneService(PostgresStore(database_url))
    run_id = service.create_run(
        RunRequest(
            tenant_id="tenant_synthetic",
            case_id="case_vendor_review",
            requester_subject="subject:synthetic-requester",
            purpose="Exercise the local durable control-plane reference.",
            audience="synthetic-reviewer",
            risk_tier=0,
            policy_version="policy:synthetic:1",
        ),
        idempotency_key="seed-v1",
    )
    print(run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
