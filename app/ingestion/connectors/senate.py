from __future__ import annotations

import json
import re
from datetime import date
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.db.models.enums import Chamber, RawDocumentType, SourceSystem
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.contracts import DiscoveryBatch, RawArtifactPayload, SourceFilingListing
from app.normalization.common import parse_date


class SenateConnector(BaseConnector):
    source_system = SourceSystem.SENATE_EFD
    chamber = Chamber.SENATE
    base_url = "https://efdsearch.senate.gov"
    home_path = "/search/home/"
    search_path = "/search/"
    data_path = "/search/report/data/"
    report_type_ptr = "11"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._terms_accepted = False

    def discover_filings(
        self,
        *,
        start_date: date,
        end_date: date,
        limit: int | None = None,
    ) -> DiscoveryBatch:
        self._ensure_terms_accepted()

        run_artifacts: list[RawArtifactPayload] = []
        search_page = self.client.get(urljoin(self.base_url, self.search_path))
        search_page.raise_for_status()
        csrf_token = self._extract_csrf_token(search_page.text)
        run_artifacts.append(
            RawArtifactPayload(
                document_type=RawDocumentType.DISCOVERY_HTML,
                source_url=str(search_page.url),
                content_type=search_page.headers.get("content-type", "text/html"),
                body=search_page.content,
                filename=f"senate-search-{start_date.isoformat()}-{end_date.isoformat()}.html",
            )
        )

        search_response = self.client.post(
            urljoin(self.base_url, self.search_path),
            data={
                "report_type": self.report_type_ptr,
                "submitted_start_date": start_date.strftime("%m/%d/%Y"),
                "submitted_end_date": end_date.strftime("%m/%d/%Y"),
                "csrfmiddlewaretoken": csrf_token,
            },
            headers={"Referer": str(search_page.url)},
        )
        search_response.raise_for_status()
        run_artifacts.append(
            RawArtifactPayload(
                document_type=RawDocumentType.DISCOVERY_HTML,
                source_url=str(search_response.url),
                content_type=search_response.headers.get("content-type", "text/html"),
                body=search_response.content,
                filename=f"senate-search-results-{start_date.isoformat()}-{end_date.isoformat()}.html",
            )
        )

        page_size = 100
        listings: list[SourceFilingListing] = []
        start = 0
        total_records = None

        while total_records is None or start < total_records:
            payload = self._build_results_payload(
                start=start,
                length=page_size,
                start_date=start_date,
                end_date=end_date,
            )
            results = self.client.post(
                urljoin(self.base_url, self.data_path),
                data=payload,
                headers={
                    "Referer": urljoin(self.base_url, self.search_path),
                    "X-CSRFToken": self.client.cookies.get("csrftoken", ""),
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
            results.raise_for_status()
            payload_json = results.json()
            run_artifacts.append(
                RawArtifactPayload(
                    document_type=RawDocumentType.DISCOVERY_JSON,
                    source_url=str(results.url),
                    content_type=results.headers.get("content-type", "application/json"),
                    body=json.dumps(payload_json, indent=2).encode("utf-8"),
                    filename=f"senate-results-{start:04d}.json",
                )
            )
            total_records = int(payload_json.get("recordsFiltered", 0))
            rows = payload_json.get("data", [])
            if not rows:
                break

            for row in rows:
                listing = self._parse_listing_row(row)
                listings.append(listing)
                if limit is not None and len(listings) >= limit:
                    return DiscoveryBatch(listings=listings[:limit], run_artifacts=run_artifacts)

            start += page_size

        return DiscoveryBatch(listings=listings, run_artifacts=run_artifacts)

    def fetch_filing_artifacts(self, listing: SourceFilingListing) -> list[RawArtifactPayload]:
        self._ensure_terms_accepted()
        response = self.client.get(listing.source_url, headers={"Referer": urljoin(self.base_url, self.search_path)})
        response.raise_for_status()

        artifacts = [
            RawArtifactPayload(
                document_type=RawDocumentType.REPORT_HTML,
                source_url=listing.source_url,
                content_type=response.headers.get("content-type", "text/html"),
                body=response.content,
                filename=f"{listing.source_filing_id}.html",
                metadata={"paper_report": listing.paper_report},
            )
        ]

        if listing.paper_report:
            soup = BeautifulSoup(response.text, "lxml")
            for index, image in enumerate(soup.select("img.filingImage"), start=1):
                image_url = urljoin(self.base_url, image.get("src", ""))
                if not image_url:
                    continue
                image_response = self.client.get(image_url, headers={"Referer": str(response.url)})
                image_response.raise_for_status()
                artifacts.append(
                    RawArtifactPayload(
                        document_type=RawDocumentType.PAPER_IMAGE,
                        source_url=image_url,
                        content_type=image_response.headers.get("content-type", "image/gif"),
                        body=image_response.content,
                        filename=f"{listing.source_filing_id}-{index:02d}.gif",
                    )
                )

        return artifacts

    def _ensure_terms_accepted(self) -> None:
        if self._terms_accepted:
            return
        response = self.client.get(urljoin(self.base_url, self.home_path))
        response.raise_for_status()
        csrf_token = self._extract_csrf_token(response.text)
        accepted = self.client.post(
            urljoin(self.base_url, self.home_path),
            data={
                "prohibition_agreement": "1",
                "csrfmiddlewaretoken": csrf_token,
            },
            headers={"Referer": str(response.url)},
        )
        accepted.raise_for_status()
        self._terms_accepted = True

    @staticmethod
    def _extract_csrf_token(html: str) -> str:
        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
        if not match:
            raise ValueError("Unable to locate Senate CSRF token")
        return match.group(1)

    def _build_results_payload(
        self,
        *,
        start: int,
        length: int,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "draw": "1",
            "start": str(start),
            "length": str(length),
            "search[value]": "",
            "search[regex]": "false",
            "order[0][column]": "1",
            "order[0][dir]": "asc",
            "report_types": "[11]",
            "filer_types": "[]",
            "submitted_start_date": f"{start_date.strftime('%m/%d/%Y')} 00:00:00",
            "submitted_end_date": f"{end_date.strftime('%m/%d/%Y')} 23:59:59",
            "candidate_state": "",
            "senator_state": "",
            "office_id": "",
            "first_name": "",
            "last_name": "",
            "csrfmiddlewaretoken": self.client.cookies.get("csrftoken", ""),
        }
        for index in range(5):
            payload[f"columns[{index}][data]"] = str(index)
            payload[f"columns[{index}][name]"] = ""
            payload[f"columns[{index}][searchable]"] = "true"
            payload[f"columns[{index}][orderable]"] = "true"
            payload[f"columns[{index}][search][value]"] = ""
            payload[f"columns[{index}][search][regex]"] = "false"
        return payload

    def _parse_listing_row(self, row: list[str]) -> SourceFilingListing:
        first_name = row[0].strip() or None
        last_name = row[1].strip() or None
        office_title = row[2].strip() or None
        report_link = BeautifulSoup(row[3], "lxml").find("a")
        if report_link is None:
            raise ValueError(f"Unable to parse Senate report link from row: {row}")
        href = report_link.get("href", "")
        title = report_link.get_text(" ", strip=True)
        source_url = urljoin(self.base_url, href)
        source_filing_id = href.strip("/").split("/")[-1]
        filer_name = " ".join(part for part in [first_name, last_name] if part)
        return SourceFilingListing(
            source_system=self.source_system,
            chamber=self.chamber,
            source_filing_id=source_filing_id,
            filer_name=filer_name or office_title or "Unknown Senator",
            filer_first_name=first_name,
            filer_last_name=last_name,
            office_title=office_title,
            report_type_raw=title,
            disclosure_date=parse_date(row[4]),
            source_url=source_url,
            document_url=source_url,
            paper_report="/view/paper/" in href,
            metadata={
                "row": row,
                "document_kind": "paper" if "/view/paper/" in href else "ptr",
                "report_title": title,
            },
        )

