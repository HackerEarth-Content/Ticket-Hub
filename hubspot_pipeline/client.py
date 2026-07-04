"""Async HubSpot API client for the dashboard extraction pipeline.

Pulls tickets across ALL pipelines/stages (not just closed Support Pipeline
tickets) since the dashboard needs live open/pending counts too. Chunks
historical pulls into date windows to stay under HubSpot's 10k-result
search cap (see handoff.md).
"""

from __future__ import annotations

import logging
import time
from typing import AsyncIterator

import aiohttp

logger = logging.getLogger(__name__)

from core.config import settings

_BASE = "https://api.hubapi.com"

# Verified against this portal's live property schema (2026-07-03) --
# `closedate` doesn't exist here, the real property is `closed_date`.
TICKET_PROPERTIES = [
    "subject",
    "hs_pipeline",
    "hs_pipeline_stage",
    "hs_ticket_category",
    "hs_ticket_priority",
    "hubspot_owner_id",
    "createdate",
    "closed_date",
    "hs_lastmodifieddate",
    "hs_time_to_first_response_sla_status",
    "hs_time_to_close_sla_status",
    "hs_last_csat_rating",
    "source_type",
]

# HubSpot search API caps any single query at 10,000 results; chunk date
# ranges to stay well under that (observed peak ~500 tickets/day).
_CHUNK_DAYS = 20
_DAY_MS = 86_400_000


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
        """Yield raw ticket dicts modified since `since_ms`, across all pipelines."""
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
        ]

        after: str | None = None
        while True:
            body: dict = {
                "filterGroups": [{"filters": filters}],
                "properties": TICKET_PROPERTIES,
                "limit": settings.TICKET_PAGE_SIZE,
                "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "ASCENDING"}],
            }
            if after:
                body["after"] = after

            async with session.post(url, headers=_headers(), json=body) as resp:
                resp.raise_for_status()
                data = await resp.json()

            for raw in data.get("results", []):
                yield raw

            after = data.get("paging", {}).get("next", {}).get("after")
            if not after:
                break
