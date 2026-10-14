from __future__ import annotations

import os
from pathlib import Path


def main() -> int:
    database_url = os.environ.get("PAR_DATABASE_URL", "")
    if not database_url:
        raise SystemExit("PAR_DATABASE_URL is required")
    import psycopg

    root = Path(__file__).resolve().parents[1]
    migrations = sorted((root / "migrations").glob("*.sql"))
    if not migrations:
        raise SystemExit("no migrations found")
    with psycopg.connect(database_url) as connection:
        for path in migrations:
            connection.execute(path.read_text(encoding="utf-8"))
    print(f"applied {len(migrations)} control-plane migration file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
