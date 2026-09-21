from __future__ import annotations

from abc import ABC, abstractmethod

from app.ingestion.contracts import ParsedFilingBundle, RawArtifactPayload, SourceFilingListing


class BaseParser(ABC):
    @abstractmethod
    def parse(
        self,
        listing: SourceFilingListing,
        artifacts: list[RawArtifactPayload],
    ) -> ParsedFilingBundle:
        raise NotImplementedError

