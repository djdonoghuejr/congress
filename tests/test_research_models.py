from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.research.models import ResearchAnswer, ResearchFinding


def test_research_answer_requires_citations_for_findings() -> None:
    with pytest.raises(ValidationError, match="Every factual finding"):
        ResearchAnswer(
            answer="There was one trade.",
            findings=[ResearchFinding(statement="One trade")],
            query_scope="local trades",
        )


def test_research_answer_accepts_cited_findings() -> None:
    answer = ResearchAnswer(
        answer="There was one trade.",
        findings=[
            {
                "statement": "One trade",
                "citations": [{"title": "Filing", "url": "https://example.com/filing"}],
            }
        ],
        query_scope="local trades",
    )

    assert str(answer.findings[0].citations[0].url) == "https://example.com/filing"
