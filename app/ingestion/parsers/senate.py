from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.ingestion.contracts import ParsedFilingBundle, ParsedTransaction, RawArtifactPayload, SourceFilingListing
from app.ingestion.parsers.base import BaseParser
from app.db.models.enums import RawDocumentType
from app.normalization.common import collapse_whitespace


FILED_AT_RE = re.compile(r"Filed\s+(\d{2}/\d{2}/\d{4}(?:\s*@\s*[\d:]+\s*[AP]M)?)", re.IGNORECASE)


class SenateParser(BaseParser):
    def parse(
        self,
        listing: SourceFilingListing,
        artifacts: list[RawArtifactPayload],
    ) -> ParsedFilingBundle:
        html_artifact = next(
            artifact for artifact in artifacts if artifact.document_type == RawDocumentType.REPORT_HTML
        )
        html = html_artifact.body.decode("utf-8", "ignore")
        soup = BeautifulSoup(html, "lxml")
        page_text = soup.get_text("\n", strip=True)

        filed_at_match = FILED_AT_RE.search(page_text)
        filed_at_raw = filed_at_match.group(1) if filed_at_match else None

        transactions: list[ParsedTransaction] = []
        table = soup.find("table", class_="table")
        if table is not None:
            for row in table.select("tbody tr"):
                cells = row.find_all("td")
                if len(cells) < 9:
                    continue
                ticker_link = cells[3].find("a")
                transactions.append(
                    ParsedTransaction(
                        sequence_number=int(cells[0].get_text(" ", strip=True)),
                        transaction_date_raw=collapse_whitespace(cells[1].get_text(" ", strip=True)),
                        disclosure_date_raw=(
                            listing.disclosure_date.strftime("%m/%d/%Y")
                            if listing.disclosure_date
                            else None
                        ),
                        owner_raw=collapse_whitespace(cells[2].get_text(" ", strip=True)),
                        ticker_raw=collapse_whitespace(
                            ticker_link.get_text(" ", strip=True)
                            if ticker_link is not None
                            else cells[3].get_text(" ", strip=True)
                        ),
                        asset_name_raw=collapse_whitespace(cells[4].get_text(" ", strip=True)) or "",
                        asset_type_raw=collapse_whitespace(cells[5].get_text(" ", strip=True)),
                        transaction_type_raw=collapse_whitespace(cells[6].get_text(" ", strip=True)) or "",
                        amount_range_raw=collapse_whitespace(cells[7].get_text(" ", strip=True)),
                        comment_raw=collapse_whitespace(cells[8].get_text(" ", strip=True)),
                        raw_payload={
                            "cells": [collapse_whitespace(cell.get_text(" ", strip=True)) for cell in cells],
                        },
                    )
                )

        return ParsedFilingBundle(
            report_type_raw=listing.report_type_raw,
            filed_at_raw=filed_at_raw,
            transactions=transactions,
            metadata={"paper_report": listing.paper_report},
        )

