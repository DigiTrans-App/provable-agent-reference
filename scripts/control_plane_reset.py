from __future__ import annotations

import argparse
import os

from provable_agent_reference.control_plane.security import validate_local_reset_target


TABLES = ("artifacts", "outbox", "journal_records", "idempotency_keys", "capability_grants", "runs")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset the local synthetic control plane")
    parser.add_argument("--confirm", required=True, choices=["RESET-LOCAL-SYNTHETIC"])
    args = parser.parse_args()
    environment = os.environ.get("PAR_ENVIRONMENT", "")
    database_url = os.environ.get("PAR_DATABASE_URL", "")
    validate_local_reset_target(environment, database_url)
    import psycopg
    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            connection.execute("TRUNCATE " + ", ".join(TABLES) + " RESTART IDENTITY CASCADE")
    print("reset completed for explicit local synthetic database")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
