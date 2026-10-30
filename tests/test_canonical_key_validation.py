from __future__ import annotations

import copy
import enum
import hashlib
import json
import sys
import threading
import unittest
from decimal import Decimal

from helpers import bundle, context, draft

from provable_agent_reference import ProvableAgentPipeline, authorize_exact_use
from provable_agent_reference.canonical import canonical_json, sha256_uri
from provable_agent_reference.dsse import sign_assurance_packet

KEY_MESSAGE = "canonical JSON object keys must be strings"
# Each non-string key and the string it used to be converted to.
COERCED_KEYS = ((1, "1"), (True, "true"), (None, "null"), (1.5, "1.5"))


class Number(enum.IntEnum):
    ONE = 1


# Produced by the unfixed implementation at 8d1ed2917487d7df5c5ee5fda5632ffa37b4c274.
PINNED_FIXTURE = {
    "": 0,
    "a": -0.0,
    "b": 9007199254740992,
    "c": 1e308,
    "\u00e9": "\U0001d11e",
    "list": [1, 2.5, None, True, "x"],
    "tuple": (1, {"k": "v"}),
    "nested": {"z": {}, "y": []},
}
PINNED_CANONICAL = (
    '{"":0,"a":-0.0,"b":9007199254740992,"c":1e+308,"list":[1,2.5,null,true,"x"],'
    '"nested":{"y":[],"z":{}},"tuple":[1,{"k":"v"}],"\u00e9":"\U0001d11e"}'
)
PINNED_DIGEST = "sha256:17f708da53dc1f07c0f2a18e76bfdb601c2fa9139662c058d523de791f58d8cf"
PINNED_BYTES_DIGEST = "sha256:805813d5394c0c652c3acbaecdef1f121f5190c94c8b46428ea2440ae7348546"


def reference_json(value: object) -> str:
    # Independent of canonical_json: the stdlib serializer with the documented options.
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def placements(key: object) -> dict[str, object]:
    # Single-key maps, so an unrelated mixed-key sorting error cannot mask the defect.
    return {
        "root": {key: "x"},
        "dict": {"outer": {key: "x"}},
        "list": [{key: "x"}],
        "tuple": ({key: "x"},),
        "mixed": {"a": [({"b": {key: "x"}},)]},
        "deep": [[[{"a": ({key: "x"},)}]]],
    }


def finishes(function, value: object) -> BaseException | None:
    # Run in a daemon thread and fail the test if it does not finish promptly.
    outcome: list[BaseException | None] = []

    def target() -> None:
        try:
            function(value)
            outcome.append(None)
        except BaseException as error:  # noqa: BLE001 - the caller inspects the error
            outcome.append(error)

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(10)
    if worker.is_alive():
        raise AssertionError(f"{function.__name__} did not finish within 10 seconds")
    return outcome[0]


class CanonicalKeyValidationTests(unittest.TestCase):
    def test_coerced_key_types_are_rejected_at_every_position(self) -> None:
        for key, counterpart in COERCED_KEYS:
            valid = placements(counterpart)
            for name, value in placements(key).items():
                with self.subTest(key=repr(key), placement=name):
                    self.assertEqual(canonical_json(valid[name]), reference_json(valid[name]))
                    with self.assertRaisesRegex(TypeError, KEY_MESSAGE):
                        canonical_json(value)
                    with self.assertRaisesRegex(TypeError, KEY_MESSAGE):
                        sha256_uri(value)

    def test_integer_subclass_keys_are_rejected(self) -> None:
        for value in placements(Number.ONE).values():
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(TypeError, KEY_MESSAGE):
                    sha256_uri(value)

    def test_other_hashable_key_types_remain_rejected(self) -> None:
        for key in ((1, 2), frozenset({1}), b"k", Decimal("1"), complex(1, 2), object()):
            for name, value in placements(key).items():
                with self.subTest(key=type(key).__name__, placement=name):
                    with self.assertRaises(TypeError):
                        canonical_json(value)
                    with self.assertRaises(TypeError):
                        sha256_uri(value)

    def test_mixed_and_all_numeric_maps_cannot_bypass_validation(self) -> None:
        for key, _ in COERCED_KEYS:
            for value in ({"a": 1, key: "x"}, {key: "x", "z": 1}, [{"m": {"a": 1, key: "x"}}]):
                with self.subTest(key=repr(key), value=repr(value)):
                    with self.assertRaisesRegex(TypeError, KEY_MESSAGE):
                        sha256_uri(value)
        with self.assertRaisesRegex(TypeError, KEY_MESSAGE):
            sha256_uri({1: "a", 2: "b"})

    def test_rejection_does_not_depend_on_position_or_value(self) -> None:
        values = (None, [], {}, "x", 0, [{"ok": 1}], ({"ok": 1},))
        for key, _ in COERCED_KEYS:
            for item in values:
                for position in range(3):
                    entries = [("a", 1), ("m", 2)]
                    entries.insert(position, (key, item))
                    with self.subTest(key=repr(key), item=repr(item), position=position):
                        with self.assertRaisesRegex(TypeError, KEY_MESSAGE):
                            canonical_json(dict(entries))

    def test_shared_non_cyclic_containers_are_valid(self) -> None:
        child = {"k": [1, {"m": "n"}]}
        shared = {"a": child, "b": child, "c": [child, (child,)]}
        self.assertEqual(canonical_json(shared), reference_json(copy.deepcopy(shared)))

        level: object = {"leaf": 1}
        for _ in range(12):
            level = {"l": level, "r": [level]}
        self.assertEqual(canonical_json(level), reference_json(level))

        bad = {1: "x"}
        with self.assertRaisesRegex(TypeError, KEY_MESSAGE):
            canonical_json({"a": bad, "b": [bad]})

    def test_cycles_reject_without_hanging(self) -> None:
        direct_list: list[object] = []
        direct_list.append(direct_list)
        direct_dict: dict[str, object] = {}
        direct_dict["self"] = direct_dict
        indirect: list[object] = []
        indirect.append({"a": indirect})
        through_tuple: list[object] = []
        through_tuple.append((through_tuple,))
        for name, value in (
            ("list", direct_list),
            ("dict", direct_dict),
            ("indirect", indirect),
            ("tuple", through_tuple),
        ):
            for function in (canonical_json, sha256_uri):
                with self.subTest(cycle=name, function=function.__name__):
                    error = finishes(function, value)
                    self.assertIsInstance(error, ValueError)
                    self.assertIn("Circular reference", str(error))

        keyed: dict[object, object] = {}
        keyed[1] = keyed
        error = finishes(canonical_json, keyed)
        self.assertIsInstance(error, TypeError)
        self.assertIn(KEY_MESSAGE, str(error))

    def test_recursion_boundary_is_unchanged(self) -> None:
        moderate: object = "leaf"
        for _ in range(200):
            moderate = [{"k": moderate}]
        self.assertEqual(canonical_json(moderate), reference_json(moderate))

        # The validator must add no depth limit: at every depth, including past the point where
        # the stdlib serializer itself gives up, the outcome must match the plain serializer.
        # Whether and where the serializer raises depends on the interpreter, so compare parity.
        def outcome(function, value: object) -> object:
            try:
                return function(value)
            except RecursionError:
                return RecursionError

        limit = sys.getrecursionlimit()
        for depth in (limit * 2, limit * 20, 200_000):
            with self.subTest(depth=depth):
                deep: object = []
                for _ in range(depth):
                    deep = [deep]
                expected = outcome(reference_json, deep)
                self.assertEqual(outcome(canonical_json, deep), expected)
                expected_digest = (
                    RecursionError
                    if expected is RecursionError
                    else "sha256:" + hashlib.sha256(expected.encode("utf-8")).hexdigest()
                )
                self.assertEqual(outcome(sha256_uri, deep), expected_digest)
                del deep

    def test_pinned_bytes_tuples_and_boundaries_are_unchanged(self) -> None:
        canonical = canonical_json(PINNED_FIXTURE)
        self.assertEqual(canonical, PINNED_CANONICAL)
        self.assertEqual(sha256_uri(PINNED_FIXTURE), PINNED_DIGEST)
        self.assertEqual(
            PINNED_DIGEST, "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        )
        self.assertEqual(sha256_uri(b"provable-agent-reference"), PINNED_BYTES_DIGEST)
        with self.assertRaises(TypeError):
            canonical_json(b"provable-agent-reference")
        with self.assertRaises(ValueError):
            canonical_json({"a": float("nan")})
        with self.assertRaises(TypeError):
            canonical_json({"a": {1, 2}})

    def test_string_subclass_empty_and_unicode_keys_remain_valid(self) -> None:
        class Key(str):
            pass

        value = {Key("a"): 1, "": [], "\u00e9\U0001d11e": {"\u2028": None}}
        self.assertEqual(canonical_json(value), reference_json(value))

    def test_inputs_are_not_mutated(self) -> None:
        inputs = [PINNED_FIXTURE, *placements(1).values(), {"a": [(1, {"b": None})]}]
        for value in inputs:
            snapshot = copy.deepcopy(value)
            try:
                sha256_uri(value)
            except TypeError:
                pass
            with self.subTest(value=repr(snapshot)):
                self.assertEqual(repr(value), repr(snapshot))


class PublicConsumerKeyValidationTests(unittest.TestCase):
    def test_dsse_signing_rejects_coerced_keys(self) -> None:
        for key, counterpart in COERCED_KEYS:
            with self.subTest(key=repr(key)):
                envelope = sign_assurance_packet({"extension": {counterpart: "x"}})
                self.assertEqual(envelope["signatures"][0]["keyid"].split(":")[0], "development")
                with self.assertRaisesRegex(TypeError, KEY_MESSAGE):
                    sign_assurance_packet({"extension": {key: "x"}})

    def test_exact_use_authorization_rejects_coerced_output_keys(self) -> None:
        run_context = context()
        result = ProvableAgentPipeline().run(
            context=run_context,
            draft=draft(),
            evidence_bundle=bundle(run_context),
            approver_id="human_reviewer",
        )
        self.assertEqual((result.audit_valid, result.audit_errors), (True, ()))
        approved = {
            "assurance_statement": result.candidate.assurance_statement,
            "limitations": list(result.candidate.limitations),
        }
        for key, counterpart in COERCED_KEYS:
            with self.subTest(key=repr(key)):
                denied = authorize_exact_use(
                    candidate=result.candidate,
                    approval=result.approval,
                    purpose=run_context.purpose,
                    audience=run_context.audience,
                    output={**approved, counterpart: "x"},
                )
                self.assertEqual(denied.reason, "EXACT_USE_MISMATCH")
                with self.assertRaisesRegex(TypeError, KEY_MESSAGE):
                    authorize_exact_use(
                        candidate=result.candidate,
                        approval=result.approval,
                        purpose=run_context.purpose,
                        audience=run_context.audience,
                        output={**approved, key: "x"},
                    )


if __name__ == "__main__":
    unittest.main()
