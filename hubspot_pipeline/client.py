"""Async HubSpot API client for the dashboard extraction pipeline.

Pulls tickets from Support Pipeline only (pipeline id "0") -- GT Support,
Customer Success, and Marketing Support are out of scope for this
dashboard. Chunks historical pulls into date windows to stay under
HubSpot's 10k-result search cap (see handoff.md).
"""

from __future__ import annotations

import logging
import time
from typing import AsyncIterator

import aiohttp

logger = logging.getLogger(__name__)

from core.config import settings
from hubspot_pipeline.stage_timing import STAGE_TIMING_STAGES

_BASE = "https://api.hubapi.com"

# The only pipeline this dashboard covers -- see module docstring.
_SUPPORT_PIPELINE_ID = "0"

# Verified against this portal's live property schema (2026-07-03) --
# `closedate` doesn't exist here, the real property is `closed_date`.
TICKET_PROPERTIES = [
    "subject",
    "hs_pipeline",
    "hs_pipeline_stage",
    "hs_ticket_category",
    "sub_category",
    "hs_ticket_priority",
    "hubspot_owner_id",
    "hubspot_owner_assigneddate",
    "createdate",
    "closed_date",
    "hs_lastmodifieddate",
    "hs_time_to_first_response_sla_status",
    "hs_time_to_close_sla_status",
    "hs_last_csat_rating",
    "source_type",
    # Backline/frontline reporting fields, verified live 2026-07-04.
    "final_resolution",
    "fcr",
    "backline_engineer",
    "jira_link",
    "sla_percentage",
    "time_to_close",
    "time_to_first_agent_reply",
    "hs_time_to_first_rep_assignment",
    # Customer/account name -- verified live 2026-07-06, see customer_map.py.
    "blackops_account_name",
    "other_blackops_account_name",
    "hs_primary_company_name",
] + [
    f"hs_v2_{event}_{stage['stage_id']}"
    for stage in STAGE_TIMING_STAGES.values()
    for event in ("date_entered", "date_exited", "cumulative_time_in")
]

# HubSpot search API caps any single query at 10,000 results (paging via
# `after` fails once after+limit exceeds that). 20 days is safe for ordinary
# volume (~500 tickets/day); _fetch_window bisects by time if a window turns
# out denser than that -- a bulk-modification event can concentrate ~9,000+
# tickets into under a day (observed during a --full pull, 2026-07-04), which
# no fixed chunk size can be pre-tuned against.
_CHUNK_DAYS = 20
_DAY_MS = 86_400_000
_SAFE_RESULT_CAP = 9500


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.HUBSPOT_SERVICE_KEY}",
        "Content-Type": "application/json",
    }


class HubSpotClient:
    async def fetch_pipelines(self) -> dict[str, dict]:
        """Returns {pipeline_id: {label, stages: {stage_id: label}}}"""
        url = f"{_BASE}/crm/v3/pipelines/tickets"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=_headers()) as resp:
                resp.raise_for_status()
                data = await resp.json()

        pipelines: dict[str, dict] = {}
        for p in data.get("results", []):
            stages = {s["id"]: s["label"] for s in p.get("stages", [])}
            pipelines[p["id"]] = {"label": p["label"], "stages": stages}
        return pipelines

    async def fetch_owners(self) -> dict[str, str]:
        """Returns {owner_id: full_name}, for resolving hubspot_owner_id on tickets.

        Best-effort: the private app token may not have the owners-read scope
        granted. Falls back to an empty map (tickets keep owner_id, just no
        owner_name) rather than failing the whole extraction run.
        """
        url = f"{_BASE}/crm/v3/owners"
        owners: dict[str, str] = {}
        try:
            async with aiohttp.ClientSession() as session:
                after: str | None = None
                while True:
                    params: dict[str, str | int] = {"limit": 100}
                    if after:
                        params["after"] = after
                    async with session.get(url, headers=_headers(), params=params) as resp:
                        resp.raise_for_status()
                        data = await resp.json()

                    for o in data.get("results", []):
                        name = f"{o.get('firstName') or ''} {o.get('lastName') or ''}".strip()
                        owners[o["id"]] = name or o.get("email") or o["id"]

                    after = data.get("paging", {}).get("next", {}).get("after")
                    if not after:
                        break
        except aiohttp.ClientResponseError as e:
            logger.warning("Owners lookup unavailable (status=%s) -- owner_name will be null", e.status)
            return {}
        return owners

    async def fetch_tickets(self, since_ms: int) -> AsyncIterator[dict]:
        """Yield raw ticket dicts modified since `since_ms`, from Support Pipeline only."""
        now_ms = int(time.time() * 1000)
        chunk_ms = _CHUNK_DAYS * _DAY_MS

        async with aiohttp.ClientSession() as session:
            cursor = since_ms
            while cursor < now_ms:
                window_end = min(cursor + chunk_ms, now_ms)
                async for ticket in self._fetch_window(session, cursor, window_end):
                    yield ticket
                cursor = window_end

    async def _fetch_window(
        self, session: aiohttp.ClientSession, from_ms: int, to_ms: int
    ) -> AsyncIterator[dict]:
        url = f"{_BASE}/crm/v3/objects/tickets/search"
        filters = [
            {"propertyName": "hs_lastmodifieddate", "operator": "GT", "value": str(from_ms)},
            {"propertyName": "hs_lastmodifieddate", "operator": "LTE", "value": str(to_ms)},
            {"propertyName": "hs_pipeline", "operator": "EQ", "value": _SUPPORT_PIPELINE_ID},
        ]
        body: dict = {
            "filterGroups": [{"filters": filters}],
            "properties": TICKET_PROPERTIES,
            "limit": settings.TICKET_PAGE_SIZE,
            "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "ASCENDING"}],
        }

        async with session.post(url, headers=_headers(), json=body) as resp:
            resp.raise_for_status()
            data = await resp.json()

        # `total` comes back on the very first page -- if this window is too
        # dense to page through safely, split it by time and recurse instead
        # of gambling on a fixed chunk size (see _SAFE_RESULT_CAP comment).
        if data.get("total", 0) > _SAFE_RESULT_CAP and to_ms - from_ms > 1_000:
            mid_ms = from_ms + (to_ms - from_ms) // 2
            async for ticket in self._fetch_window(session, from_ms, mid_ms):
                yield ticket
            async for ticket in self._fetch_window(session, mid_ms, to_ms):
                yield ticket
            return

        for raw in data.get("results", []):
            yield raw

        after = data.get("paging", {}).get("next", {}).get("after")
        while after:
            body["after"] = after
            async with session.post(url, headers=_headers(), json=body) as resp:
                # A cluster of tickets can share the same hs_lastmodifieddate
                # down to the millisecond (e.g. a bulk backend job stamping
                # them all at once) -- bisecting by time can never separate
                # those, so a 1,000+-ticket instant can still blow through
                # HubSpot's 10,000-result pagination cap. Stop paginating
                # this window instead of failing the whole historical pull;
                # the dropped tail is a known, logged gap, not silent loss.
                if resp.status == 400:
                    logger.warning(
                        "Pagination cap hit fetching %s..%s (window couldn't be split further, "
                        "likely a timestamp-clustered bulk update) -- stopping this window early",
                        from_ms, to_ms,
                    )
                    return
                resp.raise_for_status()
                data = await resp.json()

            for raw in data.get("results", []):
                yield raw

            after = data.get("paging", {}).get("next", {}).get("after")
