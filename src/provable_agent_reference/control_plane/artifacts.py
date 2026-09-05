from __future__ import annotations

import hashlib
import os
from pathlib import Path


class LocalArtifactStore:
    """Content-addressed local artifact store with staged atomic publication."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.staging = self.root / ".staging"
        self.staging.mkdir(parents=True, exist_ok=True)

    def publish(self, content: bytes, expected_digest: str | None = None) -> str:
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        if expected_digest is not None and expected_digest != digest:
            raise ValueError("artifact digest mismatch")
        hex_digest = digest.split(":", 1)[1]
        target = self.root / "sha256" / hex_digest[:2] / hex_digest
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != hex_digest:
                raise RuntimeError("existing artifact failed integrity verification")
            return digest
        staged = self.staging / f"{hex_digest}.{os.getpid()}.tmp"
        try:
            with staged.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if hashlib.sha256(staged.read_bytes()).hexdigest() != hex_digest:
                raise RuntimeError("staged artifact failed integrity verification")
            os.replace(staged, target)
            target.chmod(0o444)
        finally:
            staged.unlink(missing_ok=True)
        return digest

    def read(self, digest: str) -> bytes:
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise ValueError("invalid sha256 digest")
        hex_digest = digest.split(":", 1)[1]
        path = self.root / "sha256" / hex_digest[:2] / hex_digest
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != hex_digest:
            raise RuntimeError("artifact integrity verification failed")
        return content
