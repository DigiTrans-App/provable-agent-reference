"""Verify release source, metadata and release-line authorization.

Security-critical release automation (accepted decision 0009).
The verifier fails closed: any unexpected state raises ``RuntimeError``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_RELEASE_LINES_PATH = ".github/release-lines.json"
DEFAULT_MAIN_REF = "refs/remotes/origin/main"

_NUM = r"(?:0|[1-9][0-9]*)"
TAG_PATTERN = re.compile(
    rf"v({_NUM})\.({_NUM})\.({_NUM})(?:(a|b|rc)({_NUM}))?", re.ASCII
)
LINE_PATTERN = re.compile(rf"({_NUM})\.({_NUM})", re.ASCII)
BRANCH_PATTERN = re.compile(rf"release/{_NUM}\.{_NUM}\.x", re.ASCII)
SHA_PATTERN = re.compile(r"[0-9a-f]{40}", re.ASCII)
PATH_PATTERN = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_./-]*", re.ASCII)

_TOP_KEYS = {"schema_version", "main_line", "maintenance_lines"}
_ENTRY_KEYS = {"line", "branch", "base_commit"}


@dataclass(frozen=True)
class ParsedTag:
    tag: str
    major: int
    minor: int
    patch: int
    prerelease: bool

    @property
    def line(self) -> str:
        return f"{self.major}.{self.minor}"

    @property
    def version(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)


@dataclass(frozen=True)
class MaintenanceLine:
    line: str
    branch: str
    base_commit: str


@dataclass(frozen=True)
class ReleaseLines:
    main_line: str
    maintenance_lines: tuple[MaintenanceLine, ...]

    def find(self, line: str) -> MaintenanceLine | None:
        for entry in self.maintenance_lines:
            if entry.line == line:
                return entry
        return None


@dataclass(frozen=True)
class ReleaseRoute:
    kind: str  # "main" or "maintenance"
    ref: str
    branch: str | None = None
    base_commit: str | None = None


@dataclass(frozen=True)
class ReleaseDecision:
    route: ReleaseRoute
    prerelease: bool
    latest: bool


def parse_tag(tag: str) -> ParsedTag:
    match = TAG_PATTERN.fullmatch(tag)
    if match is None:
        raise RuntimeError(f"invalid release tag format: {tag!r}")
    major, minor, patch, kind, _number = match.groups()
    return ParsedTag(tag, int(major), int(minor), int(patch), kind is not None)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def parse_release_lines(text: str, source: str) -> ReleaseLines:
    """Strictly parse an allow-list; every deviation is an error."""

    def invalid(reason: str) -> RuntimeError:
        return RuntimeError(f"release allow-list invalid ({source}): {reason}")

    try:
        data = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except ValueError as error:
        raise invalid(f"not valid JSON ({error})") from error
    if not isinstance(data, dict) or set(data) != _TOP_KEYS:
        raise invalid("unexpected or missing top-level keys")
    version = data["schema_version"]
    if type(version) is not int or version != 1:
        raise invalid("unsupported schema_version")
    main_line = data["main_line"]
    if not isinstance(main_line, str) or LINE_PATTERN.fullmatch(main_line) is None:
        raise invalid("main_line must be MAJOR.MINOR")
    entries = data["maintenance_lines"]
    if not isinstance(entries, list):
        raise invalid("maintenance_lines must be a list")
    parsed: list[MaintenanceLine] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
            raise invalid("unexpected or missing maintenance line keys")
        line, branch, base = entry["line"], entry["branch"], entry["base_commit"]
        if not all(isinstance(value, str) for value in (line, branch, base)):
            raise invalid("maintenance line values must be strings")
        if LINE_PATTERN.fullmatch(line) is None:
            raise invalid(f"line {line!r} must be MAJOR.MINOR")
        if BRANCH_PATTERN.fullmatch(branch) is None or branch != f"release/{line}.x":
            raise invalid(f"branch {branch!r} must be release/{line}.x")
        if SHA_PATTERN.fullmatch(base) is None:
            raise invalid(f"base_commit for {line} must be a 40-hex SHA")
        if line == main_line:
            raise invalid(f"line {line} is both main_line and a maintenance line")
        if line in seen:
            raise invalid(f"duplicate maintenance line {line}")
        seen.add(line)
        parsed.append(MaintenanceLine(line, branch, base))
    return ReleaseLines(main_line, tuple(parsed))


def _check_path(path: str) -> None:
    if PATH_PATTERN.fullmatch(path) is None or ".." in path.split("/"):
        raise RuntimeError(f"unsafe release allow-list path: {path!r}")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        check=False,
        text=True,
    )


def read_release_lines(repo: Path, rev: str, path: str, label: str) -> ReleaseLines:
    """Read the allow-list stored at ``rev:path`` (never the working tree)."""
    _check_path(path)
    result = _git(repo, "show", f"{rev}:{path}")
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown git error"
        raise RuntimeError(
            f"release allow-list could not be read from {label} ({rev}:{path}): "
            f"{detail}"
        )
    return parse_release_lines(result.stdout, label)


def select_release_route(
    parsed: ParsedTag,
    main_lines: ReleaseLines,
    tree_lines: ReleaseLines,
    main_ref: str = DEFAULT_MAIN_REF,
) -> ReleaseRoute:
    """Route by the tag's own MAJOR.MINOR; main's allow-list is authoritative."""
    if main_lines.main_line != tree_lines.main_line:
        raise RuntimeError(
            "release allow-list main_line differs between main and the tagged tree"
        )
    if parsed.line == main_lines.main_line:
        return ReleaseRoute(kind="main", ref=main_ref)
    entry = main_lines.find(parsed.line)
    if entry is None:
        raise RuntimeError(f"{parsed.tag} is not an approved release line")
    if tree_lines.find(parsed.line) != entry:
        raise RuntimeError(
            f"release allow-list entry for {parsed.line} differs between main "
            "and the tagged tree"
        )
    return ReleaseRoute(
        kind="maintenance",
        ref=f"refs/remotes/origin/{entry.branch}",
        branch=entry.branch,
        base_commit=entry.base_commit,
    )


def validate_release_metadata(root: Path, tag: str) -> None:
    project = tomllib.loads(
        (root / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    expected_tag = f"v{project['version']}"
    if tag != expected_tag:
        raise RuntimeError(f"tag/version mismatch: {tag} != {expected_tag}")

    notes = root / "docs" / "releases" / f"{tag}.md"
    if not notes.is_file():
        raise RuntimeError(f"release notes not found: {notes.relative_to(root)}")


def validate_release_ancestry(repo: Path, commit: str, main_ref: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, main_ref],
        cwd=repo,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode == 0:
        return
    if result.returncode == 1:
        raise RuntimeError(
            f"release commit {commit} is not contained in protected branch {main_ref}"
        )
    detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
    raise RuntimeError(f"could not verify release ancestry: {detail}")


def validate_base_commit(repo: Path, base_commit: str, commit: str) -> None:
    result = _git(repo, "merge-base", "--is-ancestor", base_commit, commit)
    if result.returncode == 0:
        return
    if result.returncode == 1:
        raise RuntimeError(
            f"release commit {commit} does not descend from approved base commit "
            f"{base_commit}"
        )
    detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
    raise RuntimeError(f"could not verify release ancestry: {detail}")


def fetch_maintenance_branch(repo: Path, branch: str, remote: str = "origin") -> None:
    """Fetch exactly one allow-listed, name-validated maintenance branch."""
    if BRANCH_PATTERN.fullmatch(branch) is None:
        raise RuntimeError(f"refusing to fetch unapproved branch name: {branch!r}")
    result = _git(
        repo,
        "fetch",
        "--no-tags",
        remote,
        f"+refs/heads/{branch}:refs/remotes/{remote}/{branch}",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown git error"
        raise RuntimeError(f"could not fetch {branch}: {detail}")


def _list_release_tags(repo: Path) -> list[ParsedTag]:
    result = _git(repo, "tag", "--list")
    if result.returncode != 0:
        raise RuntimeError(f"could not list tags: {result.stderr.strip()}")
    tags = []
    for name in result.stdout.splitlines():
        if TAG_PATTERN.fullmatch(name) is not None:
            tags.append(parse_tag(name))
    return tags


def validate_tag_points_at(repo: Path, tag: str, commit: str) -> None:
    result = _git(repo, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")
    if result.returncode != 0 or result.stdout.strip() != commit:
        raise RuntimeError(f"tag {tag} does not point at release commit {commit}")


def classify_release(repo: Path, parsed: ParsedTag) -> tuple[bool, bool]:
    """Return (prerelease, latest) and enforce patch monotonicity."""
    others = [t for t in _list_release_tags(repo) if t.tag != parsed.tag]
    stable = [t for t in others if not t.prerelease]
    if not parsed.prerelease:
        newest = max(
            (t.patch for t in stable if t.line == parsed.line), default=None
        )
        if newest is not None and parsed.patch <= newest:
            raise RuntimeError(
                f"{parsed.tag} patch {parsed.patch} is not greater than existing "
                f"stable patch {newest} in line {parsed.line}"
            )
    elif any(t.version == parsed.version for t in stable):
        raise RuntimeError(
            f"{parsed.tag} is a prerelease of an already released version"
        )
    latest = (not parsed.prerelease) and all(
        parsed.version > t.version for t in stable
    )
    return parsed.prerelease, latest


def verify_release(
    repo: Path,
    tag: str,
    commit: str,
    *,
    main_ref: str = DEFAULT_MAIN_REF,
    release_lines_path: str = DEFAULT_RELEASE_LINES_PATH,
    fetch: bool = True,
    remote: str = "origin",
) -> ReleaseDecision:
    parsed = parse_tag(tag)
    if SHA_PATTERN.fullmatch(commit) is None:
        raise RuntimeError("release commit must be a full lowercase 40-hex SHA")

    validate_release_metadata(repo, tag)

    head = _git(repo, "rev-parse", "--verify", "HEAD^{commit}")
    if head.returncode != 0 or head.stdout.strip() != commit:
        raise RuntimeError(
            f"checked-out HEAD does not match release commit {commit}"
        )
    validate_tag_points_at(repo, tag, commit)

    main_lines = read_release_lines(
        repo, main_ref, release_lines_path, f"main ({main_ref})"
    )
    tree_lines = read_release_lines(
        repo, commit, release_lines_path, "tagged tree"
    )
    route = select_release_route(parsed, main_lines, tree_lines, main_ref)

    if route.kind == "maintenance":
        if route.branch is None or route.base_commit is None:
            raise RuntimeError("maintenance route is missing branch or base commit")
        validate_base_commit(repo, route.base_commit, commit)
        if fetch:
            fetch_maintenance_branch(repo, route.branch, remote)
    validate_release_ancestry(repo, commit, route.ref)

    prerelease, latest = classify_release(repo, parsed)
    return ReleaseDecision(route=route, prerelease=prerelease, latest=latest)


def write_github_output(path: Path, decision: ReleaseDecision) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"prerelease={str(decision.prerelease).lower()}\n")
        handle.write(f"latest={str(decision.latest).lower()}\n")
        handle.write(f"route={decision.route.kind}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify release metadata, release line and branch ancestry."
    )
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument(
        "--main-ref",
        default=DEFAULT_MAIN_REF,
        help="Git ref for the protected main branch",
    )
    parser.add_argument(
        "--release-lines",
        default=DEFAULT_RELEASE_LINES_PATH,
        help="Repository path of the release-line allow-list",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    decision = verify_release(
        ROOT,
        args.tag,
        args.commit,
        main_ref=args.main_ref,
        release_lines_path=args.release_lines,
    )
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        write_github_output(Path(output), decision)
    print(
        f"release source verified: {args.commit} is contained in "
        f"{decision.route.ref} (prerelease={str(decision.prerelease).lower()}, "
        f"latest={str(decision.latest).lower()})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
