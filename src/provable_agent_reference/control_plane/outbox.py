from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .store import PostgresStore


class OutboxWorker:
    def __init__(
        self,
        store: PostgresStore,
        worker_id: str,
        publish: Callable[[str, dict[str, Any]], None],
    ) -> None:
        self.store = store
        self.worker_id = worker_id
        self.publish = publish

    def run_once(self, limit: int = 50) -> tuple[int, int]:
        completed = 0
        failed = 0
        for item in self.store.claim_outbox(self.worker_id, limit):
            try:
                self.publish(item["event_type"], item["payload"])
            except Exception as exc:
                failed += 1
                delay = min(2 ** min(item["attempts"], 10), 3600)
                self.store.retry_outbox(
                    item["outbox_id"],
                    self.worker_id,
                    f"{type(exc).__name__}: publication failed",
                    delay,
                )
            else:
                self.store.complete_outbox(item["outbox_id"], self.worker_id)
                completed += 1
        return completed, failed
