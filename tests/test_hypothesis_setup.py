from __future__ import annotations

import os

from hypothesis import settings


def load_hypothesis_profile() -> str:
    """Register and load the bounded property-test profile selected by the caller."""

    settings.register_profile(
        "ci",
        max_examples=100,
        deadline=None,
        print_blob=True,
    )
    settings.register_profile(
        "extended",
        max_examples=1_000,
        deadline=None,
        print_blob=True,
    )
    profile = os.getenv("HYPOTHESIS_PROFILE", "ci")
    settings.load_profile(profile)
    return profile


ACTIVE_PROFILE = load_hypothesis_profile()
