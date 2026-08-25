from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from typing import Any

from ..canonical import sha256_uri
from .base import AdapterValidationError

_MAX_EVENT_COUNT = 10_000
_MAX_LINE_BYTES = 262_144
_MAX_STREAM_BYTES = 64 * 1024 * 1024
_MAX_STRING_LENGTH = 32_768
_MAX_NESTING_DEPTH = 64
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.:/-]{1,128}$")
_USAGE_FIELDS = {
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
}
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{12,}"),
    re.compile(
        r"(?i)\b(?:authorization|api[_-]?key|password|secret|token)\s*[:=]\s*"
        r"[A-Za-z0-9+/_=.-]{12,}"
    ),
)


def parse_jsonl(stream_name: str, text: str) -> list[dict[str, Any]]:
    if len(text.encode("utf-8")) > _MAX_STREAM_BYTES:
        raise AdapterValidationError(
            f"{stream_name} exceeds {_MAX_STREAM_BYTES} bytes"
        )
    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        if len(raw_line.encode("utf-8")) > _MAX_LINE_BYTES:
            raise AdapterValidationError(
                f"{stream_name} line {line_number} exceeds {_MAX_LINE_BYTES} bytes"
            )
        try:
            event = json.loads(
                raw_line,
                parse_constant=_raise_non_finite,
                object_pairs_hook=_reject_duplicate_keys,
            )
        except (json.JSONDecodeError, AdapterValidationError) as exc:
            raise AdapterValidationError(
                f"{stream_name} line {line_number} is not valid JSON: {exc}"
            ) from exc
        if not isinstance(event, dict):
            raise AdapterValidationError(
                f"{stream_name} line {line_number} must contain a JSON object"
            )
        _validate_value(event, f"{stream_name} line {line_number}")
        events.append(event)
        if len(events) > _MAX_EVENT_COUNT:
            raise AdapterValidationError(
                f"{stream_name} contains more than {_MAX_EVENT_COUNT} events"
            )
    return events


def require_string(payload: Mapping[str, Any], key: str, event_name: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise AdapterValidationError(f"{event_name} requires a non-empty {key} string")
    return value


def safe_token_or_hash(value: str) -> str:
    if _SAFE_TOKEN.fullmatch(value):
        return value
    return "hashed-" + hash_text(value).removeprefix("sha256:")


def safe_usage(payload: Mapping[str, Any]) -> dict[str, int]:
    return {
        key: value
        for key, value in sorted(payload.items())
        if key in _USAGE_FIELDS
        and isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    }


def hash_text(value: str) -> str:
    return sha256_uri(value.encode("utf-8"))


def source_uri(kind: str, digest: str) -> str:
    return f"urn:codex:{kind}:{digest.removeprefix('sha256:')}"


def _raise_non_finite(value: str) -> None:
    raise AdapterValidationError(f"non-finite number {value!r} is not supported")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AdapterValidationError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _validate_value(value: Any, location: str, depth: int = 0) -> None:
    if depth > _MAX_NESTING_DEPTH:
        raise AdapterValidationError(
            f"{location} exceeds maximum nesting depth {_MAX_NESTING_DEPTH}"
        )
    if isinstance(value, str):
        if len(value) > _MAX_STRING_LENGTH:
            raise AdapterValidationError(
                f"{location} contains a string longer than {_MAX_STRING_LENGTH} characters"
            )
        for pattern in _SECRET_PATTERNS:
            if pattern.search(value):
                raise AdapterValidationError(
                    f"{location} contains credential-like material and was rejected"
                )
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise AdapterValidationError(f"{location} contains a non-string object key")
            _validate_value(child, location, depth + 1)
        return
    if isinstance(value, list):
        for child in value:
            _validate_value(child, location, depth + 1)
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AdapterValidationError(f"{location} contains a non-finite number")
        return
    if value is None or isinstance(value, (bool, int)):
        return
    raise AdapterValidationError(f"{location} contains an unsupported JSON value")
