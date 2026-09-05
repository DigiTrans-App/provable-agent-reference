from __future__ import annotations

import compileall
import json
import re
import tomllib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from validate_agentic_contracts import validate_agentic_contracts

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
EXAMPLE_DIR = ROOT / "examples" / "records"
GENERATED_DIRECTORIES = {"evals/results", "validation-results"}
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
        "agentic_contracts": validate_agentic_contracts(ROOT, schemas, registry),
        "json_files": validate_json_files(),
        "markdown_links": validate_markdown_links(),
        "compiled_roots": compile_python(),
    }
    validate_secret_hygiene()
    result["secret_hygiene"] = "pass"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
