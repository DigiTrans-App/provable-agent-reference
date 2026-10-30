from __future__ import annotations

import hashlib
import json
import unittest
from contextlib import contextmanager
from typing import Any

from provable_agent_reference.control_plane.store import (
    PostgresStore,
    canonical_json,
    sha256_uri,
)


def legacy_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def legacy_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(legacy_json(value).encode("utf-8")).hexdigest()


def placements(value: Any) -> tuple[Any, ...]:
    return value, {"outer": value}, [value], (value,), {"outer": [(value,)]}


class SyntheticConnection:
    """Record attempted writes; do not pretend to implement PostgreSQL persistence."""

    def __init__(self) -> None:
        self.row: Any = None
        self.writes: list[tuple[str, Any]] = []

    def execute(self, query: str, params: Any) -> SyntheticConnection:
        if "SELECT tenant_id, case_id FROM runs" in query:
            self.row = ("tenant_1", "case_1")
        elif "SELECT sequence, record_hash FROM agent_activity_records" in query:
            self.row = None
        elif query.lstrip().startswith("INSERT"):
            self.writes.append((query, params))
        else:
            raise AssertionError(f"Unexpected query in synthetic connection: {query}")
        return self

    def fetchone(self) -> Any:
        return self.row


class SyntheticStore(PostgresStore):
    def __init__(self) -> None:
        super().__init__("unused-synthetic-connection")
        self.connection = SyntheticConnection()

    @contextmanager
    def transaction(self):
        yield self.connection


def legacy_activity(body: Any) -> dict[str, Any]:
    record = {
        "event_id": "activity_1",
        "tenant_id": "tenant_1",
        "case_id": "case_1",
        "run_id": "run_1",
        "sequence": 0,
        "previous_event_hash": None,
        "event_type": "synthetic.activity",
        "body": body,
        "body_hash": legacy_hash(body),
    }
    return {**record, "record_hash": legacy_hash(record)}


class StoreCanonicalizationTests(unittest.TestCase):
    def test_non_string_keys_are_rejected_by_both_store_helpers(self) -> None:
        for key in (1, True, None, 1.5):
            for value in placements({key: "x"}):
                for function in (canonical_json, sha256_uri):
                    with self.subTest(key_type=type(key).__name__, function=function.__name__):
                        with self.assertRaises(TypeError):
                            function(value)

    def test_non_finite_values_are_rejected_by_both_store_helpers(self) -> None:
        for number in (float("nan"), float("inf"), -float("inf")):
            for value in placements(number):
                for function in (canonical_json, sha256_uri):
                    with self.subTest(number=repr(number), function=function.__name__):
                        with self.assertRaises(ValueError):
                            function(value)

    def test_valid_values_keep_legacy_bytes_and_hashes(self) -> None:
        values = (
            None,
            True,
            0,
            -0.0,
            2**63,
            5e-324,
            1.7976931348623157e308,
            "\u00e9\U0001d11e",
            [],
            {},
            {"z": [1, {"a": "value"}], "a": (None, {"\u2028": -0.0})},
        )
        for value in values:
            with self.subTest(value=repr(value)):
                self.assertEqual(canonical_json(value), legacy_json(value))
                self.assertEqual(sha256_uri(value), legacy_hash(value))

    def test_store_hashing_does_not_gain_a_raw_bytes_path(self) -> None:
        with self.assertRaises(TypeError):
            sha256_uri(b"synthetic bytes")

    def test_valid_legacy_activity_hashes_still_reach_the_write_boundary(self) -> None:
        store = SyntheticStore()
        record = legacy_activity({"outer": {"1": "x"}, "count": 1.5})
        store.append_agent_activities([record])
        self.assertEqual(len(store.connection.writes), 2)
        _, params = store.connection.writes[0]
        self.assertEqual(params[7], legacy_json(record["body"]))
        self.assertEqual(params[8], record["body_hash"])
        self.assertEqual(params[9], legacy_json(record))
        self.assertEqual(params[10], record["record_hash"])

    def test_malformed_legacy_activity_is_rejected_before_any_write(self) -> None:
        cases = [("key", {"outer": {key: "x"}}, TypeError) for key in (1, True, None, 1.5)]
        cases += [
            ("number", {"outer": [value]}, ValueError)
            for value in (float("nan"), float("inf"), -float("inf"))
        ]
        for kind, body, error in cases:
            store = SyntheticStore()
            record = legacy_activity(body)
            with self.subTest(kind=kind, body=repr(body)):
                with self.assertRaises(error):
                    store.append_agent_activities([record])
                self.assertEqual(store.connection.writes, [])


if __name__ == "__main__":
    unittest.main()
