from __future__ import annotations

from pathlib import Path

from app.db.models.enums import Chamber, RawDocumentType, SourceSystem
from app.ingestion.contracts import RawArtifactPayload, SourceFilingListing
from app.ingestion.parsers.house import HouseParser
from app.ingestion.parsers.senate import SenateParser


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_senate_parser_extracts_transactions() -> None:
    parser = SenateParser()
    listing = SourceFilingListing(
        source_system=SourceSystem.SENATE_EFD,
        chamber=Chamber.SENATE,
        source_filing_id="fixture-senate",
        filer_name="John Boozman",
        filer_first_name="John",
        filer_last_name="Boozman",
        office_title="Senator",
        report_type_raw="Periodic Transaction Report",
        source_url="https://efdsearch.senate.gov/search/view/ptr/fixture/",
    )
    artifacts = [
        RawArtifactPayload(
            document_type=RawDocumentType.REPORT_HTML,
            source_url=listing.source_url,
            content_type="text/html",
            body=(FIXTURE_DIR / "senate" / "report.html").read_bytes(),
            filename="report.html",
        )
    ]

    parsed = parser.parse(listing, artifacts)

    assert parsed.filed_at_raw == "01/13/2026 @ 9:26 AM"
    assert len(parsed.transactions) == 2
    assert parsed.transactions[0].ticker_raw == "ANET"
    assert parsed.transactions[1].asset_name_raw == "Apple Inc"


def test_house_parser_extracts_transactions(monkeypatch) -> None:
    parser = HouseParser()
    sample_text = "\n".join(
        [
            "Periodic Transaction Report",
            "Name: Hon. James Comer",
            "Status: Member",
            "State/District:KY01",
            "$200?",
            "Marvell Technology, Inc. - Common",
            "Stock (MRVL) [ST]",
            "P 01/21/202502/22/2025$1,001 - $15,000",
            "F S: New",
            "Palantir Technologies Inc. - Class A",
            "Common Stock (PLTR) [ST]",
            "P 01/21/202501/22/2025$1,001 - $15,000",
            "* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx.",
            "Digitally Signed: Hon. James Comer , 02/11/2025",
        ]
    )

    class FakePage:
        def extract_text(self):
            return sample_text

    class FakeReader:
        def __init__(self, *_args, **_kwargs):
            self.pages = [FakePage()]

    monkeypatch.setattr("app.ingestion.parsers.house.PdfReader", FakeReader)

    listing = SourceFilingListing(
        source_system=SourceSystem.HOUSE_CLERK,
        chamber=Chamber.HOUSE,
        source_filing_id="2025-20026750",
        filer_name="James Comer",
        filer_first_name="James",
        filer_last_name="Comer",
        office_title="Representative",
        report_type_raw="P",
        source_url="https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2025/20026750.pdf",
    )
    artifacts = [
        RawArtifactPayload(
            document_type=RawDocumentType.REPORT_PDF,
            source_url=listing.source_url,
            content_type="application/pdf",
            body=b"%PDF-fixture",
            filename="house.pdf",
        )
    ]

    parsed = parser.parse(listing, artifacts)

    assert parsed.filed_at_raw == "02/11/2025"
    assert len(parsed.transactions) == 2
    assert parsed.transactions[0].ticker_raw == "MRVL"
    assert parsed.transactions[1].transaction_type_raw == "P"

