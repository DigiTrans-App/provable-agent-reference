from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..canonical import sha256_uri
from ._codex_common import (
    hash_text,
    require_string,
    safe_token_or_hash,
    safe_usage,
)
from .base import AdapterContext, AdapterValidationError

_EXEC_EVENT_TYPES = {
    "thread.started",
    "turn.started",
    "turn.completed",
    "turn.failed",
    "error",
    "item.started",
    "item.updated",
    "item.completed",
    "session.configured",
    "session.catalog",
    "turn.configured",
}
_ITEM_EVENT_TYPES = {"item.started", "item.updated", "item.completed"}
_ACTIVITY_ITEM_TYPES = {
    "command_execution",
    "file_change",
    "mcp_tool_call",
    "web_search",
}


def normalize_execution_events(
    context: AdapterContext,
    events: Iterable[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    accepted = 0
    ignored = 0
    seen_thread_ids: set[str] = set()
    seen_terminal_items: set[tuple[str, str]] = set()
    observed_activity = False
    offered_tools = False
    offered_skills = False
    permissions_profile = False

    for event in events:
        event_type = event.get("type")
        if not isinstance(event_type, str) or event_type not in _EXEC_EVENT_TYPES:
            ignored += 1
            continue

        if event_type == "thread.started":
            thread_id = require_string(event, "thread_id", event_type)
            if thread_id in seen_thread_ids:
                raise AdapterValidationError("duplicate thread.started event")
            seen_thread_ids.add(thread_id)
            normalized_event = {
                "type": event_type,
                "thread_id_hash": hash_text(thread_id),
            }
            profile = event.get("permissions_profile")
            if isinstance(profile, str):
                normalized_event["permissions_profile_hash"] = hash_text(profile)
                permissions_profile = True
        elif event_type in _ITEM_EVENT_TYPES:
            item = event.get("item")
            if not isinstance(item, dict):
                raise AdapterValidationError(f"{event_type} requires an item object")
            item_id = require_string(item, "id", event_type)
            if event_type in {"item.started", "item.completed"}:
                duplicate_key = (event_type, item_id)
                if duplicate_key in seen_terminal_items:
                    raise AdapterValidationError(
                        f"duplicate {event_type} event for one item identifier"
                    )
                seen_terminal_items.add(duplicate_key)
            normalized_event = _normalize_item_event(event_type, item)
            if normalized_event["item_type"] in _ACTIVITY_ITEM_TYPES:
                observed_activity = True
        elif event_type == "turn.completed":
            normalized_event = {"type": event_type}
            usage = event.get("usage")
            if isinstance(usage, dict):
                normalized_usage = safe_usage(usage)
                if normalized_usage:
                    normalized_event["usage"] = normalized_usage
        elif event_type in {"turn.failed", "error"}:
            normalized_event = {"type": event_type}
            error_value = event.get("error", event.get("message"))
            if error_value is not None:
                normalized_event["error_hash"] = sha256_uri(error_value)
        elif event_type in {"session.configured", "session.catalog", "turn.configured"}:
            normalized_event = {"type": event_type}
            tools = _normalize_catalog(event.get("tools"))
            skills = _normalize_catalog(event.get("skills"))
            if tools is not None:
                normalized_event["tool_name_hashes"] = tools
                offered_tools = True
            if skills is not None:
                normalized_event["skill_name_hashes"] = skills
                offered_skills = True
            profile = event.get("permissions_profile", event.get("permissions"))
            if isinstance(profile, str):
                normalized_event["permissions_profile_hash"] = hash_text(profile)
                permissions_profile = True
            model = event.get("model")
            if isinstance(model, str):
                normalized_event["model_hash"] = hash_text(model)
        else:
            normalized_event = {"type": event_type}

        normalized.append(normalized_event)
        accepted += 1

    document = {
        "schema_version": "codex-exec-evidence/v0.1",
        "runtime": "codex",
        "run_id_hash": hash_text(context.run_id),
        "created_at": context.created_at,
        "events": normalized,
    }
    facts = {
        "accepted": accepted,
        "ignored": ignored,
        "observed_activity": observed_activity,
        "offered_tools": offered_tools,
        "offered_skills": offered_skills,
        "permissions_profile": permissions_profile,
    }
    return document, facts


def _normalize_item_event(event_type: str, item: dict[str, Any]) -> dict[str, Any]:
    item_id = require_string(item, "id", event_type)
    item_type = require_string(item, "type", event_type)
    normalized: dict[str, Any] = {
        "type": event_type,
        "item_id_hash": hash_text(item_id),
        "item_type": safe_token_or_hash(item_type),
    }
    status = item.get("status")
    if isinstance(status, str):
        normalized["status"] = safe_token_or_hash(status)

    if item_type == "command_execution":
        if "command" in item:
            normalized["command_hash"] = sha256_uri(item["command"])
        output = item.get("aggregated_output", item.get("output"))
        if output is not None:
            normalized["output_hash"] = sha256_uri(output)
        exit_code = item.get("exit_code")
        if isinstance(exit_code, int) and not isinstance(exit_code, bool):
            normalized["exit_code"] = exit_code
    elif item_type == "file_change":
        changes = item.get("changes")
        if isinstance(changes, list):
            normalized_changes: list[dict[str, str]] = []
            for change in changes:
                if not isinstance(change, dict):
                    raise AdapterValidationError("file_change entries must be objects")
                path = require_string(change, "path", "file_change")
                normalized_change = {"path_hash": hash_text(path)}
                kind = change.get("kind")
                if isinstance(kind, str):
                    normalized_change["kind"] = safe_token_or_hash(kind)
                normalized_changes.append(normalized_change)
            normalized["changes"] = normalized_changes
        else:
            normalized["change_payload_hash"] = sha256_uri(item)
    elif item_type == "mcp_tool_call":
        server = item.get("server", item.get("server_name"))
        tool = item.get("tool", item.get("tool_name"))
        if isinstance(server, str):
            normalized["server_name_hash"] = hash_text(server)
        if isinstance(tool, str):
            normalized["tool_name_hash"] = hash_text(tool)
        if "arguments" in item:
            normalized["arguments_hash"] = sha256_uri(item["arguments"])
        if "result" in item:
            normalized["result_hash"] = sha256_uri(item["result"])
    elif item_type == "web_search":
        query = item.get("query")
        if query is not None:
            normalized["query_hash"] = sha256_uri(query)
    else:
        normalized["item_payload_hash"] = sha256_uri(item)
    return normalized


def _normalize_catalog(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    names: list[str] = []
    for entry in value:
        if isinstance(entry, str):
            name = entry
        elif isinstance(entry, dict) and isinstance(entry.get("name"), str):
            name = entry["name"]
        else:
            raise AdapterValidationError("catalog entries must be names or objects with a name")
        names.append(hash_text(name))
    return sorted(set(names))
