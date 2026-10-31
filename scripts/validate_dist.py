from __future__ import annotations

import hashlib
import json
import tarfile
import tomllib
import zipfile
from collections.abc import Iterable
from email.parser import Parser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
PACKAGE = "provable_agent_reference"

# Files outside tests/ and src/ that the bundled tests import or open. Keep this
# list in step with MANIFEST.in. tests/*.py, every module under src/ and the
# release notes for the project version are added by required_sdist_paths().
SDIST_SUPPORT_PATHS = (
    "CHANGELOG.md",
    "MANIFEST.in",
    "NOTICE",
    ".github/release-lines.json",
    ".github/workflows/release.yml",
    ".github/workflows/validate.yml",
    "examples/codex_evidence_adapter/expected/codex_coverage.expected.json",
    "examples/codex_evidence_adapter/expected/codex_evidence_bundle.expected.json",
    "examples/codex_evidence_adapter/fixtures/codex_exec.synthetic.jsonl",
    "examples/codex_evidence_adapter/fixtures/codex_otel.synthetic.jsonl",
    "examples/records/assurance-packet.example.json",
    "scripts/check_built_distributions.py",
    "scripts/external_validation/__init__.py",
    "scripts/external_validation/runner.py",
    "scripts/validate_dist.py",
    "scripts/validate_repo.py",
    "scripts/verify_release.py",
    "trust/development-trust-bundle.json",
    "typescript/verifier.ts",
    "vectors/dsse/envelope.json",
    "vectors/dsse/packet.json",
)


def project_metadata() -> tuple[str, str]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    return str(project["name"]), str(project["version"])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_modules(repo_root: Path = ROOT) -> set[str]:
    """Return the package's Python files relative to src/, as POSIX paths."""
    src = repo_root / "src"
    return {path.relative_to(src).as_posix() for path in (src / PACKAGE).rglob("*.py")}


def required_sdist_paths(version: str, repo_root: Path = ROOT) -> set[str]:
    """Return the repository-relative paths a self-contained sdist must contain."""
    required = set(SDIST_SUPPORT_PATHS)
    required.add(f"docs/releases/v{version}.md")
    required.update(f"tests/{path.name}" for path in (repo_root / "tests").glob("*.py"))
    required.update(f"src/{module}" for module in package_modules(repo_root))
    return required


def is_bytecode(name: str) -> bool:
    parts = name.split("/")
    return "__pycache__" in parts or name.endswith((".pyc", ".pyo"))


def validate_wheel(
    path: Path,
    project_name: str,
    version: str,
    expected_modules: Iterable[str] = (),
) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        metadata_paths = sorted(
            name for name in names if name.endswith(".dist-info/METADATA")
        )
        if len(metadata_paths) != 1:
            raise RuntimeError(
                f"expected one wheel METADATA file, found {len(metadata_paths)}"
            )

        metadata = Parser().parsestr(
            archive.read(metadata_paths[0]).decode("utf-8")
        )
        if metadata.get("Name") != project_name:
            raise RuntimeError(
                f"wheel project name mismatch: {metadata.get('Name')!r} != {project_name!r}"
            )
        if metadata.get("Version") != version:
            raise RuntimeError(
                f"wheel version mismatch: {metadata.get('Version')!r} != {version!r}"
            )
        if "provable_agent_reference/__init__.py" not in names:
            raise RuntimeError("wheel does not contain the public package")
        missing = sorted(set(expected_modules) - names)
        if missing:
            raise RuntimeError("wheel is missing modules: " + ", ".join(missing))
        bytecode = sorted(name for name in names if is_bytecode(name))
        if bytecode:
            raise RuntimeError("wheel contains bytecode: " + ", ".join(bytecode))


def validate_sdist(
    path: Path,
    distribution_stem: str,
    version: str,
    required_paths: Iterable[str] = (),
) -> None:
    root = f"{distribution_stem}-{version}"
    required = {
        f"{root}/LICENSE",
        f"{root}/README.md",
        f"{root}/pyproject.toml",
        f"{root}/src/provable_agent_reference/__init__.py",
    }
    required.update(f"{root}/{relative}" for relative in required_paths)
    with tarfile.open(path, mode="r:gz") as archive:
        names = set(archive.getnames())
    missing = sorted(required - names)
    if missing:
        raise RuntimeError("source distribution is missing: " + ", ".join(missing))
    bytecode = sorted(name for name in names if is_bytecode(name))
    if bytecode:
        raise RuntimeError("source distribution contains bytecode: " + ", ".join(bytecode))


def main() -> int:
    project_name, version = project_metadata()
    distribution_stem = project_name.replace("-", "_")
    wheel = DIST_DIR / f"{distribution_stem}-{version}-py3-none-any.whl"
    sdist = DIST_DIR / f"{distribution_stem}-{version}.tar.gz"

    missing = [path.name for path in (wheel, sdist) if not path.is_file()]
    if missing:
        raise RuntimeError("missing release artifacts: " + ", ".join(missing))

    validate_wheel(wheel, project_name, version, package_modules())
    validate_sdist(sdist, distribution_stem, version, required_sdist_paths(version))

    result = {
        "artifacts": [
            {
                "filename": path.name,
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in (wheel, sdist)
        ],
        "project": project_name,
        "version": version,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
