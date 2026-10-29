from __future__ import annotations

import os
import unittest

from hypothesis import settings

# Configured example limits. The guard tests below compare them with fixed agreed minimums,
# so lowering a configured limit fails those tests instead of lowering the expectation.
CI_MAX_EXAMPLES = 100
EXTENDED_MAX_EXAMPLES = 1_000


def load_hypothesis_profile() -> str:
    """Register and load the bounded property-test profile selected by the caller.

    An unknown ``HYPOTHESIS_PROFILE`` value raises ``InvalidArgument`` rather than silently
    falling back to a smaller profile.
    """

    settings.register_profile(
        "ci",
        max_examples=CI_MAX_EXAMPLES,
        deadline=None,
        print_blob=True,
    )
    settings.register_profile(
        "extended",
        max_examples=EXTENDED_MAX_EXAMPLES,
        deadline=None,
        print_blob=True,
    )
    profile = os.getenv("HYPOTHESIS_PROFILE", "ci")
    settings.load_profile(profile)
    return profile


ACTIVE_PROFILE = load_hypothesis_profile()


class HypothesisProfileTests(unittest.TestCase):
    # Agreed minimums, deliberately independent of the configured limits above.
    AGREED_CI_MINIMUM = 100
    AGREED_EXTENDED_MINIMUM = 1_000

    def test_registered_profiles_keep_their_example_floors(self) -> None:
        self.assertGreaterEqual(
            settings.get_profile("ci").max_examples, self.AGREED_CI_MINIMUM
        )
        self.assertGreaterEqual(
            settings.get_profile("extended").max_examples, self.AGREED_EXTENDED_MINIMUM
        )
        for name in ("ci", "extended"):
            with self.subTest(profile=name):
                profile = settings.get_profile(name)
                self.assertIsNone(profile.deadline)
                self.assertTrue(profile.print_blob)

    def test_active_profile_meets_the_ci_floor(self) -> None:
        self.assertIn(ACTIVE_PROFILE, {"ci", "extended"})
        self.assertGreaterEqual(settings().max_examples, self.AGREED_CI_MINIMUM)


if __name__ == "__main__":
    unittest.main()