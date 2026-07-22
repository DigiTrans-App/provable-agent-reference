from __future__ import annotations

from typing import Any


def grade(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    actual = result.get("status")
    expected = case["expected"]
    return {
        "passed": actual == expected,
        "expected": expected,
        "actual": actual,
    }
