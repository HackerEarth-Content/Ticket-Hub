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
    "source_type",
    # Record source (e.g. CRM_UI/CONVERSATIONS/IMPORT/BOT) -- verified
    # against this portal's live property schema (2026-08-04).
    "hs_object_source",
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
    # Event a ticket was raised for (hackathon/hiring challenge/etc) --
    # verified against this portal's live property schema (2026-08-07):
    # single-select radio with an "others" catch-all option, paired with the
    # free-text other_event_name for that case. See models.py's
    # _resolve_event_name for how the two collapse into one clean value.
    "event_name",
    "other_event_name",
    # HubSpot's own "module" dropdown (Assessment/Upskilling/Spam/etc, see
    # category_taxonomy.json's module comment for why this is a SEPARATE
    # concept from this pipeline's derived `module`) -- needed to match the
    # native "CSAT Score (Ticket owners)" report's ticket exclusion filter,
    # see dashboard/utils.py's get_csat.
    "module",
    # Ticket description -- Slack-sourced tickets embed "Reported By: <name>"
    # as their first line (verified live 2026-07-07, 14/15 tickets), a far
    # better reporter signal than the associated-contact rollup (which is
    # blank for those same 14/15). See DashboardTicket.reporter_contact_name.
    "content",
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

# CSAT eligibility, matched to this portal's native "CSAT Score (Ticket
# owners)" report (which reads off a Contact-level "Last CSAT survey rating"
# rollup, not a single survey name) -- verified live 2026-07-07:
#   - hs_survey_type == "CSAT" covers every survey of that type in this
#     portal ("Customer Satisfaction Survey - Support" + the differently
#     named "Customer Satisfaction Survey ", confirmed to sum exactly to the
#     type-wide total: 2808 + 6399 == 9207).
#   - "CSAT Sharable link new" is a CUSTOM-type survey but is CSAT-purpose by
#     name -- included explicitly since CUSTOM alone would also pull in
#     unrelated surveys like "Registration Email Survey".
CSAT_SURVEY_TYPE = "CSAT"
CSAT_SHARABLE_LINK_SURVEY_NAME = "CSAT Sharable link new"
CSAT_SUBMISSION_PROPERTIES = ["hs_value", "hs_submission_timestamp"]


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

    async def fetch_csat_submissions(self, since_ms: int) -> AsyncIterator[list[dict]]:
        """Yield pages of raw feedback_submissions dicts eligible as CSAT
        (see CSAT_SURVEY_TYPE/CSAT_SHARABLE_LINK_SURVEY_NAME), modified since
        `since_ms`. Yields pages (not individual records) so callers can
        batch the association lookups below instead of firing one per
        submission.

        Run as two separate paginated queries (type=CSAT, ~9.2k total; named
        Sharable-link survey, ~1k total) rather than one OR'd query -- combined
        they're past the 10k search-pagination cap, but each is comfortably
        under it alone."""
        eligibility_filters = [
            {"propertyName": "hs_survey_type", "operator": "EQ", "value": CSAT_SURVEY_TYPE},
            {"propertyName": "hs_survey_name", "operator": "EQ", "value": CSAT_SHARABLE_LINK_SURVEY_NAME},
        ]
        async with aiohttp.ClientSession() as session:
            for eligibility_filter in eligibility_filters:
                async for page in self._fetch_csat_query(session, eligibility_filter, since_ms):
                    yield page

    async def _fetch_csat_query(
        self, session: aiohttp.ClientSession, eligibility_filter: dict, since_ms: int
    ) -> AsyncIterator[list[dict]]:
        url = f"{_BASE}/crm/v3/objects/feedback_submissions/search"
        body: dict = {
            "filterGroups": [{"filters": [
                eligibility_filter,
                {"propertyName": "hs_submission_timestamp", "operator": "GTE", "value": str(since_ms)},
            ]}],
            "properties": CSAT_SUBMISSION_PROPERTIES,
            "limit": 100,
            "sorts": [{"propertyName": "hs_submission_timestamp", "direction": "ASCENDING"}],
        }
        while True:
            async with session.post(url, headers=_headers(), json=body) as resp:
                resp.raise_for_status()
                data = await resp.json()

            results = data.get("results", [])
            if results:
                yield results

            after = data.get("paging", {}).get("next", {}).get("after")
            if not after:
                break
            body["after"] = after

    async def fetch_submission_contacts(self, submission_ids: list[str]) -> dict[str, str]:
        """submission_id -> contact_id. The search endpoint above doesn't
        return associations, so this is a separate v4 batch association call --
        Feedback Submissions associate only to the contact who responded, not
        to a ticket (verified live 2026-07-07)."""
        if not submission_ids:
            return {}
        url = f"{_BASE}/crm/v4/associations/feedback_submissions/contacts/batch/read"
        body = {"inputs": [{"id": sid} for sid in submission_ids]}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=_headers(), json=body) as resp:
                resp.raise_for_status()
                data = await resp.json()
        return {
            r["from"]["id"]: str(r["to"][0]["toObjectId"])
            for r in data.get("results", [])
            if r.get("to")
        }

    async def fetch_ticket_pipelines(self, ticket_ids: list[str]) -> dict[str, str]:
        """ticket_id -> current hs_pipeline, via a direct batch-read (not the
        `_fetch_window` search) -- so it sees a ticket's real current pipeline
        even if that ticket has since moved out of Support Pipeline and would
        no longer match the search's `hs_pipeline EQ 0` filter. Tickets that
        no longer exist in HubSpot at all (deleted) are simply absent from
        the result. Used by pipeline.reconcile_pipeline_scope to catch drift
        the regular sync can never see."""
        if not ticket_ids:
            return {}
        url = f"{_BASE}/crm/v3/objects/tickets/batch/read"
        results: dict[str, str] = {}
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(ticket_ids), 100):
                chunk = ticket_ids[i : i + 100]
                body = {"inputs": [{"id": tid} for tid in chunk], "properties": ["hs_pipeline"]}
                async with session.post(url, headers=_headers(), json=body) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                for r in data.get("results", []):
                    results[r["id"]] = r.get("properties", {}).get("hs_pipeline")
        return results

    async def fetch_contact_tickets(self, contact_ids: list[str]) -> dict[str, list[str]]:
        """contact_id -> [ticket_id, ...] -- candidates for matching a CSAT
        response back to the ticket it was likely about (see
        hubspot_pipeline.pipeline._match_ticket)."""
        if not contact_ids:
            return {}
        url = f"{_BASE}/crm/v4/associations/contacts/tickets/batch/read"
        body = {"inputs": [{"id": cid} for cid in contact_ids]}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=_headers(), json=body) as resp:
                resp.raise_for_status()
                data = await resp.json()
        return {
            r["from"]["id"]: [str(t["toObjectId"]) for t in r.get("to", [])]
            for r in data.get("results", [])
        }
