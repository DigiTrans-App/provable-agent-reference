"""Static checks for artifact verification in the release and validation workflows."""

from __future__ import annotations

import re
import tempfile
import tomllib
import unittest
from pathlib import Path

from scripts.check_built_distributions import sdist_build_requirements

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CHECK_STEP = "Install and test built distributions"
CHECK_COMMAND = "python scripts/check_built_distributions.py"


def workflow_text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def step_names(text: str) -> list[str]:
    return re.findall(r"^      - name: (.+)$", text, flags=re.MULTILINE)


def step_block(text: str, step_name: str) -> str:
    match = re.search(
        rf"^      - name: {re.escape(step_name)}\n(.*?)(?=^      - name: |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, step_name
    return match.group(1)


class ReleaseArtifactVerificationTests(unittest.TestCase):
    def test_release_installs_and_tests_artifacts_before_attestation(self) -> None:
        text = workflow_text("release.yml")
        names = step_names(text)
        self.assertEqual(names.count(CHECK_STEP), 1)
        position = names.index(CHECK_STEP)
        self.assertGreater(position, names.index("Build distributions"))
        self.assertGreater(position, names.index("Validate distributions and generate manifests"))
        self.assertLess(position, names.index("Attest release artifacts"))
        self.assertLess(position, names.index("Publish GitHub release"))
        block = step_block(text, CHECK_STEP)
        self.assertIn(CHECK_COMMAND, block)
        self.assertNotIn("continue-on-error", block)
        self.assertNotIn("if:", block)

    def test_release_keeps_existing_gates_before_the_artifact_check(self) -> None:
        text = workflow_text("release.yml")
        names = step_names(text)
        position = names.index(CHECK_STEP)
        for earlier in (
            "Verify release source and metadata",
            "Run release validation",
            "Build distributions",
            "Validate distributions and generate manifests",
        ):
            self.assertLess(names.index(earlier), position, earlier)

    def test_validation_workflow_runs_the_same_check_after_building(self) -> None:
        text = workflow_text("validate.yml")
        names = step_names(text)
        self.assertEqual(names.count(CHECK_STEP), 1)
        self.assertGreater(names.index(CHECK_STEP), names.index("Build and validate distributions"))
        self.assertIn(CHECK_COMMAND, step_block(text, CHECK_STEP))
        self.assertIn("  validate:\n", text)
        self.assertIn('python-version: ["3.11", "3.12"]', text)

    def test_check_script_covers_wheel_sdist_and_bundled_tests(self) -> None:
        text = (REPO_ROOT / "scripts" / "check_built_distributions.py").read_text(encoding="utf-8")
        self.assertEqual(text.count('"-m", "venv"'), 1)
        for needle in ("pip", "install", "unittest", "discover", "PYTHONPATH", "site-packages"):
            self.assertIn(needle, text)


class WorkflowActionTests(unittest.TestCase):
    # Pinning of every action is covered by test_release_lines.test_w04.
    def test_artifact_check_step_adds_no_action(self) -> None:
        for name in ("release.yml", "validate.yml"):
            self.assertNotIn("uses:", step_block(workflow_text(name), CHECK_STEP))


class SdistBuildRequirementTests(unittest.TestCase):
    def test_reads_the_build_requirements_the_sdist_declares(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            tree = Path(name)
            (tree / "pyproject.toml").write_text(
                (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"), encoding="utf-8"
            )
            declared = tomllib.loads((tree / "pyproject.toml").read_text(encoding="utf-8"))
            requires = sdist_build_requirements(tree)
            self.assertEqual(requires, declared["build-system"]["requires"])
            self.assertTrue(any(item.startswith("setuptools") for item in requires))

    def test_missing_build_requirements_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            tree = Path(name)
            (tree / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "build-system"):
                sdist_build_requirements(tree)


if __name__ == "__main__":
    unittest.main()
