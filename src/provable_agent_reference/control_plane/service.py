from __future__ import annotations

import uuid
from typing import Any

from .models import CapabilityGrant, RunRequest
from .store import PostgresStore, sha256_uri


class ControlPlaneService:
    def __init__(self, store: PostgresStore) -> None:
        self.store = store

    def create_run(self, request: RunRequest, idempotency_key: str) -> str:
        if not idempotency_key or len(idempotency_key) > 500:
            raise ValueError("a bounded idempotency key is required")
        identity = {
            "case_id": request.case_id,
            "idempotency_key": idempotency_key,
            "requester_subject": request.requester_subject,
            "tenant_id": request.tenant_id,
        }
        run_id = "run_" + sha256_uri(identity).split(":", 1)[1][:24]
        body = request.journal_body()
        event_id = "evt_" + uuid.uuid4().hex
        event_without_hash = {
            "event_id": event_id,
            "tenant_id": request.tenant_id,
            "case_id": request.case_id,
            "run_id": run_id,
            "sequence": 0,
            "previous_event_hash": None,
            "body": body,
            "body_hash": sha256_uri(body),
        }
        event = {**event_without_hash, "record_hash": sha256_uri(event_without_hash)}
        run: dict[str, Any] = {"run_id": run_id, **request.__dict__}
        outbox = {
            "outbox_id": "outbox_" + uuid.uuid4().hex,
            "tenant_id": request.tenant_id,
            "aggregate_type": "run",
            "aggregate_id": run_id,
            "event_type": "run.requested",
            "payload": {"event_id": event_id, "record_hash": event["record_hash"]},
        }
        self.store.create_run(run, event, outbox)
        return run_id

    @staticmethod
    def require_attenuation(parent: CapabilityGrant, child: CapabilityGrant) -> None:
        if not parent.permits_child(child):
            raise PermissionError("child capability grant expands parent authority")
