from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.core.config import Settings, get_settings
from app.db.models.enums import Chamber, SourceSystem
from app.ingestion.contracts import DiscoveryBatch, RawArtifactPayload, SourceFilingListing


class BaseConnector(ABC):
    source_system: SourceSystem
    chamber: Chamber

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None) -> None:
        self.settings = settings or get_settings()
        self._owns_client = client is None
        self.client = client or httpx.Client(
            headers={"User-Agent": self.settings.user_agent},
            follow_redirects=True,
            timeout=self.settings.http_timeout_seconds,
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    @abstractmethod
    def discover_filings(self, **kwargs) -> DiscoveryBatch:
        raise NotImplementedError

    @abstractmethod
    def fetch_filing_artifacts(self, listing: SourceFilingListing) -> list[RawArtifactPayload]:
        raise NotImplementedError

