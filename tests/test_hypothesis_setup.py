from __future__ import annotations

import os
import secrets
import sys
import unittest

from hypothesis import __version__, is_hypothesis_test, seed, settings

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


def replay_seed() -> int:
    """Choose a fresh run seed unless the caller supplies a recorded decimal seed."""

    value = os.getenv("PAR_HYPOTHESIS_SEED")
    if value is None:
        return secrets.randbits(128)
    if not value.isascii() or not value.isdecimal():
        raise ValueError("PAR_HYPOTHESIS_SEED must be a non-negative decimal integer")
    return int(value)


RUN_SEED = replay_seed()
print(
    f"Property replay: PAR_HYPOTHESIS_SEED={RUN_SEED}; "
    f"HYPOTHESIS_PROFILE={ACTIVE_PROFILE}; Hypothesis {__version__}",
    file=sys.stderr,
)


def seeded_properties(cls: type[unittest.TestCase]) -> type[unittest.TestCase]:
    """Seed generated methods after all native Hypothesis decorators are applied."""

    for name, method in vars(cls).items():
        if is_hypothesis_test(method):
            setattr(cls, name, seed(RUN_SEED)(method))
    return cls


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
