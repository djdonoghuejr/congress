# Congress Trades MVP

Greenfield FastAPI/Postgres backend for ingesting official U.S. congressional trade disclosures from the House Clerk and Senate eFD systems.

## MVP scope

- FastAPI service with query endpoints for trades and filings
- Canonical SQLAlchemy models for filers, filings, raw documents, transactions, ingestion runs, and ticker mappings
- Official Senate connector for PTR discovery plus electronic report parsing
- Official House connector for PTR discovery via the Clerk XML index plus PDF parsing
- Raw artifact capture to disk before normalization
- Alembic migration for the initial schema
- pytest coverage for schema, parsers, one full Senate ingestion path, and API queries

## Repo structure

```text
app/
  api/                 FastAPI routers
  core/                settings and JSON helpers
  db/                  SQLAlchemy models, metadata, session management
  ingestion/
    connectors/        official House and Senate fetchers
    parsers/           source-specific raw parsers
    pipeline/          raw artifact storage
  normalization/       canonical field normalization helpers
  repositories/        read/query layer
  services/            ingestion orchestration
alembic/               migration environment and revisions
tests/                 parser, ingestion, API, and schema tests
compose.yml            local Postgres
```

## Local setup

1. Create and activate a virtual environment.

   Windows PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install the project and dev dependencies.

   ```powershell
   python -m pip install -e .[dev]
   ```

3. Copy the example environment file.

   ```powershell
   Copy-Item .env.example .env
   ```

4. Start Postgres.

   ```powershell
   docker compose up -d postgres
   ```

5. Run the database migration.

   ```powershell
   alembic upgrade head
   ```

6. Start the API.

   ```powershell
   uvicorn app.main:app --reload
   ```

The API will be available at `http://127.0.0.1:8000`, with interactive docs at `/docs`.
The trades browser interface is available at `http://127.0.0.1:8000/`.

## Ingestion commands

Ingest Senate periodic transaction reports for a date window:

```powershell
python -m app.cli ingest-senate --start-date 2026-01-01 --end-date 2026-01-31
```

Ingest House periodic transaction reports for a filing year:

```powershell
python -m app.cli ingest-house --year 2025
```

Optional flags:

- `--limit N` for either command to cap discovery during local development
- `--skip-existing-before YYYY-MM-DD` to avoid re-fetching successfully parsed older filings

## Automatic ingestion on Windows

The scheduler helper runs Senate ingestion daily over a 14-day overlap and scans the current House
filing-year index weekly on Sundays. Successfully parsed filings older than the overlap are skipped;
new filing IDs and recent records are still processed. It writes per-run logs under `logs/ingestion/`
and retries failed tasks up to three times.

Before registering the task, install dependencies, configure `.env`, start Docker Desktop, and apply
the current database migrations once:

```powershell
python -m pip install -e .[dev]
alembic upgrade head
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\register-ingestion-task.ps1
```

The task runs daily at 6:00 AM by default. To choose another 24-hour time, pass `-StartTime`, such as
`-StartTime "08:30"`. It runs under your Windows account; keep the computer awake and logged in, and
configure Docker Desktop to start when you sign in. Task Scheduler is configured to ignore overlapping
runs and retry failed runs. Trigger the task once from Task Scheduler to verify the setup. Logs are
available in `logs/ingestion/`.

## Research copilot

The project includes a read-only OpenAI Agents SDK research copilot over stored trades and filings.
Set `OPENAI_API_KEY` and `CONGRESS_AGENT_MODEL` in `.env`, then ask a question:

```powershell
python -m app.cli research "Which senators disclosed AAPL purchases in 2026?"
```

The manager agent delegates to trade and filing specialists, which can only use bounded read-only
database tools. Answers include source URLs and limitations. Agent runs are traced by the Agents SDK
when tracing is enabled for the configured OpenAI organization.

Raw artifacts are written to `CONGRESS_RAW_STORAGE_DIR` and every normalized record keeps the original filing URL in the database.

## API surface

The home page (`/`) provides a filterable trades table. Select a row to open a detail card with
disclosure fields and a link to the source filing. Filters include member, ticker, chamber,
transaction type, and transaction date range.

- `GET /health`
- `GET /trades`
- `GET /members/{member_id}/trades`
- `GET /tickers/{ticker}/trades`
- `GET /filings`

Useful query params:

- `/trades`: `limit`, `offset`, `chamber`, `ticker`, `start_date`, `end_date`
- `/filings`: `limit`, `offset`, `chamber`, `source_system`, `member_id`, `report_type`, `start_date`, `end_date`

## Tests

Run the suite with:

```powershell
pytest
```

## Assumptions and current limitations

- The application is designed around official sources only:
  - Senate eFD search and report pages
  - House Clerk yearly XML index plus official PTR PDFs
- Senate electronic PTRs are fully parsed in this MVP.
- Senate paper-image filings are captured as raw artifacts and stored as filings, but they remain partial because this MVP does not include OCR.
- House PTR parsing is best-effort against text-extractable PDFs from the Clerk site.
- Trade amounts remain ranges. The service stores `amount_low` and `amount_high` bounds when they are disclosed and never invents exact amounts.
- Tickers remain nullable when the source does not provide a trustworthy symbol.
