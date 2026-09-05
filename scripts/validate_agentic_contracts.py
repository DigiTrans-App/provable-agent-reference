"""Validate experimental Phase 1 agentic contracts and adversarial vectors."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

POSITIVE_EXAMPLE_SCHEMA_MAP = {
    "agent-activity-delegation.example.json": "agent-activity-record.schema.json",
    "agent-activity-lifecycle.example.json": "agent-activity-record.schema.json",
    "agent-activity-memory.example.json": "agent-activity-record.schema.json",
    "agent-activity-policy.example.json": "agent-activity-record.schema.json",
    "agent-activity-tool.example.json": "agent-activity-record.schema.json",
    "agentic-conformance-report.example.json": "agentic-conformance-report.schema.json",
    "agentic-negative-vectors.example.json": "agentic-negative-vector-set.schema.json",
    "agentic-semantic-negative-vectors.example.json": "agentic-semantic-vector-set.schema.json",
    "dsse-assurance-envelope.example.json": "dsse-assurance-envelope.schema.json",
    "execution-receipt.example.json": "execution-receipt.schema.json",
    "reconciliation-record.example.json": "reconciliation-record.schema.json",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry_for(schemas: dict[str, dict[str, Any]]) -> Registry:
    registry = Registry()
    for schema in schemas.values():
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return registry


def _semantic_rule_passes(rule: str, records: list[dict[str, Any]]) -> bool:
    if rule == "same_case_scope":
        return (
            len(
                {(record.get("tenant_id"), record.get("case_id")) for record in records}
            )
            == 1
        )
    if rule == "unique_event_identity":
        event_ids = [record["event_id"] for record in records]
        return len(event_ids) == len(set(event_ids))
    if rule == "monotonic_run_sequence":
        last_by_run: dict[str, int] = {}
        for record in records:
            run_id = record["run_id"]
            sequence = record["sequence"]
            if run_id in last_by_run and sequence != last_by_run[run_id] + 1:
                return False
            last_by_run[run_id] = sequence
        return True
    if rule == "previous_hash_chain":
        previous_by_run: dict[str, dict[str, Any]] = {}
        for record in records:
            run_id = record["run_id"]
            previous = previous_by_run.get(run_id)
            if previous is None and record["previous_event_hash"] is not None:
                return False
            if (
                previous is not None
                and record["previous_event_hash"] != previous["record_hash"]
            ):
                return False
            previous_by_run[run_id] = record
        return True
    if rule == "receipt_reconciliation_binding":
        receipt, reconciliation = records
        return (
            receipt["tenant_id"] == reconciliation["tenant_id"]
            and receipt["case_id"] == reconciliation["case_id"]
            and receipt["run_id"] == reconciliation["run_id"]
            and receipt["receipt_id"] == reconciliation["receipt_id"]
            and receipt["record_hash"] == reconciliation["receipt_hash"]
        )
    if rule == "delegation_attenuation":
        parent, child = (record["body"] for record in records)
        return (
            set(child["capability_grant"]).issubset(parent["capability_grant"])
            and child["budget"]["max_tool_calls"] <= parent["budget"]["max_tool_calls"]
            and child["budget"]["max_model_calls"] <= parent["budget"]["max_model_calls"]
            and child["valid_until"] <= parent["valid_until"]
        )
    if rule == "idempotency_input_binding":
        bindings: dict[str, tuple[str, str, str]] = {}
        for record in records:
            key = record["idempotency_key_commitment"]
            value = (
                record["authorization_hash"],
                record["action_hash"],
                record["target_ref"],
            )
            if key in bindings and bindings[key] != value:
                return False
            bindings[key] = value
        return True
    if rule == "receipt_time_order":
        for record in records:
            values = [
                record[name]
                for name in ("submitted_at", "acknowledged_at", "observed_at", "reconciled_at")
                if record[name] is not None
            ]
            if values != sorted(values):
                return False
        return True
    if rule == "unknown_effect_retry_blocked":
        by_operation: dict[str, bool] = {}
        for record in sorted(records, key=lambda value: value["attempt_number"]):
            operation_id = record["operation_id"]
            if by_operation.get(operation_id):
                return False
            if record["effect_status"] == "unknown":
                by_operation[operation_id] = True
        return True
    raise ValueError(f"unsupported semantic rule: {rule}")


def _format_errors(errors: list[Any]) -> str:
    details = []
    for error in errors[:5]:
        location = "/" + "/".join(str(part) for part in error.absolute_path)
        details.append(f"{location}: {error.message}")
    return "; ".join(details)


def _decode_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _apply_mutation(document: Any, mutation: dict[str, Any]) -> None:
    tokens = [_decode_pointer_token(token) for token in mutation["path"].split("/")[1:]]
    if not tokens:
        raise ValueError("mutating the document root is not supported")

    parent = document
    for token in tokens[:-1]:
        if isinstance(parent, list):
            parent = parent[int(token)]
        else:
            parent = parent[token]

    final = tokens[-1]
    operation = mutation["operation"]
    if isinstance(parent, list):
        index = int(final)
        if operation == "add":
            if index > len(parent):
                raise IndexError(f"array add index {index} is out of range")
            parent.insert(index, mutation["value"])
        elif operation == "replace":
            parent[index] = mutation["value"]
        elif operation == "remove":
            parent.pop(index)
        else:
            raise ValueError(f"unsupported mutation operation: {operation}")
        return

    if operation == "add":
        parent[final] = mutation["value"]
    elif operation == "replace":
        if final not in parent:
            raise KeyError(f"replace target does not exist: {mutation['path']}")
        parent[final] = mutation["value"]
    elif operation == "remove":
        if final not in parent:
            raise KeyError(f"remove target does not exist: {mutation['path']}")
        del parent[final]
    else:
        raise ValueError(f"unsupported mutation operation: {operation}")


def validate_agentic_contracts(
    root: Path,
    schemas: dict[str, dict[str, Any]] | None = None,
    registry: Registry | None = None,
) -> dict[str, int]:
    """Validate positive examples and prove that every negative vector fails closed."""

    schema_dir = root / "schemas"
    example_dir = root / "examples" / "records"
    if schemas is None:
        schemas = {
            path.name: _load_json(path)
            for path in sorted(schema_dir.glob("*.schema.json"))
        }
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    if registry is None:
        registry = _registry_for(schemas)

    format_checker = FormatChecker()
    for example_name, schema_name in POSITIVE_EXAMPLE_SCHEMA_MAP.items():
        example = _load_json(example_dir / example_name)
        validator = Draft202012Validator(
            schemas[schema_name], registry=registry, format_checker=format_checker
        )
        errors = list(validator.iter_errors(example))
        if errors:
            raise ValueError(
                f"{example_name} does not validate against {schema_name}: "
                f"{_format_errors(errors)}"
            )

    vector_set = _load_json(example_dir / "agentic-negative-vectors.example.json")
    seen_case_ids: set[str] = set()
    for case in vector_set["cases"]:
        case_id = case["case_id"]
        if case_id in seen_case_ids:
            raise ValueError(f"duplicate negative-vector case_id: {case_id}")
        seen_case_ids.add(case_id)

        schema_name = case["schema"]
        base_example_name = case["base_example"]
        if schema_name not in schemas:
            raise ValueError(f"{case_id} references unknown schema: {schema_name}")
        base_path = example_dir / base_example_name
        if not base_path.is_file():
            raise ValueError(
                f"{case_id} references unknown example: {base_example_name}"
            )

        mutated = copy.deepcopy(_load_json(base_path))
        for mutation in case["mutations"]:
            _apply_mutation(mutated, mutation)

        validator = Draft202012Validator(
            schemas[schema_name], registry=registry, format_checker=format_checker
        )
        errors = list(validator.iter_errors(mutated))
        if not errors:
            raise ValueError(
                f"negative vector {case_id} unexpectedly validated against {schema_name}"
            )

    semantic_vector_set = _load_json(
        example_dir / "agentic-semantic-negative-vectors.example.json"
    )
    for case in semantic_vector_set["cases"]:
        case_id = case["case_id"]
        if case_id in seen_case_ids:
            raise ValueError(f"duplicate vector case_id: {case_id}")
        seen_case_ids.add(case_id)

        records = []
        for record_spec in case["records"]:
            example_name = record_spec["example"]
            if example_name not in POSITIVE_EXAMPLE_SCHEMA_MAP:
                raise ValueError(
                    f"{case_id} references unknown example: {example_name}"
                )
            record = copy.deepcopy(_load_json(example_dir / example_name))
            for mutation in record_spec["mutations"]:
                _apply_mutation(record, mutation)

            schema_name = POSITIVE_EXAMPLE_SCHEMA_MAP[example_name]
            validator = Draft202012Validator(
                schemas[schema_name], registry=registry, format_checker=format_checker
            )
            errors = list(validator.iter_errors(record))
            if errors:
                raise ValueError(
                    f"semantic vector {case_id} is not schema-valid after mutation: "
                    f"{_format_errors(errors)}"
                )
            records.append(record)

        if _semantic_rule_passes(case["semantic_rule"], records):
            raise ValueError(
                f"semantic vector {case_id} unexpectedly passed {case['semantic_rule']}"
            )

    return {
        "positive_examples": len(POSITIVE_EXAMPLE_SCHEMA_MAP),
        "negative_vectors": len(vector_set["cases"]),
        "semantic_negative_vectors": len(semantic_vector_set["cases"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the parent of scripts/)",
    )
    args = parser.parse_args()
    result = validate_agentic_contracts(args.root.resolve())
    print(json.dumps({"agentic_contracts": result}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
