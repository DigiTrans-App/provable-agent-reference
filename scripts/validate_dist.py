from __future__ import annotations

import hashlib
import json
import tarfile
import tomllib
import zipfile
from email.parser import Parser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"


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


def validate_wheel(path: Path, project_name: str, version: str) -> None:
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


def validate_sdist(path: Path, distribution_stem: str, version: str) -> None:
    root = f"{distribution_stem}-{version}"
    required = {
        f"{root}/LICENSE",
        f"{root}/README.md",
        f"{root}/pyproject.toml",
        f"{root}/src/provable_agent_reference/__init__.py",
    }
    with tarfile.open(path, mode="r:gz") as archive:
        names = set(archive.getnames())
    missing = sorted(required - names)
    if missing:
        raise RuntimeError("source distribution is missing: " + ", ".join(missing))


def main() -> int:
    project_name, version = project_metadata()
    distribution_stem = project_name.replace("-", "_")
    wheel = DIST_DIR / f"{distribution_stem}-{version}-py3-none-any.whl"
    sdist = DIST_DIR / f"{distribution_stem}-{version}.tar.gz"

    missing = [path.name for path in (wheel, sdist) if not path.is_file()]
    if missing:
        raise RuntimeError("missing release artifacts: " + ", ".join(missing))

    validate_wheel(wheel, project_name, version)
    validate_sdist(sdist, distribution_stem, version)

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
