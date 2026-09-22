from __future__ import annotations

import asyncio
import os

import pytest

from agents import Runner

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.research.agents import build_research_manager
from app.research.models import ResearchAnswer


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_AGENT_INTEGRATION") != "1",
    reason="set RUN_AGENT_INTEGRATION=1 to run the live Agents SDK integration test",
)
def test_live_research_agent_returns_structured_answer() -> None:
    settings = get_settings()
    if not settings.openai_api_key or not settings.agent_model:
        pytest.skip("OPENAI_API_KEY and CONGRESS_AGENT_MODEL are required")

    session = SessionLocal()
    try:
        manager = build_research_manager(session, settings.agent_model)
        result = asyncio.run(Runner.run(manager, "Show me recent congressional trade filings."))
        assert isinstance(result.final_output, ResearchAnswer)
    finally:
        session.close()
