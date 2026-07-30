from __future__ import annotations

import json
from pathlib import Path

from provable_agent_reference.adapters import AdapterContext, CodexEvidenceAdapter

HERE = Path(__file__).resolve().parent


def main() -> int:
    result = CodexEvidenceAdapter().build_evidence(
        context=AdapterContext(
            tenant_id="tenant_demo",
            case_id="case_demo",
            run_id="run_codex_demo",
            created_at="2026-07-30T00:00:00Z",
            classification="internal",
        ),
        execution_jsonl=(HERE / "fixtures" / "codex_exec.synthetic.jsonl").read_text(
            encoding="utf-8"
        ),
        telemetry_jsonl=(HERE / "fixtures" / "codex_otel.synthetic.jsonl").read_text(
            encoding="utf-8"
        ),
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
