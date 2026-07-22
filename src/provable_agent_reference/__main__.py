from __future__ import annotations

import json

from .demo import run_demo


def main() -> None:
    print(json.dumps(run_demo().to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
