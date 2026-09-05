from __future__ import annotations

import argparse
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify release metadata and protected-branch ancestry."
    )
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument(
        "--main-ref",
        default="refs/remotes/origin/main",
        help="Git ref for the protected main branch",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_release_metadata(ROOT, args.tag)
    validate_release_ancestry(ROOT, args.commit, args.main_ref)
    print(f"release source verified: {args.commit} is contained in {args.main_ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
