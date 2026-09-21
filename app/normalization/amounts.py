from __future__ import annotations

import re
from dataclasses import dataclass

from app.normalization.common import collapse_whitespace


AMOUNT_RANGE_RE = re.compile(r"\$?\s*([\d,]+)\s*-\s*\$?\s*([\d,]+)")
OVER_RE = re.compile(r"over\s+\$?\s*([\d,]+)", re.IGNORECASE)
UNDER_RE = re.compile(r"(?:under|less than)\s+\$?\s*([\d,]+)", re.IGNORECASE)


@dataclass(slots=True)
class AmountRange:
    raw: str | None
    low: int | None
    high: int | None


def _parse_int(value: str) -> int:
    return int(value.replace(",", ""))


def parse_amount_range(value: str | None) -> AmountRange:
    normalized = collapse_whitespace(value)
    if not normalized or normalized == "--":
        return AmountRange(raw=normalized, low=None, high=None)

    if match := AMOUNT_RANGE_RE.search(normalized):
        return AmountRange(
            raw=normalized,
            low=_parse_int(match.group(1)),
            high=_parse_int(match.group(2)),
        )

    if match := OVER_RE.search(normalized):
        return AmountRange(raw=normalized, low=_parse_int(match.group(1)), high=None)

    if match := UNDER_RE.search(normalized):
        return AmountRange(raw=normalized, low=None, high=_parse_int(match.group(1)))

    return AmountRange(raw=normalized, low=None, high=None)

