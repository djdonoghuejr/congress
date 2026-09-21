from __future__ import annotations

from io import BytesIO
from typing import Any
from urllib.parse import urljoin
from xml.etree import ElementTree
from zipfile import ZipFile

from app.db.models.enums import Chamber, RawDocumentType, SourceSystem
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.contracts import DiscoveryBatch, RawArtifactPayload, SourceFilingListing
from app.normalization.common import parse_date


class HouseConnector(BaseConnector):
    source_system = SourceSystem.HOUSE_CLERK
    chamber = Chamber.HOUSE
    base_url = "https://disclosures-clerk.house.gov"

    def discover_filings(self, *, year: int, limit: int | None = None) -> DiscoveryBatch:
        zip_path = f"/public_disc/financial-pdfs/{year}FD.zip"
        zip_url = urljoin(self.base_url, zip_path)
        response = self.client.get(zip_url)
        response.raise_for_status()

        run_artifacts = [
            RawArtifactPayload(
                document_type=RawDocumentType.DISCOVERY_ZIP,
                source_url=zip_url,
                content_type=response.headers.get("content-type", "application/zip"),
                body=response.content,
                filename=f"{year}FD.zip",
            )
        ]

        with ZipFile(BytesIO(response.content)) as archive:
            xml_name = next(name for name in archive.namelist() if name.lower().endswith(".xml"))
            xml_bytes = archive.read(xml_name)

        run_artifacts.append(
            RawArtifactPayload(
                document_type=RawDocumentType.INDEX_XML,
                source_url=zip_url,
                content_type="application/xml",
                body=xml_bytes,
                filename=xml_name,
            )
        )

        root = ElementTree.fromstring(xml_bytes.decode("utf-8-sig"))
        listings: list[SourceFilingListing] = []

        for member in root.findall("Member"):
            filing_type = (member.findtext("FilingType") or "").strip()
            if filing_type != "P":
                continue
            doc_id = (member.findtext("DocID") or "").strip()
            if not doc_id:
                continue
            prefix = (member.findtext("Prefix") or "").strip() or None
            first_name = (member.findtext("First") or "").strip() or None
            last_name = (member.findtext("Last") or "").strip() or None
            suffix = (member.findtext("Suffix") or "").strip() or None
            state_district = (member.findtext("StateDst") or "").strip() or None
            pdf_url = urljoin(self.base_url, f"/public_disc/ptr-pdfs/{year}/{doc_id}.pdf")
            raw_name_parts = [prefix, first_name, last_name, suffix]
            filer_name = " ".join(part for part in raw_name_parts if part)
            state = state_district[:2] if state_district and len(state_district) >= 2 else None
            district = state_district[2:] if state_district and len(state_district) > 2 else None
            listings.append(
                SourceFilingListing(
                    source_system=self.source_system,
                    chamber=self.chamber,
                    source_filing_id=f"{year}-{doc_id}",
                    filer_name=filer_name,
                    filer_first_name=first_name,
                    filer_last_name=last_name,
                    office_title="Representative",
                    state=state,
                    district=district,
                    report_type_raw=filing_type,
                    disclosure_date=parse_date(member.findtext("FilingDate")),
                    source_url=pdf_url,
                    document_url=pdf_url,
                    filing_year=year,
                    metadata={
                        "doc_id": doc_id,
                        "prefix": prefix,
                        "suffix": suffix,
                        "state_district": state_district,
                    },
                )
            )
            if limit is not None and len(listings) >= limit:
                break

        return DiscoveryBatch(listings=listings, run_artifacts=run_artifacts)

    def fetch_filing_artifacts(self, listing: SourceFilingListing) -> list[RawArtifactPayload]:
        response = self.client.get(listing.source_url)
        response.raise_for_status()
        return [
            RawArtifactPayload(
                document_type=RawDocumentType.REPORT_PDF,
                source_url=listing.source_url,
                content_type=response.headers.get("content-type", "application/pdf"),
                body=response.content,
                filename=f"{listing.source_filing_id}.pdf",
                metadata={"house_doc_id": listing.metadata.get("doc_id")},
            )
        ]
