from __future__ import annotations

import argparse
import json
from pathlib import Path

from provable_agent_reference.dsse import sign_assurance_packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a development-only DSSE test vector")
    parser.add_argument("packet", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    args.output.write_text(json.dumps(sign_assurance_packet(packet), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
