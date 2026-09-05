from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


LOCAL_HOSTS = {"localhost", "postgres", "127.0.0.1", "::1"}


def validate_local_reset_target(environment: str, database_url: str) -> None:
    """Fail closed unless reset targets the explicit local synthetic profile."""
    if environment != "local-synthetic":
        raise RuntimeError("reset requires PAR_ENVIRONMENT=local-synthetic")
    parsed = urlparse(database_url)
    host = parsed.hostname
    database = parsed.path.removeprefix("/")
    if host not in LOCAL_HOSTS:
        try:
            if not ipaddress.ip_address(host or "").is_loopback:
                raise RuntimeError("reset database host is not local")
        except ValueError as exc:
            raise RuntimeError("reset database host is not local") from exc
    if not database.endswith("_synthetic"):
        raise RuntimeError("reset database name must end with _synthetic")
