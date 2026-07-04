"""Extraction pipeline: fetch HubSpot tickets, normalize for dashboard KPIs.

Postgres storage is a separate next step (see handoff.md) -- this just
fetches, transforms, and optionally dumps a JSONL snapshot so the FastAPI/
Postgres layer has a stable input format to build against.
"""

from __future__ import annotations

import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from hubspot_pipeline import cursor as cursor_store
from hubspot_pipeline.client import HubSpotClient
from hubspot_pipeline.db_writer import upsert_tickets
from hubspot_pipeline.models import DashboardTicket

# First incremental run has no cursor yet; seed it with this lookback.
_DEFAULT_LOOKBACK_DAYS = 30


async def extract(since_ms: int) -> list[DashboardTicket]:
    """Fetch and normalize all tickets modified since `since_ms`."""
    client = HubSpotClient()
    pipelines = await client.fetch_pipelines()
    owners = await client.fetch_owners()

    tickets: list[DashboardTicket] = []
    async for raw in client.fetch_tickets(since_ms):
        tickets.append(DashboardTicket.from_raw(raw, pipelines, owners))
    return tickets


async def run_incremental() -> dict:
    """Sync since the last cursor (or a default lookback on first run), write
    to the DB, and advance the cursor. Meant to be called on a schedule."""
    since = await cursor_store.get_cursor()
    since_ms = (
        int(since.timestamp() * 1000)
        if since
        else int((time.time() - _DEFAULT_LOOKBACK_DAYS * 86400) * 1000)
    )
    # Capture the cursor before fetching, not after, so tickets modified
    # mid-run aren't skipped by the next sync (a small re-fetch overlap is
    # fine since upserts are idempotent).
    started_at = datetime.now(timezone.utc)

    tickets = await extract(since_ms)
    await upsert_tickets(tickets)
    await cursor_store.set_cursor(started_at)

    return summarize(tickets)


def summarize(tickets: list[DashboardTicket]) -> dict:
    """Aggregate counts used to sanity-check an extraction run."""
    n = len(tickets)
    return {
        "total": n,
        "by_status": dict(Counter(t.canonical_status for t in tickets)),
        "by_module": dict(Counter(t.module for t in tickets)),
        "by_derived_priority": dict(Counter(t.derived_priority for t in tickets)),
        "priority_inferred_pct": round(
            100 * sum(t.priority_inferred for t in tickets) / n, 1
        ) if n else 0.0,
        "unknown_status_count": sum(t.canonical_status == "Unknown" for t in tickets),
    }


def write_jsonl(tickets: list[DashboardTicket], path: Path) -> None:
    with path.open("w") as f:
        for t in tickets:
            f.write(t.model_dump_json() + "\n")
