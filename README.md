# Company Lens AI

An automated pipeline that watches a Google Sheet of companies, enriches each one
with independent public signals (including real browser automation), asks an LLM
for a structured fit verdict, and syncs the verdict back to the sheet — all backed
by a real Postgres database and exposed over an API you can trigger on demand or
on a schedule.

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

- **Source** — `GoogleSheetsService` reads unprocessed rows from the sheet via a
  service-account-authenticated Sheets API client. A background `asyncio` task in
  `app/main.py` polls on an interval (`POLL_INTERVAL_SECONDS`); `/api/v1/pipeline/run`
  triggers the same logic on demand.
- **Enrich** — `PipelineOrchestrator._collect_signals_for_company` runs three
  providers concurrently (`app/providers/`). `BrowserProvider` uses Playwright to
  load the real page in a headless browser and extract DOM text, pricing, and
  metadata — not just a static HTML fetch.
- **Persist** — SQLAlchemy models (`app/models/`) store `companies`, `signals`,
  `verdicts`, and `pipeline_runs` in Postgres, with Alembic migrations
  (`alembic/versions/`).
- **Judge** — `GeminiJudgeService` sends the collected signals to Gemini with a
  Pydantic response schema (`app/schemas/verdict.py`), returning a calibrated
  `fit` / `confidence` / `reasoning` / `follow_up_question`.
- **Sync back** — the verdict is written back to the sheet via the same
  authenticated Sheets client.
- **Ship** — FastAPI app (`app/main.py`, `app/api/routes.py`), containerized with
  a Playwright-based Docker image, deployed to Render.

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/health` | GET | Liveness check |
| `/api/v1/pipeline/run` | POST | Process all unprocessed sheet rows now |
| `/api/v1/evaluate` | POST | Enrich + evaluate a single ad-hoc `{name, website}` |
| `/api/v1/runs?limit=20` | GET | Recent pipeline run history |

## Local development

```bash
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium

cp .env.example .env   # fill in real values — see below

alembic upgrade head
uvicorn app.main:app --reload
```

### Environment variables

See `.env.example` for the full list. The two that trip people up:

- `GOOGLE_SHEET_ID` — the ID segment of the sheet's URL (not the full URL).
- `GOOGLE_SERVICE_ACCOUNT_JSON` — the **entire contents** of a Google service
  account key JSON file, as a single-line string, for an account that's been
  shared on the target sheet with Editor access. Prefer setting this directly
  as an environment variable in every environment (local `.env`, CI, Render).
  Don't check a `credentials.json` file into git — it's gitignored here on
  purpose.

> **Note on naming:** the code (`app/core/config.py`) reads `GOOGLE_SHEET_ID`
> and `GOOGLE_SERVICE_ACCOUNT_JSON`. Older drafts of this repo's
> `.env.example`/`render.yaml` used `SPREADSHEET_ID`/`GOOGLE_SHEETS_CREDENTIALS_JSON`
> instead, which the app silently ignores. Both files have been corrected to
> match the code — if you're pulling config from an older note or doc, use
> the names above.

### Tests

```bash
pytest -v
```

Tests use an in-memory/isolated setup and don't require a real Gemini key or
Sheets credentials — `GeminiJudgeService` and `GoogleSheetsService` both
degrade gracefully (returning an `unknown`/`0.0` verdict, or logging a
warning) when credentials are absent, which is what `tests/test_gemini_judge.py`
and `tests/test_sheets.py` exercise. CI does the same (see below), except for
`DATABASE_URL`, which needs to be a real Postgres connection string — the
SQLAlchemy engine is configured with `pool_size`/`max_overflow`, which SQLite
doesn't support, so tests run against a throwaway Postgres service container
in CI (and you'll want a real Postgres locally too, e.g. via Docker or Neon's
free tier).

## Deployment (Render)

1. Push this repo to GitHub (see [Security note](#security-note-before-you-push) first).
2. In Render, **New → Blueprint**, point it at the repo. `render.yaml` defines
   a free-tier Docker web service.
3. Render will prompt for the `sync: false` secrets: `DATABASE_URL` (your
   Neon connection string), `GEMINI_API_KEY`, `GOOGLE_SHEET_ID`, and
   `GOOGLE_SERVICE_ACCOUNT_JSON`. Paste the service-account JSON as one line.
4. Deploy. `healthCheckPath: /api/v1/health` gates rollout.
5. Once you have the public URL (e.g. `https://company-lens-ai-api.onrender.com`),
   add it as a GitHub Actions secret — see below.

Render/Railway/Koyeb free tiers all spin the service down after a period of
inactivity. Rather than paying for an always-on plan, this repo pairs the
free tier with a scheduled GitHub Action that periodically hits the health
check and triggers a run — see the next section. If you'd rather rely purely
on the in-process poller, upgrade the Render plan in `render.yaml` to
something that doesn't sleep.

## CI/CD (GitHub Actions)

Two workflows live in `.github/workflows/`:

- **`ci.yml`** — runs on every push/PR: `ruff check` (pyflakes/pycodestyle
  rules, not a full style rewrite), the `pytest` suite against a real
  Postgres service container, and an `alembic upgrade head` smoke test.
- **`trigger-pipeline.yml`** — runs on a 15-minute cron and on manual
  dispatch from the Actions tab. It hits `/api/v1/health` (waking a sleeping
  free-tier instance), `POST`s `/api/v1/pipeline/run`, and logs the latest
  run from `/api/v1/runs`.

`trigger-pipeline.yml` needs one repo secret:

- **Settings → Secrets and variables → Actions → New repository secret**
  - Name: `PIPELINE_BASE_URL`
  - Value: your Render URL, no trailing slash (e.g. `https://company-lens-ai-api.onrender.com`)

## Security note before you push

Before publishing this repo:

- Confirm no `.env` or `credentials.json` file is staged (`git status` — both
  are gitignored, but double-check if you've ever `git add -f`'d one).
- If a real Google service-account key, Gemini API key, or database
  connection string was ever written to disk in this project outside of
  `.env`/`credentials.json` (e.g. pasted into a doc, a chat log, or an old
  commit), rotate it — deleting the file locally doesn't undo exposure.
  Service account keys are rotated from the Google Cloud Console (IAM &
  Admin → Service Accounts → Keys); the Gemini key from Google AI Studio;
  the Neon connection string from your Neon project's connection details.

## Repo layout

```
app/
  api/routes.py          FastAPI routes
  core/                  settings, DB engine
  models/                SQLAlchemy models
  schemas/                Pydantic request/response + LLM structured-output schemas
  providers/              signal-gathering providers (website, hiring, browser)
  services/                orchestrator, Sheets client, Gemini judge
alembic/                  migrations
tests/                     pytest suite
.github/workflows/         CI + scheduled trigger
Dockerfile                 Playwright-based image
render.yaml                 Render blueprint
```
