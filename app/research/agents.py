from __future__ import annotations

import re
from typing import Any

from agents import Agent, GuardrailFunctionOutput, RunContextWrapper
from agents.decorators import input_guardrail, output_guardrail
from sqlalchemy.orm import Session

from app.research.models import ResearchAnswer
from app.research.tools import build_filing_tools, build_trade_tools

_ALLOWED_TERMS = re.compile(
    r"\b(congress|congressional|senate|senator|house|representative|member|filing|"
    r"disclosure|trade|transaction|ticker|stock|purchase|sale|exchange|report)\b",
    re.IGNORECASE,
)
_ADVICE_TERMS = re.compile(
    r"\b(should i buy|should i sell|buy this stock|sell this stock|financial advice|"
    r"investment advice|what should i invest)\b",
    re.IGNORECASE,
)


@input_guardrail
async def research_scope_guardrail(
    ctx: RunContextWrapper[None], agent: Agent, input: Any
) -> GuardrailFunctionOutput:
    text = input if isinstance(input, str) else str(input)
    blocked = bool(_ADVICE_TERMS.search(text)) or not bool(_ALLOWED_TERMS.search(text))
    return GuardrailFunctionOutput(
        output_info={"allowed": not blocked},
        tripwire_triggered=blocked,
    )


@output_guardrail
async def cited_answer_guardrail(
    ctx: RunContextWrapper[None], agent: Agent, output: ResearchAnswer
) -> GuardrailFunctionOutput:
    valid = all(finding.citations for finding in output.findings)
    return GuardrailFunctionOutput(
        output_info={"all_findings_cited": valid},
        tripwire_triggered=not valid,
    )


def build_research_manager(session: Session, model: str) -> Agent:
    trade_agent = Agent(
        name="Trade Research Specialist",
        handoff_description="Searches stored congressional transactions and summarizes trade results.",
        instructions=(
            "You are a read-only trade research specialist. Use search_trades for every factual "
            "claim. Do not make investment recommendations. Return the raw source URLs and a "
            "short, evidence-based summary to the manager."
        ),
        model=model,
        tools=build_trade_tools(session),
    )
    filing_agent = Agent(
        name="Filing Research Specialist",
        handoff_description="Searches stored congressional filings, statuses, and source documents.",
        instructions=(
            "You are a read-only filing research specialist. Use search_filings for every factual "
            "claim. Do not invent missing filing details. Return source URLs and clearly state "
            "when the local dataset has no matching records."
        ),
        model=model,
        tools=build_filing_tools(session),
    )
    return Agent(
        name="Congress Trades Research Copilot",
        instructions=(
            "Answer questions only about the local congressional trades and filings dataset. "
            "Delegate transaction questions to trade_research and filing/status questions to "
            "filing_research. You may call both when needed. Every factual finding must cite a "
            "source URL returned by a specialist. Do not provide personalized investment advice. "
            "Use the requested structured output and include limitations when the data is partial, "
            "bounded, or empty."
        ),
        model=model,
        tools=[
            trade_agent.as_tool(
                tool_name="trade_research",
                tool_description="Research stored congressional transactions.",
            ),
            filing_agent.as_tool(
                tool_name="filing_research",
                tool_description="Research stored congressional filings and source documents.",
            ),
        ],
        output_type=ResearchAnswer,
        input_guardrails=[research_scope_guardrail],
        output_guardrails=[cited_answer_guardrail],
    )
