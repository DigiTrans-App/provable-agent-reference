"""Distribution validation tests.

Synthetic archives exercise ``scripts/validate_dist.py``. One test builds a real
source distribution from a temporary copy of the tree with setuptools, offline, to
prove MANIFEST.in ships everything the bundled tests need.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import validate_dist
from scripts.validate_dist import (
    ROOT,
    SDIST_SUPPORT_PATHS,
    required_sdist_paths,
    validate_sdist,
    validate_wheel,
)

NAME = "provable-agent-reference"
STEM = "provable_agent_reference"
VERSION = "9.9.9"
MODULES = {
    "provable_agent_reference/__init__.py",
    "provable_agent_reference/core.py",
}
REQUIRED = {
    "tests/helpers.py",
    "tests/test_example.py",
    "scripts/verify_release.py",
}
COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    ".hypothesis",
    ".ruff_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "*.egg-info",
    "*.pyc",
    "build",
    "dist",
    "node_modules",
    "validation-results",
)


def write_sdist(path: Path, members: set[str]) -> Path:
    root = f"{STEM}-{VERSION}"
    with tarfile.open(path, mode="w:gz") as archive:
        for member in sorted(members):
            data = b"x\n"
            info = tarfile.TarInfo(f"{root}/{member}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return path


def base_sdist_members() -> set[str]:
    return {
        "LICENSE",
        "README.md",
        "pyproject.toml",
        "src/provable_agent_reference/__init__.py",
    }


def write_wheel(path: Path, modules: set[str], extra: set[str] = frozenset()) -> Path:
    metadata = f"Metadata-Version: 2.4\nName: {NAME}\nVersion: {VERSION}\n"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{STEM}-{VERSION}.dist-info/METADATA", metadata)
        for module in sorted(modules | extra):
            archive.writestr(module, "x = 1\n")
    return path


class SdistValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def sdist(self, members: set[str]) -> Path:
        return write_sdist(self.directory / "example.tar.gz", members)

    def test_complete_sdist_is_accepted(self) -> None:
        path = self.sdist(base_sdist_members() | REQUIRED)
        validate_sdist(path, STEM, VERSION, REQUIRED)

    def test_missing_helpers_module_is_rejected(self) -> None:
        path = self.sdist(base_sdist_members() | (REQUIRED - {"tests/helpers.py"}))
        with self.assertRaisesRegex(RuntimeError, "tests/helpers.py"):
            validate_sdist(path, STEM, VERSION, REQUIRED)

    def test_original_four_member_check_is_kept(self) -> None:
        path = self.sdist((base_sdist_members() - {"LICENSE"}) | REQUIRED)
        with self.assertRaisesRegex(RuntimeError, "LICENSE"):
            validate_sdist(path, STEM, VERSION, REQUIRED)

    def test_bytecode_in_sdist_is_rejected(self) -> None:
        for extra in ("tests/__pycache__/helpers.cpython-312.pyc", "tests/stale.pyc"):
            with self.subTest(extra=extra):
                path = self.sdist(base_sdist_members() | REQUIRED | {extra})
                with self.assertRaisesRegex(RuntimeError, "bytecode"):
                    validate_sdist(path, STEM, VERSION, REQUIRED)


class WheelValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "example.whl"

    def test_wheel_with_every_module_is_accepted(self) -> None:
        write_wheel(self.path, MODULES)
        validate_wheel(self.path, NAME, VERSION, MODULES)

    def test_wheel_missing_a_module_is_rejected(self) -> None:
        write_wheel(self.path, MODULES - {"provable_agent_reference/core.py"})
        with self.assertRaisesRegex(RuntimeError, "core.py"):
            validate_wheel(self.path, NAME, VERSION, MODULES)

    def test_bytecode_in_wheel_is_rejected(self) -> None:
        write_wheel(self.path, MODULES, {"provable_agent_reference/__pycache__/core.pyc"})
        with self.assertRaisesRegex(RuntimeError, "bytecode"):
            validate_wheel(self.path, NAME, VERSION, MODULES)


class RequiredPathTests(unittest.TestCase):
    def test_required_paths_cover_tests_and_package_modules(self) -> None:
        project_version = validate_dist.project_metadata()[1]
        required = required_sdist_paths(project_version)
        self.assertIn("tests/helpers.py", required)
        for path in (ROOT / "tests").glob("*.py"):
            self.assertIn(f"tests/{path.name}", required)
        for module in validate_dist.package_modules():
            self.assertIn(f"src/{module}", required)
        self.assertIn(f"docs/releases/v{project_version}.md", required)

    def test_support_paths_exist_in_the_tree(self) -> None:
        for relative in SDIST_SUPPORT_PATHS:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file())


class ManifestCoverageTests(unittest.TestCase):
    def test_built_sdist_contains_every_required_file(self) -> None:
        project_version = validate_dist.project_metadata()[1]
        with tempfile.TemporaryDirectory() as scratch_name:
            scratch = Path(scratch_name)
            tree = scratch / "tree"
            shutil.copytree(ROOT, tree, ignore=COPY_IGNORE)
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from setuptools import setup; setup()",
                    "-q",
                    "sdist",
                    "--formats=gztar",
                    "--dist-dir",
                    str(scratch / "out"),
                ],
                cwd=tree,
                capture_output=True,
                text=True,
                check=False,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertNotIn("no files found matching", output)
            self.assertNotIn("no directories found matching", output)

            archive_path = scratch / "out" / f"{STEM}-{project_version}.tar.gz"
            with tarfile.open(archive_path, mode="r:gz") as archive:
                names = set(archive.getnames())
            prefix = f"{STEM}-{project_version}/"

            # The same validation release.yml applies to the real artifact.
            validate_sdist(
                archive_path, STEM, project_version, required_sdist_paths(project_version)
            )

            # A support file added to tests/ must be covered by MANIFEST.in.
            for path in sorted((ROOT / "tests").rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                    relative = path.relative_to(ROOT).as_posix()
                    with self.subTest(path=relative):
                        self.assertIn(prefix + relative, names)


if __name__ == "__main__":
    unittest.main()
