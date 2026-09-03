# Company Lens AI

An automated company-intelligence pipeline that watches a Google Sheet of
companies, enriches each one with independent public signals (including real
browser automation), asks Gemini for a structured fit verdict, and syncs the
verdict back to the sheet — backed by a real Postgres database and exposed
over an API you can trigger on demand or on a schedule.

## 🚀 Live Demo

**Interactive API Documentation:**  
https://company-lens-ai.onrender.com/docs

**Health Check:**  
https://company-lens-ai.onrender.com/api/v1/health

> **Note:** The application is deployed on Render's free tier. The service may
> take 50+ seconds to wake up after a period of inactivity.

## Architecture

```
Google Sheet ──▶ orchestrator ──▶ providers (parallel) ──▶ Postgres
   ▲  (rows)         │             • WebsiteProvider (httpx + BeautifulSoup)
   │                 │             • HiringProvider   (careers page signals)
   │                 │             • BrowserProvider  (Playwright, real DOM)
   │                 ▼
   └────────── GeminiJudgeService (structured verdict: fit / confidence /
               sync verdict      reasoning / follow-up question)
```

- **Source** — `GoogleSheetsService` reads unprocessed rows from the sheet via
  a service-account-authenticated Sheets API client. A background `asyncio`
  task in `app/main.py` polls on an interval (`POLL_INTERVAL_SECONDS`);
  `POST /api/v1/pipeline/run` triggers the same logic on demand.
- **Enrich** — `PipelineOrchestrator._collect_signals_for_company` runs three
  providers concurrently (`app/providers/`). `BrowserProvider` uses
  Playwright to load the real page in a headless browser and extract DOM
  text, pricing, and metadata — not just a static HTML fetch.
- **Persist** — SQLAlchemy models (`app/models/`) store `companies`,
  `signals`, `verdicts`, and `pipeline_runs` in Postgres, with Alembic
  migrations (`alembic/versions/`).
- **Judge** — `GeminiJudgeService` sends the collected signals to Gemini
  (`gemini-3.6-flash` by default) with a Pydantic response schema
  (`app/schemas/verdict.py`), returning a structured `fit` / `confidence` /
  `reasoning` / `follow_up_question`. If the call fails for any reason, it
  degrades gracefully to a labeled fallback verdict rather than crashing —
  see `scripts/verify_gemini.py` below if you want to confirm a real call
  succeeded rather than silently fell back.
- **Sync back** — the verdict is written back to the sheet via the same
  authenticated Sheets client, only when the row came from a real sheet
  (`source_row_id` is set) — ad-hoc `/evaluate` calls skip this.
- **Ship** — FastAPI app (`app/main.py`, `app/api/routes.py`), containerized
  with a Playwright-based Docker image (`mcr.microsoft.com/playwright/python`
  base), deployed to Render.

## API

All routes are under `/api/v1` and are currently **unauthenticated** —
`API_KEY` exists as a setting in `app/core/config.py` but nothing in
`app/api/routes.py` checks it yet. Fine for a demo behind an obscure Render
URL; worth knowing before pointing this at anything sensitive.

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/health` | GET | Liveness check |
| `/api/v1/pipeline/run` | POST | Process all unprocessed rows from the Google Sheet |
| `/api/v1/evaluate` | POST | Enrich + evaluate one ad-hoc `{name, website}`, no sheet row required |
| `/api/v1/runs?limit=20` | GET | Recent pipeline run history |
| `/docs` | GET | Interactive Swagger UI |

There's currently no route at bare `/` — hitting the root path 404s. That's
expected, not a bug; every real route lives under `/api/v1`.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium

cp .env.example .env   # then fill in real values — see note below
alembic upgrade head
uvicorn app.main:app --reload
```

### Environment variables

`app/core/config.py` is the source of truth. It reads:

```
ENVIRONMENT
LOG_LEVEL
API_KEY
PORT
DATABASE_URL
GEMINI_API_KEY
GEMINI_MODEL
GOOGLE_SHEET_ID
GOOGLE_SERVICE_ACCOUNT_JSON
POLL_INTERVAL_SECONDS
```

> **The checked-in `.env.example` is currently out of date** — it lists
> `GOOGLE_SHEETS_CREDENTIALS`, which the app doesn't read at all. Use
> `GOOGLE_SERVICE_ACCOUNT_JSON` (shown above), matching `config.py`, or the
> Sheets integration will silently fail to authenticate.

Notes on the two that trip people up:

- `GOOGLE_SHEET_ID` — the ID segment of the sheet's URL, not the full URL.
  Note there's also a hardcoded fallback sheet ID baked into `config.py` if
  this is left unset — don't rely on that in a fork, set your own.
- `GOOGLE_SERVICE_ACCOUNT_JSON` — the entire contents of a Google
  service-account key JSON file, as a single-line string, for an account
  shared on the target sheet with Editor access. `config.py` also has a
  fallback that reads a local `credentials.json` file if the env var is
  empty — don't commit that file (it's gitignored on purpose).

### Tests

```bash
pytest -v
```

Runs against `sqlite:///:memory:` with empty Gemini/Sheets credentials — both
services degrade gracefully rather than erroring when credentials are
missing, and `app/core/database.py` only applies Postgres-specific engine
args (`pool_size`/`max_overflow`) when the URL isn't SQLite, so no real
database is needed to run the suite. Production still uses Postgres (Neon).

To prove the *deployed* app is actually calling Gemini — not just that tests
pass, since the judge silently falls back on any failure — run:

```bash
python scripts/verify_gemini.py
```

with a real `.env` in place. It makes one live, non-mocked call and fails
loudly if it detects a fallback response.

## Deployment (Render)

`render.yaml` defines a free-tier Docker web service. In Render: **New →
Blueprint**, point it at this repo. It'll prompt for the `sync: false`
secrets: `DATABASE_URL` (a real Postgres string — this deploys against an
existing Neon instance rather than provisioning a new one), `GEMINI_API_KEY`,
`GOOGLE_SHEET_ID`, and `GOOGLE_SERVICE_ACCOUNT_JSON` (paste the service
account JSON as one line). `healthCheckPath: /api/v1/health` gates rollout.

Render's free tier spins the service down after ~15 min idle, which pauses
the in-process polling loop. `trigger-pipeline.yml` (below) compensates by
periodically hitting the deployed URL on a schedule, which both wakes a
sleeping instance and triggers a run.

## CI/CD (GitHub Actions)

Two workflows in `.github/workflows/`:

- **`ci.yml`** — on every push/PR: `ruff check`, then `pytest tests/ -v`
  against `sqlite:///:memory:` (see Tests above for why that's safe). This
  means CI does **not** currently catch Postgres-specific issues — a real
  Postgres service container would be a reasonable addition if that matters
  to you.
- **`trigger-pipeline.yml`** — cron (every 6 hours) plus manual dispatch from
  the Actions tab. `POST`s to whatever URL is in the `RENDER_PIPELINE_URL`
  secret, with retries to ride out cold starts.

`trigger-pipeline.yml` needs one repo secret:

- **Settings → Secrets and variables → Actions → New repository secret**
  - Name: `RENDER_PIPELINE_URL`
  - Value: the full pipeline-run URL, e.g.
    `https://company-lens-ai.onrender.com/api/v1/pipeline/run`

## Repo layout

```
app/
  api/routes.py          FastAPI routes (all under /api/v1)
  core/                   settings (config.py), DB engine (database.py)
  models/                 SQLAlchemy models: company, signal, verdict, pipeline_run
  schemas/                Pydantic request/response + LLM structured-output schemas
  providers/              website_provider, hiring_provider, browser_provider
  services/               orchestrator, sheets_service, gemini_judge
alembic/                  migrations
scripts/
  verify_gemini.py        real, non-mocked Gemini smoke test (see Tests above)
tests/                    pytest suite (7 test files)
.github/workflows/        ci.yml, trigger-pipeline.yml
Dockerfile                mcr.microsoft.com/playwright/python base image
render.yaml                Render blueprint
```

## Security note

Before making further changes public, double-check `.env` and
`credentials.json` are never staged (`git status` — both are gitignored).
`.env.example` should only ever contain placeholder values, never a real key
or connection string — if you ever paste real credentials into it while
editing, replace them with placeholders before committing, not after.
