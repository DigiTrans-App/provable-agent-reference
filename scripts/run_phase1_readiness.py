from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from provable_agent_reference.readiness import canonicalization_baseline, phase1_conformance_report

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> str:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    output = completed.stdout + completed.stderr
    if completed.returncode != 0:
        raise RuntimeError(f"readiness command failed: {' '.join(command)}\n{output[-4000:]}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local synthetic Phase 1 readiness gate")
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, default=Path("validation-results/phase1-readiness.json"))
    args = parser.parse_args()

    test_output = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    match = re.search(r"Ran (\d+) tests?", test_output)
    if match is None:
        raise RuntimeError("could not determine reproducible test count")
    test_count = int(match.group(1))
    run([sys.executable, "scripts/validate_repo.py"])
    run(
        [
            "node",
            "typescript/verifier.ts",
            "vectors/dsse/envelope.json",
            "trust/development-trust-bundle.json",
        ]
    )
    benchmark = canonicalization_baseline()
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    report = phase1_conformance_report(
        source_revision=args.source_revision,
        test_count=test_count,
        benchmark=benchmark,
        generated_at=generated_at,
    )
    schema = json.loads(
        (ROOT / "schemas/agentic-conformance-report.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    registry = Registry()
    for schema_path in sorted((ROOT / "schemas").glob("*.schema.json")):
        candidate = json.loads(schema_path.read_text(encoding="utf-8"))
        registry = registry.with_resource(candidate["$id"], Resource.from_contents(candidate))
    errors = sorted(
        Draft202012Validator(schema, registry=registry).iter_errors(report),
        key=lambda error: list(error.path),
    )
    if errors:
        details = "; ".join(
            f"{'.'.join(map(str, error.path)) or '<root>'}: {error.message}" for error in errors
        )
        raise RuntimeError(f"Phase 1 conformance report is invalid: {details}")
    result = {"benchmark": benchmark, "conformance": report, "test_count": test_count}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
