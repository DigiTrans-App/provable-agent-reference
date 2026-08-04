from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.external_validation import runner


class ExternalValidationTests(unittest.TestCase):
    def test_sanitize_text_redacts_paths_and_secret_like_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            raw = (
                f"{repository}/fixture "
                f"sk-proj-{'A' * 24} "
                f"AKIA{'B' * 16} "
                f"ghp_{'C' * 24} "
                "Bearer abcdefghijklmnopqrstuvwxyz "
                "password=correct-horse-battery-staple "
                "-----BEGIN PRIVATE KEY-----\nsynthetic\n-----END PRIVATE KEY-----"
            )

            sanitized = runner.sanitize_text(raw, repository)

            self.assertIn("$REPOSITORY_ROOT/fixture", sanitized)
            self.assertNotIn("sk-proj-", sanitized)
            self.assertNotIn("AKIA", sanitized)
            self.assertNotIn("ghp_", sanitized)
            self.assertNotIn("correct-horse", sanitized)
            self.assertNotIn("BEGIN PRIVATE KEY", sanitized)
            self.assertGreaterEqual(sanitized.count("<redacted>"), 6)

    def test_parse_sha256sums_rejects_unsafe_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "SHA256SUMS"
            path.write_text(f"{'0' * 64}  ../artifact.whl\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unsafe"):
                runner.parse_sha256sums(path)

    def test_archive_path_safety_rejects_traversal_and_drive_paths(self) -> None:
        self.assertFalse(runner.is_unsafe_archive_path("package/module.py"))
        self.assertTrue(runner.is_unsafe_archive_path("../module.py"))
        self.assertTrue(runner.is_unsafe_archive_path("/absolute/module.py"))
        self.assertTrue(runner.is_unsafe_archive_path("C:\\absolute\\module.py"))

    def test_run_command_validates_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = runner.run_command(
                name="json_check",
                command=[
                    sys.executable,
                    "-c",
                    'print(\'{"passed": true, "case_count": 1}\')',
                ],
                repository_root=Path(temporary),
                timeout_seconds=10,
                max_output_chars=1000,
                json_validator=runner.validate_evaluation_result,
            )

            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["command"][0], "$PYTHON")
            self.assertEqual(result["structured_output"]["case_count"], 1)

    def test_run_command_fails_when_json_contract_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = runner.run_command(
                name="json_check",
                command=[sys.executable, "-c", "print('not-json')"],
                repository_root=Path(temporary),
                timeout_seconds=10,
                max_output_chars=1000,
                json_validator=runner.validate_json_object,
            )

            self.assertEqual(result["status"], "fail")
            self.assertIn("validation_error", result)

    def test_collect_git_provenance_verifies_annotated_tag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            self._git(repository, "init")
            self._git(repository, "config", "user.name", "Validation Test")
            self._git(repository, "config", "user.email", "validation@example.invalid")
            (repository / "README.md").write_text("synthetic\n", encoding="utf-8")
            self._git(repository, "add", "README.md")
            self._git(repository, "commit", "-m", "test fixture")
            self._git(
                repository,
                "tag",
                "-a",
                "v0.2.0",
                "-m",
                "Synthetic v0.2.0",
            )
            head = self._git(repository, "rev-parse", "HEAD")

            result = runner.collect_git_provenance(
                repository,
                expected_tag="v0.2.0",
                expected_commit=head,
                allow_dirty=False,
            )

            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["tag"]["object_type"], "tag")
            self.assertEqual(result["tag"]["peeled_commit_sha"], head)
            self.assertFalse(result["dirty"])

    def test_verify_release_artifacts_accepts_valid_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release_dir = Path(temporary)
            self._write_release_fixture(release_dir)

            result = runner.verify_release_artifacts(
                release_dir,
                expected_project="provable-agent-reference",
                expected_version="0.2.0",
                required=True,
            )

            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["project"], "provable-agent-reference")
            self.assertEqual(len(result["files"]), 3)

    def test_verify_release_artifacts_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release_dir = Path(temporary)
            wheel = self._write_release_fixture(release_dir)
            with wheel.open("ab") as stream:
                stream.write(b"tampered")

            result = runner.verify_release_artifacts(
                release_dir,
                expected_project="provable-agent-reference",
                expected_version="0.2.0",
                required=True,
            )

            self.assertEqual(result["status"], "fail")
            self.assertTrue(any("SHA-256 mismatch" in item for item in result["errors"]))

    def test_report_digest_is_stable_for_identical_content(self) -> None:
        first = {"status": "pass", "checks": [{"name": "synthetic"}]}
        second = {"checks": [{"name": "synthetic"}], "status": "pass"}

        self.assertEqual(runner.report_digest(first), runner.report_digest(second))
        second["status"] = "fail"
        self.assertNotEqual(runner.report_digest(first), runner.report_digest(second))

    @staticmethod
    def _git(repository: Path, *arguments: str) -> str:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return completed.stdout.strip()

    @staticmethod
    def _write_release_fixture(release_dir: Path) -> Path:
        project = "provable-agent-reference"
        distribution = "provable_agent_reference"
        version = "0.2.0"
        wheel = release_dir / f"{distribution}-{version}-py3-none-any.whl"
        source = release_dir / f"{distribution}-{version}.tar.gz"

        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(f"{distribution}/__init__.py", '__version__ = "0.2.0"\n')
            archive.writestr(
                f"{distribution}-{version}.dist-info/METADATA",
                "Metadata-Version: 2.4\n"
                f"Name: {project}\n"
                f"Version: {version}\n",
            )

        root = f"{distribution}-{version}"
        with tarfile.open(source, "w:gz") as archive:
            entries = {
                f"{root}/LICENSE": b"Apache-2.0\n",
                f"{root}/README.md": b"Synthetic release fixture.\n",
                f"{root}/pyproject.toml": b"[project]\nname='fixture'\n",
                f"{root}/src/{distribution}/__init__.py": b'__version__ = "0.2.0"\n',
            }
            for name, content in entries.items():
                info = tarfile.TarInfo(name)
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))

        manifest = {
            "project": project,
            "version": version,
            "artifacts": [
                {
                    "filename": wheel.name,
                    "sha256": runner.sha256_file(wheel),
                    "size_bytes": wheel.stat().st_size,
                },
                {
                    "filename": source.name,
                    "sha256": runner.sha256_file(source),
                    "size_bytes": source.stat().st_size,
                },
            ],
        }
        manifest_path = release_dir / "ARTIFACTS.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        checksums = release_dir / "SHA256SUMS"
        checksums.write_text(
            "\n".join(
                f"{runner.sha256_file(path)}  {path.name}"
                for path in (wheel, source, manifest_path)
            )
            + "\n",
            encoding="utf-8",
        )
        return wheel


if __name__ == "__main__":
    unittest.main()
