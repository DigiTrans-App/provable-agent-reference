"""Protected maintenance release line tests (accepted decision 0009).

Scenarios S01-S30 build real temporary git repositories (a local bare ``origin``
plus a working clone) and call the verifier. W01-W07 are static checks of the
workflow files. No network access is used.
"""

from __future__ import annotations

import copy
import fnmatch
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.verify_release import (
    ReleaseDecision,
    parse_release_lines,
    parse_tag,
    verify_release,
    write_github_output,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
DEFAULT = object()
MAIN_REF = "refs/remotes/origin/main"
REL_REF = "refs/remotes/origin/release/0.2.x"


def default_list(base: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "main_line": "0.3",
        "maintenance_lines": [
            {"line": "0.2", "branch": "release/0.2.x", "base_commit": base}
        ],
    }


def run_git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()



def base_files(
    version: str,
    tag: str,
    *,
    notes: bool = True,
    list_text: str | None = None,
) -> dict[str, str]:
    data = {"pyproject.toml": f'[project]\nname = "example"\nversion = "{version}"\n'}
    if notes:
        data[f"docs/releases/{tag}.md"] = "# notes\n"
    if list_text is not None:
        data[".github/release-lines.json"] = list_text
    return data


class FastImport:
    """Build a git fast-import stream (one git process instead of dozens)."""

    def __init__(self) -> None:
        self._parts: list[bytes] = []
        self._count = 0

    def commit(
        self,
        ref: str,
        parent: str | int | None,
        files: dict[str, str],
        message: str,
    ) -> int:
        self._count += 1
        mark = self._count
        body = message.encode()
        self._parts.append(
            (
                f"commit {ref}\nmark :{mark}\n"
                f"committer Release Test <release-test@example.invalid> "
                f"{1_700_000_000 + mark} +0000\ndata {len(body)}\n"
            ).encode()
            + body
            + b"\n"
        )
        if parent is not None:
            source = f":{parent}" if isinstance(parent, int) else parent
            self._parts.append(f"from {source}\n".encode())
        self._parts.append(b"deleteall\n")
        for path, content in files.items():
            raw = content.encode()
            self._parts.append(
                f"M 100644 inline {path}\ndata {len(raw)}\n".encode() + raw + b"\n"
            )
        self._parts.append(b"\n")
        return mark

    def tag(self, name: str, target: str | int) -> None:
        source = f":{target}" if isinstance(target, int) else target
        self._parts.append(f"reset refs/tags/{name}\nfrom {source}\n\n".encode())

    def data(self) -> bytes:
        return b"".join(self._parts)


class Fixture:
    """A bare origin and a working clone laid out per scenarios S01-S30."""

    def __init__(
        self,
        root: Path,
        *,
        tag: str = "v0.2.1",
        pyproject_version: str | None = None,
        notes: bool = True,
        main_list: Any = DEFAULT,
        tree_list: Any = DEFAULT,
        existing_tags: tuple[str, ...] = ("v0.2.0",),
        commit: str = "REL_TIP",
        branch_tip: str = "REL_TIP",
        checked_out: str | None = None,
        fetched_refs: tuple[str, ...] = (MAIN_REF, REL_REF),
    ) -> None:
        self.origin = root / "origin.git"
        self.work = root / "work"
        self.origin.mkdir()
        self.work.mkdir()
        run_git(self.origin, "init", "--bare", "--initial-branch=main")
        run_git(self.work, "init", "--initial-branch=main")
        run_git(self.work, "remote", "add", "origin", str(self.origin))

        self.tag = tag
        version = pyproject_version or tag[1:]
        marks_file = root / "marks.txt"

        # Phase 1: the base commit (the v0.2.0 stand-in) has no allow-list.
        stream = FastImport()
        stream.commit("refs/heads/base", None, base_files("0.2.0", "v0.2.0"), "base")
        self._import(stream, marks_file)
        self.base = run_git(self.work, "rev-parse", "refs/heads/base")

        main_text = self._render(main_list, default_list(self.base))
        tree_text = self._render(tree_list, default_list(self.base))

        def files(list_text: str | None, extra: str | None = None) -> dict[str, str]:
            data = base_files(version, tag, notes=notes, list_text=list_text)
            if extra is not None:
                data["touch.txt"] = extra
            return data

        # Phase 2: every other commit, written by a single git fast-import.
        stream = FastImport()
        r1 = stream.commit("refs/heads/rel", self.base, files(tree_text), "r1")
        r2 = stream.commit("refs/heads/rel", r1, files(tree_text, "rel\n"), "r2")
        side = stream.commit("refs/heads/side", r2, files(tree_text, "side\n"), "s")
        m1 = stream.commit("refs/heads/main", self.base, files(main_text), "m1")
        ms = stream.commit("refs/heads/mside", self.base, files(main_text, "ms\n"), "ms")
        legacy = stream.commit("refs/heads/legacy", None, files(tree_text), "legacy")
        unrelated = stream.commit(
            "refs/heads/unrelated", None, files(tree_text), "unrelated"
        )
        marks = {
            "REL_TIP": r2,
            "REL_TIP_MINUS_1": r1,
            "MAIN_TIP": m1,
            "MAIN_SIDE": ms,
            "SIDE": side,
            "LEGACY": legacy,
            "UNRELATED_TIP": unrelated,
        }
        for existing in existing_tags:
            stream.tag(existing, self.base)
        if tag not in existing_tags:
            stream.tag(tag, marks[commit])
        self._import(stream, marks_file)
        exported = dict(
            line.split()
            for line in marks_file.read_text(encoding="utf-8").splitlines()
        )
        self.shas = {name: exported[f":{mark}"] for name, mark in marks.items()}
        self.commit = self.shas[commit]

        run_git(
            self.work,
            "push",
            "origin",
            "main:refs/heads/main",
            f"{self.shas[branch_tip]}:refs/heads/release/0.2.x",
            "legacy:refs/heads/release/v0.2.0",
        )
        run_git(self.work, "checkout", "-f", "--detach", self.shas[checked_out or commit])
        for ref in run_git(
            self.work, "for-each-ref", "--format=%(refname)", "refs/remotes/origin"
        ).splitlines():
            if ref not in fetched_refs:
                run_git(self.work, "update-ref", "-d", ref)

    def _import(self, stream: FastImport, marks_file: Path) -> None:
        subprocess.run(
            [
                "git",
                "fast-import",
                "--quiet",
                f"--export-marks={marks_file}",
            ],
            cwd=self.work,
            input=stream.data(),
            check=True,
            capture_output=True,
        )

    def _render(self, spec: Any, default: dict[str, Any]) -> str | None:
        if spec is DEFAULT:
            spec = default
        if spec is None:
            return None
        if isinstance(spec, str):
            return spec
        return json.dumps(json.loads(json.dumps(spec).replace("$BASE", self.base)))

    def verify(
        self, *, tag: str | None = None, fetch: bool = True
    ) -> ReleaseDecision:
        chosen = self.tag if tag is None else tag
        return verify_release(self.work, chosen, self.commit, fetch=fetch)


def lists_without_lines() -> dict[str, Any]:
    return {"schema_version": 1, "main_line": "0.3", "maintenance_lines": []}


def lines_with(**overrides: Any) -> dict[str, Any]:
    data = default_list("$BASE")
    data["maintenance_lines"][0].update(overrides)
    return data


# (id, fixture kwargs, expected error regex or None, latest, prerelease, route)
SCENARIOS: list[dict[str, Any]] = [
    {"id": "S01", "kw": {}, "ok": (True, False, "maintenance")},
    {
        "id": "S02",
        "kw": {"tag": "v0.3.0", "commit": "MAIN_TIP"},
        "ok": (True, False, "main"),
    },
    {"id": "S03", "kw": {"commit": "MAIN_TIP"}, "err": "not contained in"},
    {
        "id": "S04",
        "kw": {"tag": "v0.3.0", "commit": "REL_TIP"},
        "err": "not contained in",
    },
    {"id": "S05", "kw": {"commit": "SIDE"}, "err": "not contained in"},
    {"id": "S06", "kw": {"commit": "LEGACY"}, "err": "base commit"},
    {
        "id": "S07",
        "kw": {"commit": "UNRELATED_TIP", "branch_tip": "UNRELATED_TIP"},
        "err": "base commit",
    },
    {"id": "S08a", "kw": {"tag": "v0.4.0"}, "err": "not an approved release line"},
    {"id": "S08b", "kw": {"tag": "v1.0.0"}, "err": "not an approved release line"},
    {
        "id": "S09",
        "kw": {"main_list": lists_without_lines()},
        "err": "not an approved release line",
    },
    {"id": "S10", "kw": {"tree_list": lists_without_lines()}, "err": "allow-list"},
    {
        "id": "S11",
        "kw": {"tree_list": lines_with(branch="release/0.2.y")},
        "err": "allow-list",
    },
    {
        "id": "S11b",
        "kw": {"tree_list": lines_with(base_commit="0" * 40)},
        "err": "allow-list",
    },
    {
        "id": "S12a",
        "kw": {"main_list": lines_with(branch="release/v0.2.0")},
        "err": "branch",
    },
    {"id": "S12b", "kw": {"main_list": lines_with(branch="main")}, "err": "branch"},
    {
        "id": "S12c",
        "kw": {"main_list": lines_with(branch="feature/x")},
        "err": "branch",
    },
    {"id": "S13", "kw": {"main_list": None}, "err": "allow-list"},
    {"id": "S14a", "kw": {"main_list": "{not json"}, "err": "allow-list"},
    {
        "id": "S14b",
        "kw": {"main_list": {**default_list("$BASE"), "schema_version": 2}},
        "err": "allow-list",
    },
    {
        "id": "S14c",
        "kw": {"main_list": {**default_list("$BASE"), "extra": True}},
        "err": "allow-list",
    },
    {
        "id": "S15",
        "kw": {
            "main_list": {
                **default_list("$BASE"),
                "main_line": "0.2",
            }
        },
        "err": "allow-list",
    },
    {"id": "S16", "kw": {"pyproject_version": "0.2.2"}, "err": "tag/version mismatch"},
    {"id": "S17", "kw": {"notes": False}, "err": "release notes not found"},
    {
        "id": "S19a",
        "kw": {"existing_tags": ("v0.2.0", "v0.2.2")},
        "err": "not greater",
    },
    {
        "id": "S19b",
        "kw": {"existing_tags": ("v0.2.0", "v0.2.1")},
        "err": "does not point at",
    },
    {
        "id": "S20",
        "kw": {"tag": "v0.2.2", "existing_tags": ("v0.2.0", "v0.2.3")},
        "err": "not greater",
    },
    {
        "id": "S21",
        "kw": {
            "tag": "v0.2.2",
            "existing_tags": ("v0.2.0", "v0.2.1", "v0.3.0"),
        },
        "ok": (False, False, "maintenance"),
    },
    {
        "id": "S22",
        "kw": {"tag": "v0.3.0rc1", "commit": "MAIN_TIP"},
        "ok": (False, True, "main"),
    },
    {
        "id": "S23",
        "kw": {
            "tag": "v0.3.0rc1",
            "commit": "MAIN_TIP",
            "existing_tags": ("v0.2.0", "v0.2.1"),
        },
        "ok": (False, True, "main"),
    },
    {
        "id": "S23b",
        "kw": {
            "tag": "v0.3.0rc1",
            "commit": "MAIN_TIP",
            "existing_tags": ("v0.2.0", "v0.3.0"),
        },
        "err": "already released",
    },
    {
        "id": "S24",
        "kw": {"checked_out": "MAIN_TIP"},
        "err": "checked-out",
    },
    {
        "id": "S25",
        "kw": {"fetched_refs": (MAIN_REF,)},
        "fetch": False,
        "err": "could not verify release ancestry",
    },
    {
        "id": "S26",
        "kw": {"fetched_refs": (REL_REF,)},
        "err": "allow-list",
    },
    {"id": "S27", "kw": {"commit": "REL_TIP"}, "ok": (True, False, "maintenance")},
    {
        "id": "S28",
        "kw": {"commit": "REL_TIP_MINUS_1"},
        "ok": (True, False, "maintenance"),
    },
    {
        "id": "S30",
        "kw": {"tag": "v0.3.0", "commit": "MAIN_SIDE"},
        "err": "not contained in",
    },
]


class ReleaseLineScenarioTests(unittest.TestCase):
    def run_fixture(self, kwargs: dict[str, Any], fetch: bool = True) -> ReleaseDecision:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            fixture = Fixture(Path(tmp), **kwargs)
            return fixture.verify(fetch=fetch)

    def test_scenarios(self) -> None:
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario["id"]):
                fetch = scenario.get("fetch", True)
                if "err" in scenario:
                    with self.assertRaisesRegex(RuntimeError, scenario["err"]):
                        self.run_fixture(scenario["kw"], fetch)
                    continue
                latest, prerelease, route = scenario["ok"]
                decision = self.run_fixture(scenario["kw"], fetch)
                self.assertEqual(decision.latest, latest)
                self.assertEqual(decision.prerelease, prerelease)
                self.assertEqual(decision.route.kind, route)
                if route == "maintenance":
                    self.assertEqual(decision.route.ref, REL_REF)
                else:
                    self.assertEqual(decision.route.ref, MAIN_REF)

    def test_s18_malformed_tags_rejected_before_any_use(self) -> None:
        bad = [
            "v0.2",
            "v0.2.1.post1",
            "v0.2.01",
            "v0.2.1+local",
            "V0.2.1",
            "v0.2.1-rc.1",
            "v0.2.1\n",
            "v0.2.1rc",
            "v0.2.1c1",
            "v٠.٢.١",
            "",
        ]
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            fixture = Fixture(Path(tmp))
            for tag in bad:
                with self.subTest(tag=tag):
                    with self.assertRaisesRegex(RuntimeError, "tag format"):
                        fixture.verify(tag=tag)

    def test_s29_shell_metacharacters_in_tag_rejected(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            fixture = Fixture(Path(tmp))
            for tag in ("v0.2.1;rm -rf /", "v0.2.1$(id)", "v0.2.1/../../x", "-v0.2.1"):
                with self.subTest(tag=tag):
                    with self.assertRaisesRegex(RuntimeError, "tag format"):
                        fixture.verify(tag=tag)

    def test_commit_must_be_full_sha(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            fixture = Fixture(Path(tmp))
            for commit in ("HEAD", fixture.commit[:12], "--all", fixture.commit.upper()):
                with self.subTest(commit=commit):
                    with self.assertRaisesRegex(RuntimeError, "40-hex"):
                        verify_release(fixture.work, fixture.tag, commit)

    def test_verifier_fetches_only_the_allow_listed_branch(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            fixture = Fixture(Path(tmp), fetched_refs=(MAIN_REF,))
            fixture.verify()
            refs = run_git(
                fixture.work, "for-each-ref", "--format=%(refname)", "refs/remotes"
            ).splitlines()
            self.assertEqual(sorted(refs), sorted([MAIN_REF, REL_REF]))

    def test_main_line_never_fetches_a_maintenance_branch(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            fixture = Fixture(
                Path(tmp), tag="v0.3.0", commit="MAIN_TIP", fetched_refs=(MAIN_REF,)
            )
            fixture.verify()
            refs = run_git(
                fixture.work, "for-each-ref", "--format=%(refname)", "refs/remotes"
            ).splitlines()
            self.assertEqual(refs, [MAIN_REF])

    def test_tag_pointing_elsewhere_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            fixture = Fixture(Path(tmp))
            run_git(fixture.work, "tag", "-f", fixture.tag, fixture.base)
            with self.assertRaisesRegex(RuntimeError, "does not point at"):
                fixture.verify()

    def test_github_output_contents(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            decision = Fixture(Path(tmp), tag="v0.3.0rc1", commit="MAIN_TIP").verify()
            out = Path(tmp) / "github_output.txt"
            write_github_output(out, decision)
            self.assertEqual(
                out.read_text(encoding="utf-8").splitlines(),
                ["prerelease=true", "latest=false", "route=main"],
            )


class ParsingTests(unittest.TestCase):
    def test_valid_tags(self) -> None:
        for tag in ("v0.2.1", "v10.20.30", "v0.3.0a1", "v0.3.0b2", "v0.3.0rc10"):
            with self.subTest(tag=tag):
                parse_tag(tag)
        self.assertTrue(parse_tag("v0.3.0rc1").prerelease)
        self.assertFalse(parse_tag("v0.3.0").prerelease)

    def test_duplicate_keys_rejected(self) -> None:
        text = (
            '{"schema_version":1,"schema_version":1,"main_line":"0.3",'
            '"maintenance_lines":[]}'
        )
        with self.assertRaisesRegex(RuntimeError, "allow-list"):
            parse_release_lines(text, "test")

    def test_duplicate_and_bool_schema_rejected(self) -> None:
        data = default_list("a" * 40)
        data["maintenance_lines"].append(copy.deepcopy(data["maintenance_lines"][0]))
        with self.assertRaisesRegex(RuntimeError, "duplicate"):
            parse_release_lines(json.dumps(data), "test")
        data = default_list("a" * 40)
        data["schema_version"] = True
        with self.assertRaisesRegex(RuntimeError, "schema_version"):
            parse_release_lines(json.dumps(data), "test")

    def test_repository_allow_list_is_valid_and_matches_design(self) -> None:
        text = (REPO_ROOT / ".github" / "release-lines.json").read_text(
            encoding="utf-8"
        )
        lines = parse_release_lines(text, "repository")
        self.assertEqual(lines.main_line, "0.3")
        self.assertEqual(len(lines.maintenance_lines), 1)
        entry = lines.maintenance_lines[0]
        self.assertEqual(entry.line, "0.2")
        self.assertEqual(entry.branch, "release/0.2.x")
        self.assertEqual(entry.base_commit, "106b91ea790bf96b059d5d60c07f79f16c02eeea")


def workflow_text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def step_block(text: str, step_name: str) -> str:
    match = re.search(
        rf"^      - name: {re.escape(step_name)}\n(.*?)(?=^      - name: |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, step_name
    return match.group(1)


class WorkflowStaticChecks(unittest.TestCase):
    def test_w01_release_invokes_verifier_and_fetches_only_main(self) -> None:
        text = workflow_text("release.yml")
        block = step_block(text, "Verify release source and metadata")
        self.assertIn("python scripts/verify_release.py", block)
        self.assertIn("--release-lines .github/release-lines.json", block)
        self.assertIn("id: verify", block)
        fetches = re.findall(r"git fetch .*", text)
        self.assertEqual(
            fetches,
            ["git fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main"],
        )
        self.assertNotIn("refs/heads/*", text)
        self.assertNotIn("release/*", text)

    def test_w02_explicit_release_labels_without_relabelling(self) -> None:
        text = workflow_text("release.yml")
        block = step_block(text, "Publish GitHub release")
        self.assertIn("steps.verify.outputs.latest", block)
        self.assertIn("steps.verify.outputs.prerelease", block)
        self.assertIn('"--latest=${RELEASE_LATEST}"', block)
        self.assertIn("--prerelease", block)
        self.assertIn("--verify-tag", block)
        self.assertNotIn("gh release edit", text)
        self.assertEqual(text.count("gh release"), 1)

    def test_release_publication_is_serialized_across_tags(self) -> None:
        text = workflow_text("release.yml")
        match = re.search(r"^concurrency:\n((?:  [^\n]*\n)+)", text, re.MULTILINE)
        self.assertIsNotNone(match)
        block = match.group(1)
        self.assertIn("  group: release-publication\n", block)
        self.assertIn("  cancel-in-progress: false\n", block)
        self.assertNotIn("${{", block)

    def test_w03_permissions_unchanged(self) -> None:
        text = workflow_text("release.yml")
        self.assertIn("\npermissions:\n  contents: read\n", text)
        self.assertEqual(len(re.findall(r"^\s*permissions:", text, re.M)), 2)
        job = text.split("    permissions:\n", 1)[1].split("    steps:", 1)[0]
        self.assertEqual(
            [line.strip() for line in job.strip().splitlines()],
            [
                "contents: write",
                "id-token: write",
                "attestations: write",
                "artifact-metadata: write",
            ],
        )

    def test_w04_every_action_is_sha_pinned(self) -> None:
        count = 0
        for path in sorted(WORKFLOWS.glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"^\s*(?:- )?uses:\s*(\S+)", text, re.M):
                count += 1
                self.assertRegex(
                    match.group(1),
                    r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$",
                    f"{path.name}: {match.group(1)}",
                )
        self.assertGreater(count, 0)
        for name in ("release.yml", "codeql.yml", "dependency-review.yml", "validate.yml"):
            text = workflow_text(name)
            self.assertEqual(
                text.count("actions/checkout@"),
                text.count("persist-credentials: false"),
                name,
            )

    def test_w05_release_hardening_steps_retained(self) -> None:
        text = workflow_text("release.yml")
        for needle in (
            "pip_audit",
            "scripts/validate_dist.py",
            "SHA256SUMS",
            "actions/attest@",
            "scripts/validate_repo.py",
            "ruff check .",
            "python -m unittest discover",
        ):
            self.assertIn(needle, text)

    def test_w06_branch_filters_cover_maintenance_not_legacy(self) -> None:
        pattern = "release/*.*.x"
        self.assertTrue(fnmatch.fnmatchcase("release/0.2.x", pattern))
        self.assertFalse(fnmatch.fnmatchcase("release/v0.2.0", pattern))
        filter_line = 'branches: [main, "release/*.*.x"]'
        expected = {
            "codeql.yml": 2,
            "dependency-review.yml": 1,
            "validate.yml": 1,
        }
        for name, count in expected.items():
            text = workflow_text(name)
            self.assertEqual(text.count(filter_line), count, name)
            self.assertNotIn("release/v0.2.0", text)
            self.assertNotIn("release/**", text)
        validate = workflow_text("validate.yml")
        self.assertIn("\n  pull_request:\n  workflow_dispatch:", validate)

    def test_w07_required_check_names_are_emitted_by_workflows(self) -> None:
        self.assertIn("name: Analyze (Python)", workflow_text("codeql.yml"))
        self.assertIn(
            "name: Review dependency changes", workflow_text("dependency-review.yml")
        )
        validate = workflow_text("validate.yml")
        self.assertIn("  validate:\n", validate)
        self.assertIn('python-version: ["3.11", "3.12"]', validate)


if __name__ == "__main__":
    unittest.main()
