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


class ArtifactReconciler:
    """Reconcile staged metadata against verified content-addressed bytes."""

    def __init__(self, store, artifacts: LocalArtifactStore, worker_id: str) -> None:
        if not worker_id:
            raise ValueError("worker_id is required")
        self.store = store
        self.artifacts = artifacts
        self.worker_id = worker_id

    def run_once(self, limit: int = 50) -> tuple[int, int, int]:
        available = unavailable = retried = 0
        for item in self.store.claim_artifacts(self.worker_id, limit):
            digest = item["digest"]
            try:
                content = self.artifacts.read(digest)
                if len(content) != item["byte_length"]:
                    raise RuntimeError("artifact byte length mismatch")
            except (FileNotFoundError, RuntimeError):
                self.store.unavailable_artifact(
                    digest, self.worker_id, "artifact bytes missing or failed verification"
                )
                unavailable += 1
            except OSError:
                delay = min(2 ** min(item["attempts"], 10), 3600)
                self.store.retry_artifact(
                    digest, self.worker_id, "artifact storage temporarily unavailable", delay
                )
                retried += 1
            else:
                self.store.finalize_artifact(digest, item["storage_key"], self.worker_id)
                available += 1
        return available, unavailable, retried
