from __future__ import annotations

import re
from io import BytesIO

from pypdf import PdfReader

from app.db.models.enums import RawDocumentType
from app.ingestion.contracts import ParsedFilingBundle, ParsedTransaction, RawArtifactPayload, SourceFilingListing
from app.ingestion.parsers.base import BaseParser
from app.normalization.common import collapse_whitespace


ROW_RE = re.compile(
    r"^(?:(?P<owner>[A-Z]{1,3})\s+)?(?P<transaction>[A-Z]{1,2})\s+"
    r"(?P<transaction_date>\d{2}/\d{2}/\d{4})\s*"
    r"(?P<disclosure_date>\d{2}/\d{2}/\d{4})\s*"
    r"(?P<amount>.+)$"
)
FILED_AT_RE = re.compile(r"Digitally Signed:\s*(?P<name>.+?)\s*,\s*(?P<date>\d{2}/\d{2}/\d{4})")
TICKER_RE = re.compile(r"\((?P<ticker>[A-Z.\-]+)\)\s*\[(?P<asset_type>[A-Z]+)\]\s*$")


class HouseParser(BaseParser):
    def parse(
        self,
        listing: SourceFilingListing,
        artifacts: list[RawArtifactPayload],
    ) -> ParsedFilingBundle:
        pdf_artifact = next(
            artifact for artifact in artifacts if artifact.document_type == RawDocumentType.REPORT_PDF
        )
        reader = PdfReader(BytesIO(pdf_artifact.body))
        raw_text = "\n".join((page.extract_text() or "") for page in reader.pages)
        clean_text = raw_text.replace("\x00", "")
        lines = [collapse_whitespace(line) for line in clean_text.splitlines()]
        lines = [line for line in lines if line]

        filed_at_raw = None
        if match := FILED_AT_RE.search(clean_text):
            filed_at_raw = match.group("date")

        transactions: list[ParsedTransaction] = []
        asset_buffer: list[str] = []
        in_table = False

        for line in lines:
            if line == "$200?":
                in_table = True
                continue
            if not in_table:
                continue
            if line.startswith("* For the complete list"):
                break
            if line.lower().startswith("filing status") or re.match(r"^f\s*s\s*:", line, re.IGNORECASE):
                continue
            if match := ROW_RE.match(line):
                asset_text = " ".join(asset_buffer).strip()
                asset_buffer = []
                ticker_match = TICKER_RE.search(asset_text)
                ticker = ticker_match.group("ticker") if ticker_match else None
                asset_type = ticker_match.group("asset_type") if ticker_match else None
                transactions.append(
                    ParsedTransaction(
                        sequence_number=len(transactions) + 1,
                        transaction_date_raw=match.group("transaction_date"),
                        disclosure_date_raw=match.group("disclosure_date"),
                        owner_raw=match.group("owner"),
                        ticker_raw=ticker,
                        asset_name_raw=asset_text or "Unknown Asset",
                        asset_type_raw=asset_type,
                        transaction_type_raw=match.group("transaction"),
                        amount_range_raw=collapse_whitespace(match.group("amount")),
                        comment_raw=None,
                        raw_payload={"row": line, "asset_text": asset_text},
                    )
                )
            else:
                asset_buffer.append(line)

        return ParsedFilingBundle(
            report_type_raw=listing.report_type_raw,
            filed_at_raw=filed_at_raw,
            transactions=transactions,
            metadata={"page_count": len(reader.pages)},
        )
