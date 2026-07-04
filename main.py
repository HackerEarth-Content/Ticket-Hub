"""FastAPI entry point for the helpdesk dashboard API.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.database import db_manager
from dashboard.api import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_manager.initialize()
    yield
    await db_manager.close()


app = FastAPI(title="HE Helpdesk Dashboard API", lifespan=lifespan)
app.include_router(dashboard_router)
