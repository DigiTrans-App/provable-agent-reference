from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPLAY_PROBE = """
import json
import sys
import unittest
from hypothesis import example, given, settings, strategies as st
from test_hypothesis_setup import seeded_properties

draws = []

@seeded_properties
class ReplayProbe(unittest.TestCase):
    @settings(max_examples=30, deadline=None)
    @example(value=-1)
    @given(value=st.integers(min_value=0, max_value=1000))
    def test_failure(self, value):
        draws.append(value)
        self.assertLess(value, 20)

result = unittest.TextTestRunner(stream=sys.stdout).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(ReplayProbe)
)
print('DRAWN_SAMPLES=' + json.dumps(draws))
raise SystemExit(0 if result.wasSuccessful() else 1)
"""


class PropertyReproductionTests(unittest.TestCase):
    def run_probe(self, replay_seed: str | None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent))
        env.pop("PAR_HYPOTHESIS_SEED", None)
        if replay_seed is not None:
            env["PAR_HYPOTHESIS_SEED"] = replay_seed
        # Each attempt has a fresh directory, so replay cannot depend on a saved database.
        with tempfile.TemporaryDirectory() as directory:
            return subprocess.run(
                [sys.executable, "-c", REPLAY_PROBE],
                cwd=directory,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )

    def test_logged_seed_replays_a_minimized_failure_in_a_fresh_process(self) -> None:
        original = self.run_probe(None)
        self.assertEqual(original.returncode, 1, original.stdout + original.stderr)
        match = re.search(r"PAR_HYPOTHESIS_SEED=([0-9]+)", original.stderr)
        self.assertIsNotNone(match, original.stderr)
        replay = self.run_probe(match.group(1))
        self.assertEqual(replay.returncode, 1, replay.stdout + replay.stderr)
        traces = []
        for attempt in (original, replay):
            self.assertIn("value=20", attempt.stdout)
            self.assertIn("@reproduce_failure(", attempt.stdout)
            line = next(
                line for line in attempt.stdout.splitlines() if line.startswith("DRAWN_SAMPLES=")
            )
            trace = json.loads(line.removeprefix("DRAWN_SAMPLES="))
            self.assertEqual(trace[0], -1)  # Native explicit examples remain active.
            self.assertIn(20, trace)  # The failing example was minimized.
            traces.append(trace)
        self.assertEqual(traces[0], traces[1])

    def test_invalid_replay_seed_fails_instead_of_running_with_a_different_seed(self) -> None:
        result = self.run_probe("not-a-number")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PAR_HYPOTHESIS_SEED must be a non-negative decimal integer", result.stderr)
        self.assertNotIn("DRAWN_SAMPLES=", result.stdout)


if __name__ == "__main__":
    unittest.main()
