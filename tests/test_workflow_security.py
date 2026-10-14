from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.validate_repo import validate_workflow_security


class WorkflowSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.workflows = self.root / ".github" / "workflows"
        self.workflows.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_workflow(self, content: str) -> None:
        (self.workflows / "test.yml").write_text(content, encoding="utf-8")

    def test_pinned_actions_and_disabled_checkout_credentials_pass(self) -> None:
        sha = "a" * 40
        self.write_workflow(
            f"""name: test
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{sha}
        with:
          persist-credentials: false
      - uses: example/action/subpath@{sha}
      - uses: ./local-action
"""
        )
        self.assertEqual(validate_workflow_security(self.root), 2)

    def test_mutable_action_reference_fails_closed(self) -> None:
        self.write_workflow(
            """name: test
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: example/action@v1
"""
        )
        with self.assertRaisesRegex(RuntimeError, "not pinned"):
            validate_workflow_security(self.root)

    def test_pull_request_target_fails_closed(self) -> None:
        self.write_workflow(
            """name: test
on:
  pull_request_target:
jobs: {}
"""
        )
        with self.assertRaisesRegex(RuntimeError, "pull_request_target"):
            validate_workflow_security(self.root)

    def test_inline_pull_request_target_fails_closed(self) -> None:
        self.write_workflow(
            """name: test
on: [push, pull_request_target]
jobs: {}
"""
        )
        with self.assertRaisesRegex(RuntimeError, "pull_request_target"):
            validate_workflow_security(self.root)

    def test_quoted_inline_pull_request_target_fails_closed(self) -> None:
        self.write_workflow(
            """name: test
"on": [push, pull_request_target]
jobs: {}
"""
        )
        with self.assertRaisesRegex(RuntimeError, "pull_request_target"):
            validate_workflow_security(self.root)

    def test_checkout_must_disable_persisted_credentials(self) -> None:
        sha = "b" * 40
        self.write_workflow(
            f"""name: test
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{sha}
      - run: python scripts/check.py
"""
        )
        with self.assertRaisesRegex(RuntimeError, "persist-credentials"):
            validate_workflow_security(self.root)

    def test_checkout_input_must_belong_to_the_checkout_step(self) -> None:
        sha = "d" * 40
        self.write_workflow(
            f"""name: test
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{sha}
      - uses: example/action@{sha}
        with:
          persist-credentials: false
"""
        )
        with self.assertRaisesRegex(RuntimeError, "persist-credentials"):
            validate_workflow_security(self.root)

    def test_checkout_input_check_is_case_insensitive(self) -> None:
        sha = "c" * 40
        self.write_workflow(
            f"""name: test
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: Actions/Checkout@{sha}
        env:
          persist-credentials: false
"""
        )
        with self.assertRaisesRegex(RuntimeError, "persist-credentials"):
            validate_workflow_security(self.root)


if __name__ == "__main__":
    unittest.main()
