from __future__ import annotations

import json

from provable_agent_reference.demo import run_demo

if __name__ == "__main__":
    print(json.dumps(run_demo().to_dict(), indent=2, sort_keys=True))
