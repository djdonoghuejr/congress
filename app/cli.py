from __future__ import annotations

import argparse
from datetime import date

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ingestion.connectors.house import HouseConnector
from app.ingestion.connectors.senate import SenateConnector
from app.ingestion.parsers.house import HouseParser
from app.ingestion.parsers.senate import SenateParser
from app.ingestion.pipeline.raw_store import RawArtifactStore
from app.services.ingestion import IngestionService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Congress disclosure ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    senate = subparsers.add_parser("ingest-senate", help="Ingest Senate PTR filings")
    senate.add_argument("--start-date", required=True, type=date.fromisoformat)
    senate.add_argument("--end-date", required=True, type=date.fromisoformat)
    senate.add_argument("--limit", type=int, default=None)

    house = subparsers.add_parser("ingest-house", help="Ingest House PTR filings")
    house.add_argument("--year", required=True, type=int)
    house.add_argument("--limit", type=int, default=None)

    research = subparsers.add_parser(
        "research", help="Ask a read-only Agents SDK copilot about stored disclosures"
    )
    research.add_argument("question", help="Natural-language question about local trade data")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = get_settings()

    if args.command == "research":
        _run_research(args.question, settings)
        return

    raw_store = RawArtifactStore(settings)
    session = SessionLocal()

    connector = None
    try:
        if args.command == "ingest-senate":
            connector = SenateConnector(settings=settings)
            filing_parser = SenateParser()
            kwargs = {
                "start_date": args.start_date,
                "end_date": args.end_date,
                "limit": args.limit,
            }
        else:
            connector = HouseConnector(settings=settings)
            filing_parser = HouseParser()
            kwargs = {"year": args.year, "limit": args.limit}

        service = IngestionService(session, raw_store)
        run = service.ingest(
            connector=connector,
            parser=filing_parser,
            discovery_kwargs=kwargs,
        )
        print(
            f"run={run.id} status={run.status.value} "
            f"discovered={run.discovered_count} processed={run.processed_count} "
            f"transactions={run.stored_count} errors={run.error_count}"
        )
    finally:
        session.close()
        if connector is not None:
            connector.close()


def _run_research(question: str, settings) -> None:
    if not settings.openai_api_key:
        raise SystemExit(
            "OPENAI_API_KEY is required for the research command. "
            "Set it in .env or the current shell."
        )
    if not settings.agent_model:
        raise SystemExit(
            "CONGRESS_AGENT_MODEL is required for the research command. "
            "Set it in .env or the current shell."
        )

    try:
        from agents import Runner
        from agents.exceptions import (
            InputGuardrailTripwireTriggered,
            OutputGuardrailTripwireTriggered,
        )
        from app.research.agents import build_research_manager
    except ImportError as exc:
        raise SystemExit(
            "The Agents SDK is not installed. Install the project with `pip install -e .[dev]`."
        ) from exc

    import asyncio

    session = SessionLocal()
    try:
        manager = build_research_manager(session, settings.agent_model)

        async def run() -> object:
            result = await Runner.run(manager, question)
            return result.final_output

        try:
            answer = asyncio.run(run())
        except (InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered) as exc:
            raise SystemExit(
                "The research request was blocked by the copilot's data-scope or citation guardrail."
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"Research agent failed: {exc}") from exc

        print(answer.answer)
        if answer.findings:
            print("\nFindings:")
            for finding in answer.findings:
                print(f"- {finding.statement}")
                for citation in finding.citations:
                    print(f"  Source: {citation.title} - {citation.url}")
        if answer.limitations:
            print("\nLimitations:")
            for limitation in answer.limitations:
                print(f"- {limitation}")
        print(f"\nQuery scope: {answer.query_scope}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
