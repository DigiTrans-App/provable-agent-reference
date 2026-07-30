from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ._codex_common import hash_text, require_string, safe_token_or_hash
from .base import AdapterContext, AdapterValidationError

_AGENT_COMMUNICATION_EVENT = "codex.agent_communication"


def normalize_telemetry_events(
    context: AdapterContext,
    events: Iterable[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    accepted = 0
    ignored = 0
    seen_states: set[tuple[str, str]] = set()
    sends: dict[str, dict[str, Any]] = {}
    receives: set[str] = set()
    readable_task_formats = 0
    task_message_count = 0

    for event in events:
        event_name = event.get("event.name", event.get("name"))
        if event_name != _AGENT_COMMUNICATION_EVENT:
            ignored += 1
            continue
        communication_id = require_string(event, "communication_id", event_name)
        state = require_string(event, "state", event_name)
        if state not in {"send", "receive"}:
            raise AdapterValidationError("agent communication state must be send or receive")
        state_key = (communication_id, state)
        if state_key in seen_states:
            raise AdapterValidationError(
                "duplicate agent communication lifecycle state for one identifier"
            )
        seen_states.add(state_key)
        normalized_event: dict[str, Any] = {
            "event_name": _AGENT_COMMUNICATION_EVENT,
            "communication_id_hash": hash_text(communication_id),
            "state": state,
        }
        if state == "send":
            kind = require_string(event, "kind", event_name)
            sender = require_string(event, "sender_thread_id", event_name)
            receiver = require_string(event, "receiver_thread_id", event_name)
            normalized_event.update(
                {
                    "kind": safe_token_or_hash(kind),
                    "sender_thread_id_hash": hash_text(sender),
                    "receiver_thread_id_hash": hash_text(receiver),
                }
            )
            if "content" in event:
                content = event["content"]
                if not isinstance(content, str):
                    raise AdapterValidationError("agent communication content must be a string")
                normalized_event["content_hash"] = hash_text(content)
                normalized_event["content_present"] = True
            else:
                normalized_event["content_present"] = False
            content_format = event.get("content_format")
            if isinstance(content_format, str):
                normalized_event["content_format"] = safe_token_or_hash(content_format)
            if kind in {"spawn", "message", "followup"}:
                task_message_count += 1
                if content_format == "plaintext_audit":
                    readable_task_formats += 1
            sends[communication_id] = normalized_event
        else:
            receives.add(communication_id)
        normalized.append(normalized_event)
        accepted += 1

    orphan_receives = sorted(receives - sends.keys())
    if orphan_receives:
        raise AdapterValidationError(
            "agent communication receive event has no corresponding send event"
        )
    unmatched_sends = len(sends.keys() - receives)
    matched = len(sends.keys() & receives)
    document = {
        "schema_version": "codex-agent-communication-evidence/v0.1",
        "runtime": "codex",
        "run_id_hash": hash_text(context.run_id),
        "created_at": context.created_at,
        "events": normalized,
        "correlation": {
            "matched_lifecycles": matched,
            "unmatched_sends": unmatched_sends,
        },
    }
    facts = {
        "accepted": accepted,
        "ignored": ignored,
        "matched": matched,
        "unmatched_sends": unmatched_sends,
        "send_count": len(sends),
        "task_message_count": task_message_count,
        "readable_task_formats": readable_task_formats,
    }
    return document, facts
