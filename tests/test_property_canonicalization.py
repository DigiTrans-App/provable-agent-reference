from __future__ import annotations

import hashlib
import json
import math
import random
import unittest
from decimal import Decimal

from hypothesis import assume, example, given
from hypothesis import strategies as st
from test_hypothesis_setup import ACTIVE_PROFILE  # noqa: F401
from test_property_strategies import JSON_SCALARS, JSON_VALUES, case_label

from provable_agent_reference.canonical import canonical_json, sha256_uri

# Numeric values at the edges of the documented Python canonical JSON contract. The core
# serializer accepts any finite float and any integer; integers beyond +/-(2**53 - 1) are
# Python-only and are rejected separately by the DSSE interoperability profile.
NUMERIC_BOUNDARIES = (
    0,
    -1,
    (2**53) - 1,
    -((2**53) - 1),
    2**53,
    2**63,
    -(2**63),
    0.0,
    -0.0,
    5e-324,
    -5e-324,
    2.2250738585072014e-308,
    1.7976931348623157e308,
    -1.7976931348623157e308,
    0.1,
    1e16,
)
NON_FINITE = (float("nan"), float("inf"), float("-inf"))
UNSUPPORTED_VALUES = (
    {1, 2},
    frozenset({1}),
    Decimal("1.5"),
    b"bytes",
    bytearray(b"bytes"),
    complex(1, 2),
    object(),
)
# Non-string keys that the serializer used to convert, with their string counterparts.
COERCED_KEYS = ((1, "1"), (True, "true"), (None, "null"), (1.5, "1.5"))
KEY_MESSAGE = "canonical JSON object keys must be strings"
LONE_SURROGATES = ("\ud800", "\udbff", "\udc00", "\udfff")


def strict_equal(left: object, right: object) -> bool:
    """Compare JSON-compatible values without Python's cross-type equality.

    ``True == 1 == 1.0`` and ``0.0 == -0.0`` in Python, but each has a distinct canonical
    representation. Floats are compared by their shortest round-trip representation.
    """

    if type(left) is not type(right):
        return False
    if isinstance(left, float):
        return repr(left) == repr(right)
    if isinstance(left, list):
        return len(left) == len(right) and all(  # type: ignore[arg-type]
            strict_equal(a, b) for a, b in zip(left, right, strict=True)  # type: ignore[arg-type]
        )
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(  # type: ignore[union-attr]
            strict_equal(left[key], right[key]) for key in left  # type: ignore[index]
        )
    return left == right


def reorder_mappings(value: object, rng: random.Random) -> object:
    """Return an equal value whose mappings, at every depth, use a shuffled insertion order."""

    if isinstance(value, dict):
        keys = list(value)
        rng.shuffle(keys)
        return {key: reorder_mappings(value[key], rng) for key in keys}
    if isinstance(value, list):
        return [reorder_mappings(item, rng) for item in value]
    return value


class CanonicalizationPropertyTests(unittest.TestCase):
    @example({})
    @example([])
    @example({"nested": [{}, []]})
    @example({"": None, "a": [True, False, 0, -0.0, ""]})
    @given(JSON_VALUES)
    def test_canonical_form_round_trips_and_is_a_fixed_point(self, value: object) -> None:
        encoded = canonical_json(value)
        decoded = json.loads(encoded)

        # Round trip: parsing the canonical text recovers the same typed value.
        self.assertTrue(strict_equal(decoded, value), (value, decoded))
        # Fixed point: canonicalizing the parsed value reproduces the same bytes.
        self.assertEqual(canonical_json(decoded), encoded)
        # The digest is exactly SHA-256 over the canonical UTF-8 bytes.
        expected_digest = "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        self.assertEqual(sha256_uri(value), expected_digest)
        self.assertEqual(sha256_uri(encoded.encode("utf-8")), expected_digest)

    @given(JSON_VALUES, st.randoms(use_true_random=False))
    def test_mapping_insertion_order_at_any_depth_does_not_change_digest(
        self,
        value: object,
        rng: random.Random,
    ) -> None:
        reordered = reorder_mappings(value, rng)

        self.assertEqual(canonical_json(reordered), canonical_json(value))
        self.assertEqual(sha256_uri(reordered), sha256_uri(value))

    @given(
        st.lists(
            st.tuples(st.text(min_size=1, max_size=20), JSON_VALUES),
            min_size=2,
            max_size=8,
            unique_by=lambda item: item[0],
        )
    )
    def test_reversed_top_level_insertion_order_does_not_change_digest(
        self,
        entries: list[tuple[str, object]],
    ) -> None:
        forward = dict(entries)
        reverse = dict(reversed(entries))

        self.assertEqual(list(forward), [key for key, _ in entries])
        self.assertEqual(canonical_json(forward), canonical_json(reverse))
        self.assertEqual(sha256_uri(forward), sha256_uri(reverse))

    @given(st.lists(JSON_VALUES, min_size=2, max_size=6), st.randoms(use_true_random=False))
    def test_list_order_remains_hash_bound(
        self,
        items: list[object],
        rng: random.Random,
    ) -> None:
        permuted = list(items)
        rng.shuffle(permuted)
        same_sequence = [canonical_json(item) for item in permuted] == [
            canonical_json(item) for item in items
        ]

        if same_sequence:
            self.assertEqual(sha256_uri(permuted), sha256_uri(items))
        else:
            self.assertNotEqual(canonical_json(permuted), canonical_json(items))
            self.assertNotEqual(sha256_uri(permuted), sha256_uri(items))

    @given(JSON_VALUES, JSON_VALUES)
    def test_swapping_two_distinct_list_elements_changes_digest(
        self,
        left: object,
        right: object,
    ) -> None:
        assume(canonical_json(left) != canonical_json(right))

        self.assertNotEqual(sha256_uri([left, right]), sha256_uri([right, left]))

    @given(JSON_SCALARS, JSON_SCALARS)
    def test_scalars_share_a_canonical_form_only_when_type_and_value_match(
        self,
        left: object,
        right: object,
    ) -> None:
        self.assertEqual(
            canonical_json(left) == canonical_json(right),
            strict_equal(left, right),
        )

    def test_distinct_scalar_types_have_distinct_canonical_forms(self) -> None:
        values = (None, False, True, 0, 0.0, -0.0, 1, 1.0, "0", "1", "", "null", "true")
        canonical = [canonical_json(value) for value in values]

        self.assertEqual(len(canonical), len(set(canonical)))

    def test_numeric_boundaries_round_trip_with_type_and_sign(self) -> None:
        for value in NUMERIC_BOUNDARIES:
            with self.subTest(value=value):
                decoded = json.loads(canonical_json(value))
                self.assertTrue(strict_equal(decoded, value), (value, decoded))
                self.assertEqual(canonical_json([value]), "[" + canonical_json(value) + "]")

    @example("")
    @example("\u0000")
    @example("\u001f\u007f")
    @example("\u2028\u2029")
    @example("€")
    @example("𝄞")
    @example("line\nquote\"slash\\")
    @example("e\u0301")
    @given(st.text(alphabet=st.characters(exclude_categories=("Cs",)), max_size=80))
    def test_unicode_and_escaping_round_trip_exactly(self, value: str) -> None:
        encoded = canonical_json({value: value})

        self.assertEqual(json.loads(encoded), {value: value})
        # Control characters are always escaped; other code points are emitted as UTF-8.
        self.assertFalse(any(ord(character) < 0x20 for character in encoded))
        for character in value:
            if ord(character) >= 0x20 and character not in {'"', "\\"}:
                self.assertIn(character, encoded)
        self.assertEqual(
            sha256_uri({value: value}),
            "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        )

    def test_unicode_normalization_forms_remain_distinct(self) -> None:
        composed = "\u00e9"
        decomposed = "e\u0301"

        self.assertNotEqual(sha256_uri({"value": composed}), sha256_uri({"value": decomposed}))

    @given(JSON_VALUES)
    def test_non_finite_numbers_fail_before_hashing_at_any_position(
        self,
        baseline: object,
    ) -> None:
        sha256_uri({"value": baseline, "list": [baseline]})
        for value in NON_FINITE:
            for container in ({"value": value}, [baseline, value], {"n": [{"v": value}]}):
                with case_label(value=value, container=type(container).__name__):
                    self.assertFalse(math.isfinite(value))
                    with self.assertRaises(ValueError):
                        canonical_json(container)
                    with self.assertRaises(ValueError):
                        sha256_uri(container)

    @given(JSON_VALUES)
    def test_unsupported_values_fail_before_hashing_at_any_position(
        self,
        baseline: object,
    ) -> None:
        sha256_uri({"value": baseline, "list": [baseline]})
        for value in UNSUPPORTED_VALUES:
            for container in ({"value": value}, [baseline, value], {"n": [{"v": value}]}):
                with case_label(value=type(value).__name__):
                    with self.assertRaises(TypeError):
                        canonical_json(container)
                    with self.assertRaises(TypeError):
                        sha256_uri(container)

    def test_unpaired_surrogates_fail_at_the_hashing_boundary(self) -> None:
        sha256_uri({"value": "\U0001d11e"})
        for value in LONE_SURROGATES:
            for container in ({"value": value}, {value: "key"}, [value]):
                with self.subTest(value=ascii(value)):
                    with self.assertRaises(UnicodeEncodeError):
                        sha256_uri(container)

    @given(
        JSON_VALUES,
        st.lists(st.sampled_from(("dict", "list", "tuple")), max_size=6),
        st.dictionaries(st.text(max_size=10), JSON_SCALARS, max_size=4),
        st.integers(min_value=0, max_value=4),
    )
    def test_non_string_keys_are_rejected_at_any_depth_and_position(
        self,
        payload: object,
        wrappers: list[str],
        siblings: dict[str, object],
        position: int,
    ) -> None:
        def build(key: object) -> object:
            entries = list(siblings.items())
            entries.insert(min(position, len(entries)), (key, payload))
            value: object = dict(entries)
            for kind in wrappers:
                if kind == "dict":
                    value = {"w": value}
                elif kind == "list":
                    value = [value]
                else:
                    value = (value,)
            return value

        # Every coerced key category is checked in each example, after a valid baseline.
        for key, counterpart in COERCED_KEYS:
            with case_label(key=repr(key), depth=len(wrappers), position=position):
                baseline = build(counterpart)
                self.assertEqual(
                    canonical_json(baseline),
                    json.dumps(
                        baseline,
                        allow_nan=False,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                )
                invalid = build(key)
                with self.assertRaisesRegex(TypeError, KEY_MESSAGE):
                    canonical_json(invalid)
                with self.assertRaisesRegex(TypeError, KEY_MESSAGE):
                    sha256_uri(invalid)


if __name__ == "__main__":
    unittest.main()
