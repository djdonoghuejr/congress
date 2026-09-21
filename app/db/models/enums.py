from enum import Enum


class Chamber(str, Enum):
    HOUSE = "house"
    SENATE = "senate"


class SourceSystem(str, Enum):
    HOUSE_CLERK = "house_clerk"
    SENATE_EFD = "senate_efd"


class ReportType(str, Enum):
    PERIODIC_TRANSACTION = "periodic_transaction"
    ANNUAL = "annual"
    CANDIDATE = "candidate"
    NEW_FILER = "new_filer"
    TERMINATION = "termination"
    AMENDMENT = "amendment"
    OTHER = "other"


class FilingStatus(str, Enum):
    DISCOVERED = "discovered"
    PARSED = "parsed"
    PARTIAL = "partial"
    FAILED = "failed"


class RawDocumentType(str, Enum):
    DISCOVERY_HTML = "discovery_html"
    DISCOVERY_JSON = "discovery_json"
    DISCOVERY_ZIP = "discovery_zip"
    INDEX_XML = "index_xml"
    REPORT_HTML = "report_html"
    REPORT_PDF = "report_pdf"
    PAPER_IMAGE = "paper_image"


class IngestionRunStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class TransactionType(str, Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    EXCHANGE = "exchange"
    RECEIPT = "receipt"
    OTHER = "other"


class OwnerType(str, Enum):
    SELF = "self"
    SPOUSE = "spouse"
    JOINT = "joint"
    DEPENDENT = "dependent"
    OTHER = "other"
    UNKNOWN = "unknown"
