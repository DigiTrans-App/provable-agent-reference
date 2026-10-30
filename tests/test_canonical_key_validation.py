from __future__ import annotations

import copy
import enum
import hashlib
import json
import math
import sys
import threading
import unittest
from decimal import Decimal

from helpers import bundle, context, draft

from provable_agent_reference import (
    ProvableAgentPipeline,
    authorize_exact_use,
    verify_audit_manifest,
)
from provable_agent_reference.canonical import canonical_json, sha256_uri

KEY_MESSAGE = "canonical JSON object keys must be strings"
# Each non-string key and the string it used to be converted to.
COERCED_KEYS = ((1, "1"), (True, "true"), (None, "null"), (1.5, "1.5"))
NON_FINITE = (float("nan"), float("inf"), float("-inf"))


class Number(enum.IntEnum):
    ONE = 1


# Produced by the unmodified v0.2.0 implementation (tag v0.2.0, commit 106b91e).
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
# Record hashes of the helpers pipeline fixture, produced by the unmodified v0.2.0 code.
PINNED_RECORD_HASHES = {
    "candidate": "sha256:0a0e5ab1440201eb83246802d692df8cce9b94268b535290013a2ec7ffc94cb9",
    "verification": "sha256:065d13f8d0be9e1d2ccc0135be6cb14e770fbd0e67f5a23719131e9a8d24231b",
    "approval": "sha256:850043fbefc45644b0898a2792becc4e9f37ad5971ce81758df9d902f77c1a02",
    "authorization": "sha256:fcd49d55d7efc0274c7c7b2905d4e61fb9933f57e24b1933c95d245138b611ea",
    "output": "sha256:b712c9f67e24e5f7a4cfd0e662e61d60f92ec8bdc63616842a4c3149fcdc14e0",
    "manifest": "sha256:7f95b6d699f1519eebdf1f3541a118d60de42f9d4916c09f3f1541b8f0462e0f",
    "bundle": "sha256:a2b0e68b5e2e03437bbb07310c0eb8f823fc36524e1ef7bfbe64baaac498ff0f",
}


def reference_json(value: object) -> str:
    # Independent of canonical_json: the stdlib serializer with the documented options.
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def placements(key: object, leaf: object = "x") -> dict[str, object]:
    # Single-key maps, so an unrelated mixed-key sorting error cannot mask the defect.
    return {
        "root": {key: leaf},
        "dict": {"outer": {key: leaf}},
        "list": [{key: leaf}],
        "tuple": ({key: leaf},),
        "mixed": {"a": [({"b": {key: leaf}},)]},
        "deep": [[[{"a": ({key: leaf},)}]]],
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


def run_pipeline():
    run_context = context()
    result = ProvableAgentPipeline().run(
        context=run_context,
        draft=draft(limitations=("First synthetic limitation.", "Second synthetic limitation.")),
        evidence_bundle=bundle(run_context),
        approver_id="human_reviewer",
    )
    return run_context, result


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
        for depth in (limit * 2, limit * 20):
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
        with self.assertRaises(TypeError):
            canonical_json({"a": {1, 2}})

    def test_non_finite_numbers_are_rejected_at_every_position(self) -> None:
        self.assertFalse(any(math.isfinite(n) for n in NON_FINITE))
        for number in NON_FINITE:
            for name, value in placements("k", number).items():
                with self.subTest(number=repr(number), placement=name):
                    with self.assertRaises(ValueError):
                        canonical_json(value)
                    with self.assertRaises(ValueError):
                        sha256_uri(value)
            with self.subTest(number=repr(number), placement="bare"):
                with self.assertRaises(ValueError):
                    canonical_json(number)

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
    def test_valid_record_hashes_are_identical_to_v0_2_0(self) -> None:
        run_context, result = run_pipeline()

        self.assertEqual(
            {
                "candidate": result.candidate.candidate_hash,
                "verification": result.verification.result_hash,
                "approval": result.approval.record_hash,
                "authorization": result.authorization.record_hash,
                "output": result.authorization.output_hash,
                "manifest": result.audit_manifest.manifest_hash,
                "bundle": bundle(run_context).bundle_hash,
            },
            PINNED_RECORD_HASHES,
        )
        self.assertEqual((result.audit_valid, result.audit_errors), (True, ()))
        self.assertEqual(
            verify_audit_manifest(
                manifest=result.audit_manifest,
                candidate=result.candidate,
                verification=result.verification,
                approval=result.approval,
                authorization=result.authorization,
            ),
            (True, ()),
        )

    def test_exact_use_authorization_rejects_coerced_output_keys(self) -> None:
        run_context, result = run_pipeline()
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

    def test_exact_use_authorization_rejects_non_finite_output_values(self) -> None:
        run_context, result = run_pipeline()
        approved = {
            "assurance_statement": result.candidate.assurance_statement,
            "limitations": list(result.candidate.limitations),
        }
        for number in NON_FINITE:
            with self.subTest(number=repr(number)):
                with self.assertRaises(ValueError):
                    authorize_exact_use(
                        candidate=result.candidate,
                        approval=result.approval,
                        purpose=run_context.purpose,
                        audience=run_context.audience,
                        output={**approved, "score": number},
                    )


if __name__ == "__main__":
    unittest.main()
