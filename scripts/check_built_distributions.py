"""Install and test the built distributions in fresh virtual environments.

Run after ``python -m build`` and ``scripts/validate_dist.py``. The checks run the
artifacts that would be published, not the repository checkout:

1. install the wheel into a fresh venv and smoke test it from a neutral directory;
2. install the source distribution (a real build from the sdist) into another fresh
   venv, extract the sdist, and run its bundled tests against the installed build.

Any failure exits non-zero. Nothing is published or modified by this script.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIST_DIR = ROOT / "dist"
DEFAULT_EXTRAS = "dev,openai"


def project_metadata() -> tuple[str, str]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    return str(project["name"]), str(project["version"])


def venv_python(venv: Path) -> Path:
    scripts = "Scripts" if os.name == "nt" else "bin"
    executable = "python.exe" if os.name == "nt" else "python"
    return venv / scripts / executable


def clean_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run(
    command: list[str], *, cwd: Path, env: dict[str, str], description: str
) -> subprocess.CompletedProcess[str]:
    print(f"==> {description}", flush=True)
    result = subprocess.run(command, cwd=cwd, env=env, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{description} failed with exit code {result.returncode}")
    return result


def create_venv(path: Path, *, cwd: Path, env: dict[str, str], description: str) -> Path:
    run([sys.executable, "-m", "venv", str(path)], cwd=cwd, env=env, description=description)
    return venv_python(path)


SMOKE_CODE = """
import json, sys
import provable_agent_reference as package
print(json.dumps({"version": package.__version__, "file": package.__file__}))
"""


def smoke_test(
    python: Path, *, version: str, forbidden: Path | None, cwd: Path, label: str
) -> None:
    """Import the installed package and run the demo entry point from a neutral cwd."""
    env = clean_environment()
    probe = subprocess.run(
        [str(python), "-c", SMOKE_CODE], cwd=cwd, env=env, text=True, capture_output=True
    )
    if probe.returncode != 0:
        raise RuntimeError(f"{label}: import failed:\n{probe.stdout}{probe.stderr}")
    info = json.loads(probe.stdout.strip().splitlines()[-1])
    if info["version"] != version:
        raise RuntimeError(f"{label}: version {info['version']!r} != pyproject {version!r}")
    location = Path(info["file"]).resolve()
    if "site-packages" not in location.parts:
        raise RuntimeError(f"{label}: package was not imported from site-packages: {location}")
    if forbidden is not None and forbidden.resolve() in location.parents:
        raise RuntimeError(f"{label}: package was imported from the source tree: {location}")
    demo = subprocess.run(
        [str(python), "-m", "provable_agent_reference"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )
    if demo.returncode != 0:
        raise RuntimeError(
            f"{label}: python -m provable_agent_reference exited {demo.returncode}:\n"
            f"{demo.stdout}{demo.stderr}"
        )
    json.loads(demo.stdout)
    print(f"{label}: imported {version} from {location}", flush=True)


def sdist_build_requirements(extracted: Path) -> list[str]:
    """Return ``[build-system].requires`` from the extracted sdist's own pyproject."""
    data = tomllib.loads((extracted / "pyproject.toml").read_text(encoding="utf-8"))
    requires = data.get("build-system", {}).get("requires", [])
    if not requires or not all(isinstance(item, str) and item for item in requires):
        raise RuntimeError("sdist pyproject.toml does not declare build-system requirements")
    return list(requires)


def extract_sdist(sdist: Path, destination: Path, root_name: str) -> Path:
    with tarfile.open(sdist, mode="r:gz") as archive:
        archive.extractall(destination, filter="data")
    extracted = destination / root_name
    if not extracted.is_dir():
        raise RuntimeError(f"sdist did not extract to {root_name}/")
    return extracted


def check(dist_dir: Path, extras: str, skip_sdist_tests: bool) -> None:
    name, version = project_metadata()
    stem = name.replace("-", "_")
    wheel = dist_dir / f"{stem}-{version}-py3-none-any.whl"
    sdist = dist_dir / f"{stem}-{version}.tar.gz"
    missing = [path.name for path in (wheel, sdist) if not path.is_file()]
    if missing:
        raise RuntimeError("missing release artifacts: " + ", ".join(missing))

    with tempfile.TemporaryDirectory(prefix="built-dist-check-") as scratch_name:
        scratch = Path(scratch_name)
        neutral = scratch / "neutral"
        neutral.mkdir()
        env = clean_environment()

        # 1. Wheel in a fresh venv.
        wheel_python = create_venv(
            scratch / "venv-wheel", cwd=neutral, env=env, description="create wheel venv"
        )
        run(
            [str(wheel_python), "-m", "pip", "install", "--quiet", str(wheel.resolve())],
            cwd=neutral,
            env=env,
            description="install built wheel",
        )
        smoke_test(wheel_python, version=version, forbidden=ROOT, cwd=neutral, label="wheel")

        # 2. Source distribution in another fresh venv.
        sdist_python = create_venv(
            scratch / "venv-sdist", cwd=neutral, env=env, description="create sdist venv"
        )
        requirement = f"{sdist.resolve()}[{extras}]" if extras else str(sdist.resolve())
        run(
            [str(sdist_python), "-m", "pip", "install", "--quiet", requirement],
            cwd=neutral,
            env=env,
            description=f"install built sdist with extras [{extras}]",
        )
        extracted = extract_sdist(sdist, scratch / "sdist-src", f"{stem}-{version}")
        smoke_test(sdist_python, version=version, forbidden=extracted, cwd=neutral, label="sdist")

        if skip_sdist_tests:
            print("sdist bundled tests skipped by request", flush=True)
            return

        # The bundled tests include a real sdist build, so the test environment
        # needs the build backend the sdist itself declares. This mirrors the
        # packaging-tool install in validate.yml; fresh venvs on Python 3.12+ do
        # not ship setuptools.
        build_requires = sdist_build_requirements(extracted)
        run(
            [
                str(sdist_python),
                "-m",
                "pip",
                "install",
                "--quiet",
                "--upgrade",
                "pip",
                *build_requires,
            ],
            cwd=neutral,
            env=env,
            description="install the sdist's build requirements: " + ", ".join(build_requires),
        )

        # 3. The sdist must be self-contained: run its bundled tests from the
        # extracted tree against the installed build (src/ is not on the path).
        test_env = clean_environment()
        test_env.setdefault("HYPOTHESIS_PROFILE", "ci")
        run(
            [str(sdist_python), "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=extracted,
            env=test_env,
            description="run bundled tests from the extracted sdist",
        )
    print("built distributions verified", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=DEFAULT_DIST_DIR)
    parser.add_argument("--extras", default=DEFAULT_EXTRAS, help="extras to install with the sdist")
    parser.add_argument("--skip-sdist-tests", action="store_true")
    args = parser.parse_args(argv)
    try:
        check(args.dist_dir, args.extras, args.skip_sdist_tests)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
