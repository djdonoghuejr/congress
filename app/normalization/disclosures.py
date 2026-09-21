from __future__ import annotations

from app.db.models.enums import OwnerType, ReportType, SourceSystem, TransactionType
from app.normalization.common import collapse_whitespace


def normalize_report_type(raw: str | None, source_system: SourceSystem) -> ReportType:
    normalized = (collapse_whitespace(raw) or "").lower()
    if source_system == SourceSystem.HOUSE_CLERK and normalized == "p":
        return ReportType.PERIODIC_TRANSACTION
    if "periodic transaction" in normalized:
        return ReportType.PERIODIC_TRANSACTION
    if "annual" in normalized:
        return ReportType.ANNUAL
    if "candidate" in normalized:
        return ReportType.CANDIDATE
    if "new filer" in normalized:
        return ReportType.NEW_FILER
    if "termination" in normalized:
        return ReportType.TERMINATION
    if "amendment" in normalized:
        return ReportType.AMENDMENT
    return ReportType.OTHER


def normalize_transaction_type(raw: str | None) -> TransactionType:
    normalized = (collapse_whitespace(raw) or "").lower()
    if normalized.startswith("p") or "purchase" in normalized:
        return TransactionType.PURCHASE
    if normalized.startswith("s") or "sale" in normalized:
        return TransactionType.SALE
    if "exchange" in normalized:
        return TransactionType.EXCHANGE
    if "receive" in normalized:
        return TransactionType.RECEIPT
    return TransactionType.OTHER


def normalize_owner_type(raw: str | None) -> OwnerType:
    normalized = (collapse_whitespace(raw) or "").lower()
    if not normalized or normalized == "--":
        return OwnerType.UNKNOWN
    if normalized in {"self", "owner", "s"}:
        return OwnerType.SELF
    if "spouse" in normalized or normalized == "sp":
        return OwnerType.SPOUSE
    if "joint" in normalized or normalized == "jt":
        return OwnerType.JOINT
    if "child" in normalized or "dependent" in normalized or normalized == "dc":
        return OwnerType.DEPENDENT
    return OwnerType.OTHER


def normalize_asset_name(raw: str | None) -> str | None:
    return collapse_whitespace(raw)


def normalize_asset_type(raw: str | None) -> str | None:
    normalized = collapse_whitespace(raw)
    if not normalized or normalized == "--":
        return None
    return normalized

