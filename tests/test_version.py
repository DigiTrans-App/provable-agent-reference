from __future__ import annotations

import unittest
from importlib.metadata import version

import provable_agent_reference


class VersionMetadataTests(unittest.TestCase):
    def test_runtime_version_matches_distribution_metadata(self) -> None:
        self.assertEqual(
            provable_agent_reference.__version__,
            version("provable-agent-reference"),
        )


if __name__ == "__main__":
    unittest.main()
