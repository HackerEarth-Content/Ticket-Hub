"""Extraction pipeline: fetch Wootric NPS responses, normalize, persist.

Unlike HubSpot CSAT, a Wootric response isn't tied to a specific ticket --
NPS is a relationship-level survey, not a per-interaction one -- so there's
no ticket-matching step here, just fetch/normalize/store keyed by the
response's own created_at (see dashboard.utils.get_nps).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from core.config import settings
from hubspot_pipeline import cursor as cursor_store
from wootric_pipeline import db_writer
from wootric_pipeline.client import WootricClient
from wootric_pipeline.models import NpsSubmission

# First incremental run has no cursor yet; seed it with this lookback.
_DEFAULT_LOOKBACK_DAYS = 30


async def extract(since_ts: int) -> list[NpsSubmission]:
    """Fetch and normalize all NPS responses created since `since_ts` (unix
    seconds). Caches the end_user lookup per run since many responses share
    the same end user."""
    client = WootricClient()
    end_user_cache: dict[str, dict | None] = {}
    submissions: list[NpsSubmission] = []

    async for raw in client.fetch_responses(since_ts):
        end_user_id = raw.get("end_user_id")
        end_user = None
        if end_user_id:
            end_user_id = str(end_user_id)
            if end_user_id not in end_user_cache:
                end_user_cache[end_user_id] = await client.fetch_end_user(end_user_id)
            end_user = end_user_cache[end_user_id]
        submissions.append(NpsSubmission.from_raw(raw, end_user))
    return submissions


async def run_incremental() -> dict:
    """Sync since the last cursor (or a default lookback on first run), write
    to the DB, and advance the cursor. Meant to be called on a schedule.

    No-ops if Wootric credentials aren't configured yet, rather than failing
    the whole sync cycle every 5 minutes (see core.config.settings)."""
    if not settings.WOOTRIC_CLIENT_ID:
        return {"total": 0, "skipped": "WOOTRIC_CLIENT_ID not configured"}

    since = await cursor_store.get_cursor(cursor_store.WOOTRIC_NPS_KEY)
    since_ts = (
        int(since.timestamp())
        if since
        else int(time.time() - _DEFAULT_LOOKBACK_DAYS * 86400)
    )
    started_at = datetime.now(timezone.utc)

    submissions = await extract(since_ts)
    await db_writer.upsert_nps_responses(submissions)
    await cursor_store.set_cursor(started_at, cursor_store.WOOTRIC_NPS_KEY)

    return {"total": len(submissions)}
