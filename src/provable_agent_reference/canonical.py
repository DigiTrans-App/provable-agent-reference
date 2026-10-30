from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from typing import Any

# Containers that ``json.dumps`` serializes as objects or arrays, including subclasses.
_CONTAINERS = (dict, list, tuple)


def _container_items(container: Any) -> Iterator[Any]:
    """Yield a container's values, rejecting any non-string object key first."""

    if isinstance(container, dict):
        for key, item in container.items():
            if not isinstance(key, str):
                raise TypeError(
                    "canonical JSON object keys must be strings, not " + type(key).__name__
                )
            yield item
    else:
        yield from container


def _require_string_keys(value: Any) -> None:
    """Reject non-string object keys at every depth before serialization.

    The standard serializer converts some non-string keys (integers, booleans, ``None`` and
    floats) to strings, so ``{1: "x"}`` and ``{"1": "x"}`` would otherwise produce the same
    canonical text and digest. The walk is iterative and adds no depth limit of its own.
    Containers on the current path are skipped so circular input still reaches the
    serializer's circular-reference check, and containers already checked are not revisited,
    so shared references cost one visit. The added cost is one pass over the reachable
    containers, without copying.
    """

    if not isinstance(value, _CONTAINERS):
        return
    active = {id(value)}
    checked: set[int] = set()
    stack = [(value, _container_items(value))]
    while stack:
        container, items = stack[-1]
        for item in items:
            if isinstance(item, _CONTAINERS):
                item_id = id(item)
                if item_id in active or item_id in checked:
                    continue
                active.add(item_id)
                stack.append((item, _container_items(item)))
                break
        else:
            stack.pop()
            active.discard(id(container))
            checked.add(id(container))


def canonical_json(value: Any) -> str:
    """Serialize a JSON-compatible value deterministically.

    Object keys must be ``str`` (including subclasses) at every depth. Any other key type raises
    ``TypeError`` instead of being converted to a string. Non-finite numbers raise
    ``ValueError`` and unsupported values raise ``TypeError``.
    """

    _require_string_keys(value)
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_uri(value: Any) -> str:
    """Return a stable sha256 URI for a JSON-compatible value or bytes.

    Non-bytes values are validated and serialized by :func:`canonical_json` and raise the same
    errors.
    """

    payload = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()
