from __future__ import annotations

import hashlib
import re
from pathlib import Path
from uuid import UUID

from app.core.config import Settings
from app.db.models.enums import SourceSystem
from app.ingestion.contracts import RawArtifactPayload


SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(value: str) -> str:
    return SAFE_FILENAME_RE.sub("-", value).strip("-") or "artifact"


class RawArtifactStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def store(
        self,
        artifact: RawArtifactPayload,
        *,
        source_system: SourceSystem,
        filing_id: UUID | None = None,
        ingestion_run_id: UUID | None = None,
    ) -> tuple[str, str]:
        digest = hashlib.sha256(artifact.body).hexdigest()
        filename = sanitize_filename(artifact.filename)
        namespace = filing_id or ingestion_run_id or "shared"
        directory = self.settings.raw_storage_dir / source_system.value / str(namespace)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{digest[:12]}-{filename}"
        if not path.exists():
            path.write_bytes(artifact.body)
        return str(path), digest
