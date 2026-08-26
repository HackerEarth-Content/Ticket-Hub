"""FastAPI entry point for the helpdesk dashboard API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.database import db_manager
from core.users import fastapi_users, OAuthNotAllowedError
from core.scheduler import start_scheduler

from api.dashboard_routes import router as dashboard_router
from api.auth_routes import router as auth_router

from models.users import UserRead, UserUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_manager.initialize()
    scheduler = start_scheduler()
    yield
    scheduler.shutdown(wait=False)
    await db_manager.close()


app = FastAPI(
    title="HE Helpdesk Dashboard API",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Cookie auth (core/users.py) needs credentialed CORS, which browsers only
# allow with an explicit origin -- "*" is rejected once allow_credentials=True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# A user who isn't on ALLOWED_EMAILS reaches this mid-OAuth-flow -- send them
# back to the frontend (not a bare JSON error) with a flag it can pop up.
@app.exception_handler(OAuthNotAllowedError)
async def oauth_not_allowed_handler(request: Request, exc: OAuthNotAllowedError):
    return RedirectResponse(
        f"{settings.FRONTEND_URL}?authError=not_allowed", status_code=302
    )


# Include API routers
app.include_router(auth_router, prefix="/api")
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate, requires_verification=True),
    prefix="/api/users",
    tags=["users"],
)

app.include_router(dashboard_router)

# Serve the built frontend (frontend/dist) when it exists -- in the Docker
# image the SPA and the API share one origin, so api.ts's relative /dashboard
# and /api URLs just work. Mounted last so the API routes above win; absent
# in dev, where Vite serves the frontend and proxies to us instead.
_frontend_dist = Path(__file__).parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
