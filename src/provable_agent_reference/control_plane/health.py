from __future__ import annotations

import os


def main() -> int:
    database_url = os.environ.get("PAR_DATABASE_URL")
    if not database_url:
        raise SystemExit("PAR_DATABASE_URL is required")
    try:
        import psycopg
        with psycopg.connect(database_url, connect_timeout=2) as connection:
            value = connection.execute("SELECT 1").fetchone()
    except Exception as exc:
        raise SystemExit(f"control-plane dependency health failed: {type(exc).__name__}") from exc
    if value != (1,):
        raise SystemExit("unexpected PostgreSQL health response")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
