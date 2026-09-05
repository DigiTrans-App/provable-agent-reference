from __future__ import annotations

import compileall
import json
import re
import tomllib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
EXAMPLE_DIR = ROOT / "examples" / "records"
GENERATED_DIRECTORIES = {"evals/results", "validation-results"}
PINNED_ACTION_PATTERN = re.compile(
    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
    r"(?:/[A-Za-z0-9_.-]+)*@[0-9a-f]{40}$"
)
USES_PATTERN = re.compile(r"^\s*(?:-\s*)?uses:\s*['\"]?([^'\"\s#]+)['\"]?\s*$")
PULL_REQUEST_TARGET_KEY_PATTERN = re.compile(
    r"^\s*['\"]?pull_request_target['\"]?\s*:"
)
EXAMPLE_SCHEMA_MAP = {
    "assurance-packet.example.json": "assurance-packet.schema.json",
    "semantic-draft.example.json": "semantic-draft.schema.json",
    "evidence-record.example.json": "evidence-record.schema.json",
    "evidence-bundle.example.json": "evidence-bundle.schema.json",
    "canonical-candidate.example.json": "canonical-candidate.schema.json",
    "verification-result.example.json": "verification-result.schema.json",
    "approval-record.example.json": "approval-record.schema.json",
    "authorization-result.example.json": "authorization-result.schema.json",
    "audit-manifest.example.json": "audit-manifest.schema.json",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def is_generated_path(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    return any(
        relative == directory or relative.startswith(directory + "/")
        for directory in GENERATED_DIRECTORIES
    )


def build_registry() -> tuple[dict[str, dict[str, Any]], Registry]:
    schemas: dict[str, dict[str, Any]] = {}
    registry = Registry()
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        schemas[path.name] = schema
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return schemas, registry


def validate_examples(
    schemas: dict[str, dict[str, Any]], registry: Registry
) -> int:
    for example_name, schema_name in EXAMPLE_SCHEMA_MAP.items():
        record = load_json(EXAMPLE_DIR / example_name)
        errors = sorted(
            Draft202012Validator(
                schemas[schema_name],
                registry=registry,
            ).iter_errors(record),
            key=lambda error: list(error.path),
        )
        if errors:
            details = "; ".join(
                f"{'.'.join(map(str, error.path)) or '<root>'}: {error.message}"
                for error in errors
            )
            raise RuntimeError(
                f"{example_name} failed {schema_name}: {details}"
            )
    return len(EXAMPLE_SCHEMA_MAP)


def validate_json_files() -> int:
    count = 0
    for path in sorted(ROOT.rglob("*.json")):
        if is_generated_path(path):
            continue
        load_json(path)
        count += 1
    return count


def validate_markdown_links() -> int:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    count = 0
    for path in sorted(ROOT.rglob("*.md")):
        for target in pattern.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            relative = target.split("#", 1)[0]
            if not relative:
                continue
            resolved = (path.parent / relative).resolve()
            if not resolved.exists():
                raise RuntimeError(
                    f"broken relative link: {path.relative_to(ROOT)} -> {target}"
                )
            count += 1
    return count


def validate_workflow_security(root: Path = ROOT) -> int:
    """Reject GitHub workflow constructs that weaken source integrity."""
    workflow_dir = root / ".github" / "workflows"
    action_count = 0

    for path in sorted((*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml"))):
        lines = path.read_text(encoding="utf-8").splitlines()
        relative = path.relative_to(root)

        for index, raw_line in enumerate(lines):
            line = raw_line.split("#", 1)[0].rstrip()
            if not line:
                continue
            inline_unsafe_trigger = re.match(
                r"^\s*['\"]?on['\"]?\s*:", line
            ) and re.search(
                r"\bpull_request_target\b", line
            )
            if PULL_REQUEST_TARGET_KEY_PATTERN.match(line) or inline_unsafe_trigger:
                raise RuntimeError(
                    f"unsafe pull_request_target trigger: {relative}:{index + 1}"
                )

            match = USES_PATTERN.match(line)
            if match is None:
                continue
            action = match.group(1)
            if action.startswith("./"):
                continue
            if PINNED_ACTION_PATTERN.fullmatch(action) is None:
                raise RuntimeError(
                    "external action is not pinned to a full commit SHA: "
                    f"{relative}:{index + 1} ({action})"
                )

            action_count += 1
            if not action.lower().startswith("actions/checkout@"):
                continue

            action_indent = len(raw_line) - len(raw_line.lstrip())
            step_lines: list[str] = []
            for following_line in lines[index + 1 :]:
                stripped = following_line.lstrip()
                following_indent = len(following_line) - len(stripped)
                if stripped.startswith("- ") and following_indent <= action_indent:
                    break
                step_lines.append(following_line.split("#", 1)[0])

            persisted = False
            for step_index, step_line in enumerate(step_lines):
                without_comment = step_line.split("#", 1)[0].rstrip()
                if not re.match(r"^\s*with\s*:\s*$", without_comment):
                    continue
                with_indent = len(step_line) - len(step_line.lstrip())
                for input_line in step_lines[step_index + 1 :]:
                    input_without_comment = input_line.split("#", 1)[0].rstrip()
                    if not input_without_comment:
                        continue
                    input_indent = len(input_line) - len(input_line.lstrip())
                    if input_indent <= with_indent:
                        break
                    if re.match(
                        r"^\s*persist-credentials:\s*['\"]?false['\"]?\s*$",
                        input_without_comment,
                        flags=re.IGNORECASE,
                    ):
                        persisted = True
                        break
                if persisted:
                    break
            if not persisted:
                raise RuntimeError(
                    "actions/checkout must set persist-credentials: false: "
                    f"{relative}:{index + 1}"
                )

    return action_count


def validate_secret_hygiene() -> None:
    pattern = re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}")
    suffixes = {".py", ".md", ".json", ".toml", ".yml", ".yaml", ".txt"}
    leaks: list[str] = []
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or path.suffix.lower() not in suffixes
            or is_generated_path(path)
        ):
            continue
        if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
            leaks.append(path.relative_to(ROOT).as_posix())
    if leaks:
        raise RuntimeError("possible API key pattern found in: " + ", ".join(leaks))


def validate_version_metadata() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    version = str(project["version"])

    init_text = (
        ROOT / "src" / "provable_agent_reference" / "__init__.py"
    ).read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"$', init_text, flags=re.MULTILINE)
    if match is None:
        raise RuntimeError("package __version__ declaration was not found")
    if match.group(1) != version:
        raise RuntimeError(
            f"version mismatch: pyproject.toml={version}, package={match.group(1)}"
        )

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{version}]" not in changelog:
        raise RuntimeError(f"CHANGELOG.md has no section for {version}")

    release_notes = ROOT / "docs" / "releases" / f"v{version}.md"
    if not release_notes.is_file():
        raise RuntimeError(f"release notes not found: {release_notes.relative_to(ROOT)}")

    return version


def compile_python() -> int:
    roots = [ROOT / "src", ROOT / "scripts", ROOT / "evals", ROOT / "examples"]
    passed = 0
    for root in roots:
        if root.exists():
            if not compileall.compile_dir(root, quiet=1):
                raise RuntimeError(f"bytecode compilation failed under {root}")
            passed += 1
    return passed


def main() -> int:
    schemas, registry = build_registry()
    result = {
        "version": validate_version_metadata(),
        "schemas": len(schemas),
        "examples": validate_examples(schemas, registry),
        "json_files": validate_json_files(),
        "markdown_links": validate_markdown_links(),
        "workflow_actions": validate_workflow_security(),
        "compiled_roots": compile_python(),
    }
    validate_secret_hygiene()
    result["secret_hygiene"] = "pass"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
