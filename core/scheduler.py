"""In-process replacement for the crontab incremental-sync entry
(`*/5 * * * * ... hubspot_pipeline.run --incremental`) -- runs the same
sync inside the API server's own event loop via APScheduler instead of a
separate OS process, so it shows up in the normal server logs and doesn't
depend on this host's crontab being set up correctly.

Only safe with a single server process -- run with multiple uvicorn/gunicorn
workers (or multiple replicas) and each one starts its own scheduler,
causing redundant concurrent syncs. Fine today (see main.py, plain
`uvicorn main:app`, no --workers); revisit with a lock (e.g. a Postgres
advisory lock) if that ever changes.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from hubspot_pipeline import pipeline
from wootric_pipeline import pipeline as wootric_pipeline

logger = structlog.get_logger(__name__)

_INTERVAL_MINUTES = 10
_JOB_ID = "incremental_sync"


async def _sync_once() -> None:
    """Swallows and logs any exception -- APScheduler would otherwise just
    log the traceback itself, but this keeps the log line in the same
    structlog format as the rest of the app, and the same "small re-fetch
    overlap is fine" idempotency run_incremental relies on makes skipping a
    cycle harmless."""
    try:
        ticket_stats = await pipeline.run_incremental()
        csat_stats = await pipeline.run_csat_incremental()
        nps_stats = await wootric_pipeline.run_incremental()
        logger.info(
            "incremental_sync_complete", tickets=ticket_stats, csat=csat_stats, nps=nps_stats
        )
    except Exception:
        logger.exception("incremental_sync_failed")


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _sync_once,
        IntervalTrigger(minutes=_INTERVAL_MINUTES),
        id=_JOB_ID,
        next_run_time=datetime.now(timezone.utc),  # run immediately on startup, not after the first interval
        max_instances=1,  # don't overlap if a sync ever runs long
        coalesce=True,  # if we fall behind, run once on catch-up, not once per missed interval
    )
    scheduler.start()
    return scheduler

