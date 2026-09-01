from __future__ import annotations

import math
import unittest

from hypothesis import assume, example, given
from hypothesis import strategies as st
from test_hypothesis_setup import ACTIVE_PROFILE  # noqa: F401
from test_property_strategies import JSON_VALUES

from provable_agent_reference.canonical import canonical_json, sha256_uri


class CanonicalizationPropertyTests(unittest.TestCase):
    @example({})
    @example([])
    @example({"nested": [{}, []]})
    @given(JSON_VALUES)
    def test_repeated_serialization_and_hashing_are_stable(self, value: object) -> None:
        first = canonical_json(value)
        second = canonical_json(value)

        self.assertEqual(first, second)
        self.assertEqual(sha256_uri(value), sha256_uri(value))
        self.assertEqual(
            sha256_uri(first.encode("utf-8")),
            sha256_uri(second.encode("utf-8")),
        )

    @given(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=20),
                JSON_VALUES,
            ),
            min_size=1,
            max_size=8,
            unique_by=lambda item: item[0],
        )
    )
    def test_mapping_insertion_order_does_not_change_canonical_form(
        self,
        entries: list[tuple[str, object]],
    ) -> None:
        forward = dict(entries)
        reverse = dict(reversed(entries))

        self.assertEqual(canonical_json(forward), canonical_json(reverse))
        self.assertEqual(sha256_uri(forward), sha256_uri(reverse))

    @given(JSON_VALUES, JSON_VALUES)
    def test_list_order_remains_hash_bound(self, left: object, right: object) -> None:
        assume(canonical_json(left) != canonical_json(right))

        self.assertNotEqual(
            canonical_json([left, right]),
            canonical_json([right, left]),
        )
        self.assertNotEqual(sha256_uri([left, right]), sha256_uri([right, left]))

    @example("")
    @example("\u0000")
    @example("€")
    @example("𝄞")
    @example("line\nquote\"slash\\")
    @given(st.text(alphabet=st.characters(exclude_categories=("Cs",)), max_size=80))
    def test_unicode_and_escaping_round_trip_stably(self, value: str) -> None:
        encoded = canonical_json({"value": value})

        self.assertEqual(encoded, canonical_json({"value": value}))
        self.assertEqual(sha256_uri({"value": value}), sha256_uri({"value": value}))

    @given(st.sampled_from((float("nan"), float("inf"), float("-inf"))))
    def test_non_finite_numbers_fail_before_hashing(self, value: float) -> None:
        self.assertFalse(math.isfinite(value))
        with self.assertRaises(ValueError):
            canonical_json({"value": value})
        with self.assertRaises(ValueError):
            sha256_uri({"value": value})

    @given(
        st.one_of(
            st.sets(st.integers(), max_size=5),
            st.decimals(allow_nan=False, allow_infinity=False),
            st.binary(max_size=20),
        )
    )
    def test_unsupported_values_fail_before_hashing(self, value: object) -> None:
        with self.assertRaises(TypeError):
            canonical_json({"value": value})
        with self.assertRaises(TypeError):
            sha256_uri({"value": value})

    def test_distinct_scalar_types_have_distinct_canonical_forms(self) -> None:
        values = (None, False, True, 0, 0.0, -0.0, 1, 1.0, "0", "1")
        canonical = [canonical_json(value) for value in values]

        self.assertEqual(len(canonical), len(set(canonical)))

    def test_unpaired_surrogates_fail_before_hashing(self) -> None:
        with self.assertRaises(UnicodeEncodeError):
            sha256_uri({"value": "\ud800"})


if __name__ == "__main__":
    unittest.main()
