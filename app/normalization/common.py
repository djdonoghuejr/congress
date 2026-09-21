from __future__ import annotations

import re
from datetime import date, datetime, timezone

from dateutil import parser


WHITESPACE_RE = re.compile(r"\s+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
HONORIFIC_RE = re.compile(
    r"^(hon\.?|mr\.?|mrs\.?|ms\.?|dr\.?|rep\.?|representative|sen\.?|senator)\s+",
    re.IGNORECASE,
)


def collapse_whitespace(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = WHITESPACE_RE.sub(" ", value).strip()
    return normalized or None


def normalize_name(value: str | None) -> str | None:
    normalized = collapse_whitespace(value)
    if not normalized:
        return None
    while True:
        stripped = HONORIFIC_RE.sub("", normalized)
        if stripped == normalized:
            break
        normalized = stripped
    return normalized.replace(" ,", ",")


def split_name(value: str | None) -> tuple[str | None, str | None]:
    normalized = normalize_name(value)
    if not normalized:
        return None, None
    if "," in normalized:
        last_name, first_name = [part.strip() for part in normalized.split(",", 1)]
        return first_name or None, last_name or None
    parts = normalized.split(" ")
    if len(parts) == 1:
        return None, parts[0]
    return " ".join(parts[:-1]), parts[-1]


def slugify(value: str) -> str:
    collapsed = collapse_whitespace(value) or ""
    slug = NON_ALNUM_RE.sub("-", collapsed.lower()).strip("-")
    return slug


def build_identity_key(*parts: str | None) -> str:
    return ":".join(part for part in (slugify(part) if part else None for part in parts) if part)


def parse_date(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    normalized = collapse_whitespace(value)
    if not normalized or normalized == "--":
        return None
    return parser.parse(normalized, fuzzy=True).date()


def parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    normalized = collapse_whitespace(value)
    if not normalized or normalized == "--":
        return None
    parsed = parser.parse(normalized, fuzzy=True)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
