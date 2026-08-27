from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.verify_release import (
    validate_release_ancestry,
    validate_release_metadata,
)


class ReleaseMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / "pyproject.toml").write_text(
            '[project]\nname = "example"\nversion = "1.2.3"\n',
            encoding="utf-8",
        )
        notes = self.root / "docs" / "releases"
        notes.mkdir(parents=True)
        (notes / "v1.2.3.md").write_text("# Release 1.2.3\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_matching_tag_and_notes_pass(self) -> None:
        validate_release_metadata(self.root, "v1.2.3")

    def test_mismatched_tag_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "tag/version mismatch"):
            validate_release_metadata(self.root, "v1.2.4")

    def test_missing_notes_fail_closed(self) -> None:
        (self.root / "docs" / "releases" / "v1.2.3.md").unlink()
        with self.assertRaisesRegex(RuntimeError, "release notes not found"):
            validate_release_metadata(self.root, "v1.2.3")


class ReleaseAncestryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary_directory.name)
        self._git("init", "--initial-branch=main")
        self._git("config", "user.name", "Release Test")
        self._git("config", "user.email", "release-test@example.invalid")
        (self.repo / "record.txt").write_text("main\n", encoding="utf-8")
        self._git("add", "record.txt")
        self._git("commit", "-m", "main commit")
        self.main_commit = self._git("rev-parse", "HEAD")

        self._git("switch", "-c", "side")
        (self.repo / "record.txt").write_text("side\n", encoding="utf-8")
        self._git("commit", "-am", "side commit")
        self.side_commit = self._git("rev-parse", "HEAD")
        self._git("switch", "main")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo,
            capture_output=True,
            check=True,
            text=True,
        )
        return result.stdout.strip()

    def test_main_commit_passes(self) -> None:
        validate_release_ancestry(
            self.repo, self.main_commit, "refs/heads/main"
        )

    def test_side_commit_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "is not contained"):
            validate_release_ancestry(
                self.repo, self.side_commit, "refs/heads/main"
            )


if __name__ == "__main__":
    unittest.main()
