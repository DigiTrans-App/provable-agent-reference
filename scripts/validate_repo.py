from __future__ import annotations

import compileall
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def validate_json_files() -> int:
    count = 0
    for path in sorted(ROOT.rglob("*.json")):
        if "evals/results" in path.as_posix():
            continue
        json.loads(path.read_text(encoding="utf-8"))
        count += 1
    return count


def _references(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "$ref" and isinstance(item, str):
                yield item
            else:
                yield from _references(item)
    elif isinstance(value, list):
        for item in value:
            yield from _references(item)


def validate_schemas() -> int:
    schema_dir = ROOT / "schemas"
    paths = sorted(schema_dir.glob("*.schema.json"))
    for path in paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        for reference in _references(schema):
            if reference.startswith(("#", "http://", "https://")):
                continue
            target = (path.parent / reference.split("#", 1)[0]).resolve()
            if not target.exists():
                raise RuntimeError(
                    f"unresolved schema reference: {path.relative_to(ROOT)} -> {reference}"
                )
    return len(paths)


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
    leaks = []
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in suffixes:
            if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                leaks.append(path.relative_to(ROOT).as_posix())
    if leaks:
        raise RuntimeError("possible API key pattern found in: " + ", ".join(leaks))


def main() -> int:
    result = {
        "json_files": validate_json_files(),
        "schemas": validate_schemas(),
        "markdown_links": validate_markdown_links(),
        "compiled": compileall.compile_dir(ROOT / "src", quiet=1),
    }
    validate_secret_hygiene()
    result["secret_hygiene"] = "pass"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["compiled"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
