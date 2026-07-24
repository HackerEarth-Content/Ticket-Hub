# HE Helpdesk Dashboard

Support/helpdesk analytics dashboard: a Python pipeline syncs HubSpot ticket
and CSAT data into Postgres, a FastAPI backend computes KPIs, and a React
frontend renders it. See `handoff.md` for the original product/data-modeling
notes.

## Architecture

```
HubSpot API ──▶ hubspot_pipeline (sync) ──▶ Postgres ◀── dashboard/ (KPI queries)
                        ▲                                      ▲
                 APScheduler (every 5 min)               api/ (FastAPI routes)
                                                                ▲
                                                     frontend/ (React SPA, nginx)
```

In production this runs as two containers (see `docker-compose.yml`):

| Container  | Image                  | Port | Role                                              |
|------------|------------------------|------|----------------------------------------------------|
| `backend`  | built from `Dockerfile` | 8000 | FastAPI app, HubSpot sync scheduler, DB access     |
| `frontend` | built from `frontend/Dockerfile` (nginx) | 80 | Serves the built SPA; proxies `/dashboard` and `/api` to `backend` |

The backend runs a single uvicorn process (no `--workers`) — running a second
instance would double the HubSpot sync.

## Prerequisites

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) (dependency manager)
- Node.js (for the frontend)
- A Postgres database
- A HubSpot private app token with at least: ticket read, `crm.objects.feedback_submissions.read`
- A Google OAuth client (Client ID + Secret) for sign-in

## Configuration reference

All config is read from environment variables (`.env` in the repo root, see
`core/config.py`).

| Variable | Required | Notes |
|---|---|---|
| `HUBSPOT_SERVICE_KEY` | yes | HubSpot private app token |
| `DATABASE_URL` | yes | `postgresql://user:pass@host:port/db`. **If the DB is behind a Supabase-style connection pooler, use the transaction-mode port (e.g. `6543`), not session-mode (`5432`)** — session mode caps concurrent clients far lower and the app will hit `EMAXCONNSESSION` under normal dashboard load. Transaction mode requires disabling psycopg's server-side prepared statements, already handled in `core/database.py` (`prepare_threshold=None`) — don't remove that if you touch this file. |
| `USER_SECRET` | yes | Random secret signing auth cookies/JWTs |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | yes | Google OAuth client for sign-in |
| `FRONTEND_URL` | yes | Origin the backend allows via CORS and redirects to after login |
| `API_BASE_URL` | yes | Public base URL of the backend; also determines the OAuth redirect URI (see below) |
| `ENVIRONMENT` | yes | e.g. `development` / `production` |
| `ALLOWED_EMAILS` | no | Comma-separated allowlist of Google account emails permitted to sign in. Empty = anyone with a Google account can sign in |
| `OPENAI_API_KEY` | no | Only needed if AI features are used |
| `WOOTRIC_CLIENT_ID` / `WOOTRIC_CLIENT_SECRET` | no | Wootric NPS sync; left blank, the NPS sync no-ops instead of failing startup |
| `TICKET_PAGE_SIZE` | no | Default `200` — HubSpot search API page size |

In Google Cloud Console, the OAuth client's authorized redirect URI must be
`{API_BASE_URL}/api/auth/google/callback`.

### Access control note

Not all `/dashboard/*` routes require login — some (e.g. `/dashboard/summary`,
`/dashboard/customers/*`, `/dashboard/meta/*`) are intentionally public,
others require an authenticated session (`core/users.py`,
`current_active_user` dependency in `api/dashboard_routes.py`). CORS only
blocks cross-origin browser JS requests — it does **not** stop direct
navigation, curl, or same-origin requests to public routes. Check
`api/dashboard_routes.py` before assuming a route is gated.

## Local development setup

### 1. Install dependencies

```bash
uv sync
```

This creates `.venv/` and installs everything pinned in `uv.lock`.

### 2. Configure environment

Create a `.env` in the repo root using the table above. Local defaults:

```bash
FRONTEND_URL=http://localhost:5173
API_BASE_URL=http://localhost:8000
ENVIRONMENT=development
```

### 3. Set up the database

```bash
source .venv/bin/activate
alembic upgrade head
```

Schema changes going forward: edit the ORM models in `core/orm.py`, then
generate and apply a migration.

### 4. Backfill HubSpot data

First run — pulls ticket and CSAT history since 2026-02-02 into Postgres
(`--full`'s floor date, see `hubspot_pipeline/run.py`):

```bash
python -m hubspot_pipeline.run --full --write-db
```

This can take a while on a large HubSpot portal. For a smaller/faster initial
load during development, use `--days N --write-db` instead of `--full`.

### 5. Run the backend

```bash
uvicorn main:app --reload
```

Serves the API at `http://localhost:8000`. On startup it also starts an
**in-process scheduler** (`core/scheduler.py`, via APScheduler) that re-runs
the incremental HubSpot sync every 5 minutes for as long as the server is
running — no separate cron job needed.

To trigger a sync on demand instead of waiting for the schedule, hit
`POST /dashboard/meta/sync-now`.

### 6. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Serves at `http://localhost:5173`, proxying `/dashboard` and `/api` requests
to the backend (default `http://localhost:8000`; override with
`VITE_API_PROXY_TARGET` if the backend runs elsewhere).

## Production deployment

The app ships as two Docker images, run via `docker-compose.yml`.

### 1. Provision the database

Point `DATABASE_URL` at the production Postgres instance. Run migrations
**once**, from a machine with `.venv` set up (not inside the running
containers):

```bash
source .venv/bin/activate
alembic upgrade head
```

### 2. Configure `.env`

Same variables as local dev, with production values:

```bash
FRONTEND_URL=https://<your-domain>
API_BASE_URL=https://<your-domain>          # or the backend's public URL if split
ENVIRONMENT=production
```

`docker-compose.yml` loads `.env` for the `backend` service only — the
frontend container needs no secrets, it just serves the built SPA and proxies
API calls through nginx (`frontend/nginx.conf`).

### 3. Build and start

```bash
docker compose up -d --build
```

- `backend` listens on `8000`
- `frontend` (nginx) listens on `80` and proxies `/dashboard/*` and `/api/*` to `backend:8000`

### 4. First-time data load

Same as local dev step 4 — backfill once before the scheduler's incremental
sync takes over:

```bash
docker compose exec backend python -m hubspot_pipeline.run --full --write-db
```

### 5. Verify

- `GET /dashboard/meta/sync-status` — confirms the scheduler is syncing
- `GET /dashboard/live/today` — confirms KPI queries work end-to-end
- Load the dashboard in a browser and reload a few times — the original
  motivation for the `DATABASE_URL` pooler-mode note above was this exact
  page triggering enough concurrent queries to exhaust a session-mode pool

### Redeploying

```bash
git pull
docker compose up -d --build
```

Migrations aren't run automatically on deploy — run `alembic upgrade head`
manually (per step 1) whenever a deploy includes a schema change.

## Project layout

- `hubspot_pipeline/` — HubSpot API client, extraction/normalization, the
  incremental sync pipeline.
- `core/` — settings, database session management (`database.py`), ORM
  models (`orm.py`), auth (`users.py`), scheduler (`scheduler.py`).
- `dashboard/` — all KPI/query logic, one module per dashboard section
  (`utils.py`, `customers.py`, `backline.py`, `frontline.py`, `slack_issues.py`).
- `api/` — thin FastAPI route definitions; routes call into `dashboard/`.
- `migrations/` — Alembic migrations.
- `frontend/` — React + TypeScript + Recharts dashboard UI.

## Self-checks

A few modules include a runnable self-check instead of a full test suite:

```bash
python -m hubspot_pipeline.test_transforms
```
