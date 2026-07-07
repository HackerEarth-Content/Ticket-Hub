# HE Helpdesk Dashboard

Support/helpdesk analytics dashboard: a Python pipeline syncs HubSpot ticket
and CSAT data into Postgres, a FastAPI backend computes KPIs, and a React
frontend renders it. See `handoff.md` for the original product/data-modeling
notes.

## Prerequisites

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) (dependency manager)
- Node.js (for the frontend)
- A Postgres database
- A HubSpot private app token with at least: ticket read, `crm.objects.feedback_submissions.read`
- A Google OAuth client (Client ID + Secret) for sign-in

## 1. Install dependencies

```bash
uv sync
```

This creates `.venv/` and installs everything pinned in `uv.lock`.

## 2. Configure environment

Create a `.env` file in the repo root:

```bash
HUBSPOT_SERVICE_KEY=       # HubSpot private app token
DATABASE_URL=              # e.g. postgresql://user:pass@localhost:5432/he_art
USER_SECRET=               # random secret used to sign auth cookies/JWTs
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
FRONTEND_URL=http://localhost:5173   # default, override if needed
API_BASE_URL=http://localhost:8000   # default, override if needed
OPENAI_API_KEY=             # optional, only if AI features are used
```

In Google Cloud Console, the OAuth client's authorized redirect URI must be
`{API_BASE_URL}/api/auth/google/callback`.

## 3. Set up the database

Apply all migrations:

```bash
source .venv/bin/activate
alembic upgrade head
```

Schema changes going forward: edit the ORM models in `core/orm.py`, then
generate a migration and apply it:


## 4. Backfill HubSpot data

First run — pulls ticket and CSAT history since 2026-02-02 into Postgres
(`--full`'s floor date, see `hubspot_pipeline/run.py`):

```bash
python -m hubspot_pipeline.run --full --write-db
```

This can take a while on a large HubSpot portal. For a smaller/faster initial
load during development, use `--days N --write-db` instead of `--full`.

## 5. Run the backend

```bash
uvicorn main:app --reload
```

Serves the API at `http://localhost:8000`. On startup it also starts an
**in-process scheduler** (`hubspot_pipeline/scheduler.py`, via APScheduler)
that re-runs the incremental HubSpot sync every 5 minutes for as long as the
server is running — no separate cron job needed. Only run one instance of
this process (no `--workers`); a second instance would double-sync.

To trigger a sync on demand instead of waiting for the schedule, hit
`POST /dashboard/meta/sync-now`.

## 6. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Serves at `http://localhost:5173`, proxying `/dashboard` and `/api` requests
to the backend (default `http://localhost:8000`; override with
`VITE_API_PROXY_TARGET` if the backend runs elsewhere).

## Project layout

- `hubspot_pipeline/` — HubSpot API client, extraction/normalization, the
  incremental sync pipeline, and the in-process scheduler.
- `core/` — settings, database session management, ORM models (`orm.py`),
  auth (`users.py`).
- `dashboard/` — all KPI/query logic, one module per dashboard section
  (`utils.py`, `customers.py`, `backline.py`, `frontline.py`, `slack_issues.py`).
- `api/` — thin FastAPI route definitions; routes call into `dashboard/`.
- `migrations/` — Alembic migrations.
- `frontend/` — React + TypeScript + Recharts dashboard UI.

## Self-checks

A few modules include a runnable self-check instead of a full test suite:

```bash
python -m hubspot_pipeline.test_transforms
python -m hubspot_pipeline.scheduler
```
