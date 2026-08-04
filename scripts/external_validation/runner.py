from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tarfile
import time
import tomllib
import zipfile
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from email.parser import Parser
from pathlib import Path, PurePosixPath
from typing import Any

from . import SCHEMA_VERSION

SCHEMA_URI = (
    "https://digitrans.app/schemas/provable-agent-reference/"
    "independent-validation-report.schema.json"
)
DEFAULT_REPOSITORY = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("validation-results/independent-validation-report.json")
CHECKSUM_PATTERN = re.compile(r"^([0-9a-fA-F]{64})\s+\*?(.+)$")
WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")
SECRET_PATTERNS = (
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"(?i)\bBearer\s+[^\s,;]+"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|password|secret)\b"
        r"\s*[:=]\s*[^\s,;]+"
    ),
    re.compile(
        r"-----BEGIN [^-\n]*PRIVATE KEY-----.*?"
        r"-----END [^-\n]*PRIVATE KEY-----",
        flags=re.DOTALL,
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sanitize_text(value: str, repository_root: Path) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    replacements = {
        str(repository_root.resolve()): "$REPOSITORY_ROOT",
        repository_root.resolve().as_posix(): "$REPOSITORY_ROOT",
        str(Path.home().resolve()): "$HOME",
        Path.home().resolve().as_posix(): "$HOME",
    }
    for source, replacement in sorted(
        replacements.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if source and source != os.sep:
            normalized = normalized.replace(source, replacement)
    for pattern in SECRET_PATTERNS:
        normalized = pattern.sub("<redacted>", normalized)
    return normalized


def sanitize_structure(value: Any, repository_root: Path) -> Any:
    if isinstance(value, str):
        return sanitize_text(value, repository_root)
    if isinstance(value, list):
        return [sanitize_structure(item, repository_root) for item in value]
    if isinstance(value, dict):
        return {
            key: sanitize_structure(item, repository_root)
            for key, item in value.items()
        }
    return value


def output_summary(value: str, repository_root: Path, limit: int) -> dict[str, Any]:
    sanitized = sanitize_text(value, repository_root)
    return {
        "sha256": sha256_text(sanitized),
        "tail": sanitized[-limit:],
        "truncated": len(sanitized) > limit,
    }


def display_command(command: Sequence[str]) -> list[str]:
    rendered = list(command)
    if rendered and Path(rendered[0]).resolve() == Path(sys.executable).resolve():
        rendered[0] = "$PYTHON"
    return rendered


def validate_json_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return {"json_type": "object", "keys": sorted(value)}


def validate_repository_result(value: Any) -> dict[str, Any]:
    summary = validate_json_object(value)
    if value.get("secret_hygiene") != "pass":
        raise ValueError("repository secret-hygiene result did not pass")
    summary["version"] = value.get("version")
    summary["schemas"] = value.get("schemas")
    summary["examples"] = value.get("examples")
    return summary


def validate_evaluation_result(value: Any) -> dict[str, Any]:
    summary = validate_json_object(value)
    if value.get("passed") is not True:
        raise ValueError("local evaluation suite did not report passed=true")
    summary["case_count"] = value.get("case_count")
    summary["passed"] = True
    return summary


def run_command(
    *,
    name: str,
    command: Sequence[str],
    repository_root: Path,
    timeout_seconds: int,
    max_output_chars: int,
    json_validator: Callable[[Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    started_at = utc_now()
    started = time.monotonic()
    environment = os.environ.copy()
    environment.setdefault("PYTHONHASHSEED", "0")
    environment.setdefault("PYTHONDONTWRITEBYTECODE", "1")

    try:
        completed = subprocess.run(
            list(command),
            cwd=repository_root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        status = "pass" if completed.returncode == 0 else "fail"
        validation_error: str | None = None
        structured_output: dict[str, Any] | None = None

        if status == "pass" and json_validator is not None:
            try:
                structured_output = json_validator(json.loads(stdout))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                status = "fail"
                validation_error = str(exc)

        result: dict[str, Any] = {
            "name": name,
            "required": True,
            "status": status,
            "command": display_command(command),
            "started_at": started_at,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "returncode": completed.returncode,
            "stdout": output_summary(stdout, repository_root, max_output_chars),
            "stderr": output_summary(stderr, repository_root, max_output_chars),
        }
        if validation_error is not None:
            result["validation_error"] = validation_error
        if structured_output is not None:
            result["structured_output"] = structured_output
        return result
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {
            "name": name,
            "required": True,
            "status": "timeout",
            "command": display_command(command),
            "started_at": started_at,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "returncode": None,
            "stdout": output_summary(stdout, repository_root, max_output_chars),
            "stderr": output_summary(stderr, repository_root, max_output_chars),
            "validation_error": f"command exceeded {timeout_seconds} seconds",
        }
    except OSError as exc:
        return {
            "name": name,
            "required": True,
            "status": "error",
            "command": display_command(command),
            "started_at": started_at,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "returncode": None,
            "stdout": output_summary("", repository_root, max_output_chars),
            "stderr": output_summary(str(exc), repository_root, max_output_chars),
            "validation_error": str(exc),
        }


def git_text(repository_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(detail or f"git {' '.join(arguments)} failed")
    return completed.stdout.strip()


def collect_git_provenance(
    repository_root: Path,
    *,
    expected_tag: str | None,
    expected_commit: str | None,
    allow_dirty: bool,
) -> dict[str, Any]:
    errors: list[str] = []
    result: dict[str, Any] = {
        "available": False,
        "status": "fail",
        "repository_root_matches": None,
        "commit_sha": None,
        "dirty": None,
        "exact_tags": [],
        "expected_tag": expected_tag,
        "expected_commit": expected_commit,
        "origin_present": False,
        "tag": None,
        "errors": errors,
    }

    try:
        top_level = Path(git_text(repository_root, "rev-parse", "--show-toplevel")).resolve()
        head = git_text(repository_root, "rev-parse", "HEAD")
        status = git_text(
            repository_root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        )
        exact_tags_text = git_text(
            repository_root,
            "tag",
            "--points-at",
            "HEAD",
            "--sort=refname",
        )
        exact_tags = [line for line in exact_tags_text.splitlines() if line]

        result.update(
            {
                "available": True,
                "repository_root_matches": top_level == repository_root.resolve(),
                "commit_sha": head,
                "dirty": bool(status),
                "exact_tags": exact_tags,
            }
        )

        try:
            git_text(repository_root, "remote", "get-url", "origin")
            result["origin_present"] = True
        except RuntimeError:
            result["origin_present"] = False

        if top_level != repository_root.resolve():
            errors.append("--repository does not resolve to the Git top-level directory")
        if status and not allow_dirty:
            errors.append("working tree is not clean")

        if expected_commit is not None:
            resolved_expected = git_text(
                repository_root,
                "rev-parse",
                f"{expected_commit}^{{commit}}",
            )
            if resolved_expected != head:
                errors.append(
                    f"HEAD {head} does not match expected commit {resolved_expected}"
                )

        if expected_tag is not None:
            tag_ref = f"refs/tags/{expected_tag}"
            object_type = git_text(repository_root, "cat-file", "-t", tag_ref)
            object_sha = git_text(repository_root, "rev-parse", tag_ref)
            peeled_commit = git_text(
                repository_root,
                "rev-list",
                "-n",
                "1",
                expected_tag,
            )
            message = git_text(
                repository_root,
                "for-each-ref",
                "--format=%(contents)",
                tag_ref,
            )
            result["tag"] = {
                "name": expected_tag,
                "object_type": object_type,
                "object_sha": object_sha,
                "peeled_commit_sha": peeled_commit,
                "message": message,
            }
            if object_type != "tag":
                errors.append(f"{expected_tag} is not an annotated tag")
            if peeled_commit != head:
                errors.append(f"{expected_tag} resolves to {peeled_commit}, not HEAD {head}")
    except (OSError, RuntimeError) as exc:
        errors.append(f"Git provenance unavailable: {exc}")

    result["status"] = "pass" if not errors else "fail"
    return result


def read_project_metadata(repository_root: Path) -> dict[str, str]:
    pyproject = tomllib.loads(
        (repository_root / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    return {"name": str(pyproject["name"]), "version": str(pyproject["version"])}


def parse_sha256sums(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line:
            continue
        match = CHECKSUM_PATTERN.fullmatch(line)
        if match is None:
            raise ValueError(f"invalid SHA256SUMS line {line_number}")
        digest = match.group(1).lower()
        filename = match.group(2).strip()
        candidate = Path(filename)
        if (
            candidate.is_absolute()
            or candidate.name != filename
            or ".." in candidate.parts
            or "/" in filename
            or "\\" in filename
            or WINDOWS_DRIVE_PATTERN.match(filename)
        ):
            raise ValueError(f"unsafe SHA256SUMS filename on line {line_number}")
        if filename in entries:
            raise ValueError(f"duplicate SHA256SUMS entry for {filename}")
        entries[filename] = digest
    if not entries:
        raise ValueError("SHA256SUMS contains no entries")
    return entries


def is_unsafe_archive_path(value: str) -> bool:
    path = PurePosixPath(value.replace("\\", "/"))
    return (
        path.is_absolute()
        or ".." in path.parts
        or WINDOWS_DRIVE_PATTERN.match(value) is not None
    )


def validate_wheel(path: Path, project_name: str, version: str) -> None:
    distribution_stem = project_name.replace("-", "_")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if any(is_unsafe_archive_path(name) for name in names):
            raise ValueError("wheel contains an unsafe archive path")
        metadata_paths = sorted(
            name for name in names if name.endswith(".dist-info/METADATA")
        )
        if len(metadata_paths) != 1:
            raise ValueError(
                f"expected one wheel METADATA file, found {len(metadata_paths)}"
            )
        metadata = Parser().parsestr(
            archive.read(metadata_paths[0]).decode("utf-8", errors="strict")
        )
        if metadata.get("Name") != project_name:
            raise ValueError("wheel project name does not match ARTIFACTS.json")
        if metadata.get("Version") != version:
            raise ValueError("wheel version does not match ARTIFACTS.json")
        if f"{distribution_stem}/__init__.py" not in names:
            raise ValueError("wheel does not contain the public package")


def validate_sdist(path: Path, project_name: str, version: str) -> None:
    distribution_stem = project_name.replace("-", "_")
    root = f"{distribution_stem}-{version}"
    required = {
        f"{root}/LICENSE",
        f"{root}/README.md",
        f"{root}/pyproject.toml",
        f"{root}/src/{distribution_stem}/__init__.py",
    }
    with tarfile.open(path, mode="r:gz") as archive:
        names = set(archive.getnames())
    if any(is_unsafe_archive_path(name) for name in names):
        raise ValueError("source distribution contains an unsafe archive path")
    missing = sorted(required - names)
    if missing:
        raise ValueError("source distribution is missing: " + ", ".join(missing))


def verify_release_artifacts(
    release_dir: Path | None,
    *,
    expected_project: str | None,
    expected_version: str | None,
    required: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "requested": release_dir is not None,
        "required": required,
        "status": "not_requested",
        "directory": None,
        "project": None,
        "version": None,
        "files": [],
        "errors": [],
    }
    errors: list[str] = result["errors"]

    if release_dir is None:
        if required:
            result["status"] = "fail"
            errors.append("release artifacts were required but --release-dir was not provided")
        return result

    directory = release_dir.expanduser().resolve()
    result["directory"] = "$RELEASE_DIR"
    try:
        if not directory.is_dir():
            raise ValueError("release directory does not exist")

        manifest_path = directory / "ARTIFACTS.json"
        checksums_path = directory / "SHA256SUMS"
        if not manifest_path.is_file() or not checksums_path.is_file():
            raise ValueError(
                "release directory must contain ARTIFACTS.json and SHA256SUMS"
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        project_name = str(manifest["project"])
        version = str(manifest["version"])
        result["project"] = project_name
        result["version"] = version

        if expected_project is not None and project_name != expected_project:
            raise ValueError(
                f"artifact project {project_name} does not match expected {expected_project}"
            )
        if expected_version is not None and version != expected_version:
            raise ValueError(
                f"artifact version {version} does not match expected {expected_version}"
            )

        distribution_stem = project_name.replace("-", "_")
        wheel_name = f"{distribution_stem}-{version}-py3-none-any.whl"
        sdist_name = f"{distribution_stem}-{version}.tar.gz"
        expected_checksum_names = {wheel_name, sdist_name, "ARTIFACTS.json"}
        checksum_entries = parse_sha256sums(checksums_path)
        if set(checksum_entries) != expected_checksum_names:
            raise ValueError(
                "SHA256SUMS entries do not match the expected wheel, source "
                "distribution, and ARTIFACTS.json"
            )

        verified_files: list[dict[str, Any]] = []
        for filename in sorted(expected_checksum_names):
            artifact_path = directory / filename
            if not artifact_path.is_file():
                raise ValueError(f"release artifact is missing: {filename}")
            digest = sha256_file(artifact_path)
            if digest != checksum_entries[filename]:
                raise ValueError(f"SHA-256 mismatch for {filename}")
            verified_files.append(
                {
                    "filename": filename,
                    "sha256": digest,
                    "size_bytes": artifact_path.stat().st_size,
                }
            )

        manifest_entries = manifest.get("artifacts")
        if not isinstance(manifest_entries, list):
            raise ValueError("ARTIFACTS.json artifacts must be a list")
        by_name: dict[str, dict[str, Any]] = {}
        for entry in manifest_entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("filename"), str):
                raise ValueError("ARTIFACTS.json contains an invalid artifact entry")
            filename = entry["filename"]
            if filename in by_name:
                raise ValueError(f"ARTIFACTS.json repeats {filename}")
            by_name[filename] = entry
        if set(by_name) != {wheel_name, sdist_name}:
            raise ValueError(
                "ARTIFACTS.json must describe exactly the wheel and source archive"
            )

        for filename in (wheel_name, sdist_name):
            artifact_path = directory / filename
            entry = by_name[filename]
            if entry.get("sha256") != sha256_file(artifact_path):
                raise ValueError(f"ARTIFACTS.json SHA-256 mismatch for {filename}")
            if entry.get("size_bytes") != artifact_path.stat().st_size:
                raise ValueError(f"ARTIFACTS.json size mismatch for {filename}")

        validate_wheel(directory / wheel_name, project_name, version)
        validate_sdist(directory / sdist_name, project_name, version)

        result["status"] = "pass"
        result["files"] = verified_files
    except (
        KeyError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        tarfile.TarError,
        zipfile.BadZipFile,
    ) as exc:
        result["status"] = "fail"
        errors.append(str(exc))

    return result


def environment_summary() -> dict[str, str]:
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
        "os_name": os.name,
    }


def report_digest(report: dict[str, Any]) -> str:
    canonical = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return sha256_text(canonical)


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the public offline validation suite and write a privacy-bounded JSON report."
        )
    )
    parser.add_argument(
        "--repository",
        type=Path,
        default=DEFAULT_REPOSITORY,
        help="repository checkout to validate (default: this repository)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="report path; relative paths are resolved inside --repository",
    )
    parser.add_argument(
        "--expected-tag",
        help="require an annotated tag to resolve to HEAD",
    )
    parser.add_argument(
        "--expected-commit",
        help="require HEAD to match this commit or ref",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="record but do not fail on a dirty working tree",
    )
    parser.add_argument(
        "--release-dir",
        type=Path,
        help=(
            "directory containing a wheel, source archive, ARTIFACTS.json, "
            "and SHA256SUMS"
        ),
    )
    parser.add_argument(
        "--require-artifacts",
        action="store_true",
        help="fail unless --release-dir is supplied and all artifacts verify",
    )
    parser.add_argument(
        "--expected-artifact-version",
        help=(
            "expected version in ARTIFACTS.json "
            "(default: checkout project version)"
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
        help="timeout applied independently to each command",
    )
    parser.add_argument(
        "--max-output-chars",
        type=int,
        default=4000,
        help="maximum sanitized tail retained for stdout and stderr per command",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    if args.max_output_chars <= 0:
        parser.error("--max-output-chars must be positive")

    repository_root = args.repository.expanduser().resolve()
    output_path = args.output.expanduser()
    if not output_path.is_absolute():
        output_path = repository_root / output_path

    errors: list[str] = []
    report: dict[str, Any] = {
        "$schema": SCHEMA_URI,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": "fail",
        "project": None,
        "provenance": None,
        "environment": environment_summary(),
        "checks": [],
        "artifacts": None,
        "errors": errors,
        "limitations": [
            "A passing report is a reproducibility signal, not certification.",
            "The runner does not authenticate the original runtime event source or "
            "prove log completeness.",
            "Sanitized output tails still require human review before public disclosure.",
            "SHA-256 values provide integrity references, not anonymity, identity, or "
            "attestation.",
        ],
    }

    try:
        project = read_project_metadata(repository_root)
        report["project"] = project
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        project = {"name": "unknown", "version": "unknown"}
        report["project"] = project
        errors.append(f"unable to read project metadata: {exc}")

    provenance = collect_git_provenance(
        repository_root,
        expected_tag=args.expected_tag,
        expected_commit=args.expected_commit,
        allow_dirty=args.allow_dirty,
    )
    report["provenance"] = provenance
    errors.extend(provenance["errors"])

    check_definitions: list[
        tuple[str, list[str], Callable[[Any], dict[str, Any]] | None]
    ] = [
        (
            "unit_tests",
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            None,
        ),
        (
            "repository_validation",
            [sys.executable, "scripts/validate_repo.py"],
            validate_repository_result,
        ),
        (
            "local_evaluations",
            [sys.executable, "evals/run_local.py"],
            validate_evaluation_result,
        ),
        (
            "ruff",
            [sys.executable, "-m", "ruff", "check", "."],
            None,
        ),
        (
            "offline_demo",
            [sys.executable, "-m", "provable_agent_reference"],
            validate_json_object,
        ),
    ]

    checks: list[dict[str, Any]] = []
    if repository_root.is_dir():
        for name, command, validator in check_definitions:
            print(f"[external-validation] running {name}...", flush=True)
            result = run_command(
                name=name,
                command=command,
                repository_root=repository_root,
                timeout_seconds=args.timeout_seconds,
                max_output_chars=args.max_output_chars,
                json_validator=validator,
            )
            checks.append(result)
            print(
                f"[external-validation] {name}: {result['status']}",
                flush=True,
            )
            if result["status"] != "pass":
                errors.append(f"required check failed: {name}")
    else:
        errors.append(f"repository directory does not exist: {repository_root}")
    report["checks"] = checks

    artifact_version = args.expected_artifact_version
    if artifact_version is None and project["version"] != "unknown":
        artifact_version = project["version"]
    artifacts = verify_release_artifacts(
        args.release_dir,
        expected_project=(project["name"] if project["name"] != "unknown" else None),
        expected_version=artifact_version,
        required=args.require_artifacts,
    )
    if artifacts["status"] == "fail":
        errors.extend(
            f"artifact verification: {message}" for message in artifacts["errors"]
        )
    report["artifacts"] = artifacts

    report["status"] = "pass" if not errors else "fail"
    report = sanitize_structure(report, repository_root)
    report["report_sha256"] = report_digest(report)

    try:
        write_report(output_path, report)
    except OSError as exc:
        print(f"unable to write validation report: {exc}", file=sys.stderr)
        return 2

    display_output = sanitize_text(str(output_path), repository_root)
    print(f"[external-validation] report: {display_output}")
    print(f"[external-validation] report_sha256: {report['report_sha256']}")
    print(f"[external-validation] overall: {report['status']}")
    return 0 if report["status"] == "pass" else 1
