"""FastAPI entry point for the helpdesk dashboard API.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.database import db_manager
from core.users import fastapi_users
from hubspot_pipeline.scheduler import start_scheduler

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

app = FastAPI(title="HE Helpdesk Dashboard API", lifespan=lifespan)

# Include API routers
app.include_router(auth_router, prefix="/api")
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate, requires_verification=True),
    prefix="/api/users",
    tags=["users"],
)

app.include_router(dashboard_router)
