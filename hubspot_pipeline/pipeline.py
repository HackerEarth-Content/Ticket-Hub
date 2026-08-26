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
from hubspot_pipeline import db_writer
from hubspot_pipeline.client import HubSpotClient, _SUPPORT_PIPELINE_ID
from hubspot_pipeline.db_writer import parse_iso, upsert_tickets
from hubspot_pipeline.models import CsatSubmission, DashboardTicket

# First incremental run has no cursor yet; seed it with this lookback.
_DEFAULT_LOOKBACK_DAYS = 30
_CSAT_DEFAULT_LOOKBACK_DAYS = 30


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


async def reconcile_pipeline_scope() -> dict:
    """Catches tickets that moved out of Support Pipeline (or were deleted)
    in HubSpot after being synced -- the regular incremental/full sync can
    never see this, since its search is itself filtered to
    `hs_pipeline EQ 0` (see client.py), so a ticket that left never matches
    that filter again and would otherwise stay frozen in our DB forever at
    its last-known status. Scoped to non-terminal tickets only -- a small,
    bounded set -- and done via a direct batch-read, which (unlike search)
    isn't filtered by pipeline."""
    ticket_ids = await db_writer.fetch_non_terminal_ticket_ids()
    client = HubSpotClient()
    current_pipelines = await client.fetch_ticket_pipelines(ticket_ids)

    # .get(tid) is None (not `_SUPPORT_PIPELINE_ID`) for a ticket HubSpot no
    # longer returns at all -- deleted tickets get cleaned up here too.
    stale_ids = [
        tid for tid in ticket_ids if current_pipelines.get(tid) != _SUPPORT_PIPELINE_ID
    ]
    await db_writer.delete_tickets(stale_ids)

    return {"checked": len(ticket_ids), "removed": len(stale_ids)}


def _match_ticket(
    submitted_at: datetime,
    candidate_ticket_ids: list[str],
    ticket_info: dict[str, tuple],
) -> tuple[str | None, str | None, str | None]:
    """Picks the candidate ticket closed nearest the survey's submission
    time -- the best available proxy for "which ticket this CSAT response is
    about", since Feedback Submissions only associate to the contact (see
    client.fetch_contact_tickets). Wrong when a contact has multiple tickets
    closed close together; upgrade path is a direct submission-to-ticket
    association if HubSpot's survey automation ever adds one."""
    # Ticket.closed_at comes back tz-naive (column has no timezone, like every
    # other timestamp on Ticket) -- strip tzinfo from both sides to compare.
    if submitted_at.tzinfo is not None:
        submitted_at = submitted_at.replace(tzinfo=None)

    best_id = best_owner_id = best_owner_name = None
    best_diff = None
    for ticket_id in candidate_ticket_ids:
        closed_at, owner_id, owner_name = ticket_info.get(ticket_id, (None, None, None))
        if closed_at is None:
            continue
        if closed_at.tzinfo is not None:
            closed_at = closed_at.replace(tzinfo=None)
        diff = abs((submitted_at - closed_at).total_seconds())
        if best_diff is None or diff < best_diff:
            best_id, best_owner_id, best_owner_name, best_diff = (
                ticket_id,
                owner_id,
                owner_name,
                diff,
            )
    return best_id, best_owner_id, best_owner_name


async def extract_csat(since_ms: int) -> list[CsatSubmission]:
    """Fetch and match Support CSAT survey responses since `since_ms`.
    Ticket matching reads from our own DB (via db_writer), so tickets should
    be synced before this runs in the same pass."""
    client = HubSpotClient()
    submissions: list[CsatSubmission] = []
    async for page in client.fetch_csat_submissions(since_ms):
        submission_ids = [r["id"] for r in page]
        contact_by_submission = await client.fetch_submission_contacts(submission_ids)
        contact_ids = list(set(contact_by_submission.values()))
        tickets_by_contact = await client.fetch_contact_tickets(contact_ids)
        candidate_ticket_ids = list(
            {tid for tids in tickets_by_contact.values() for tid in tids}
        )
        ticket_info = await db_writer.fetch_ticket_owner_info(candidate_ticket_ids)

        for raw in page:
            submission_id = raw["id"]
            contact_id = contact_by_submission.get(submission_id)
            candidates = tickets_by_contact.get(contact_id, []) if contact_id else []
            submitted_at = parse_iso(raw["properties"]["hs_submission_timestamp"])
            ticket_id, owner_id, owner_name = _match_ticket(
                submitted_at, candidates, ticket_info
            )
            submissions.append(
                CsatSubmission.from_raw(
                    raw, contact_id, ticket_id, owner_id, owner_name
                )
            )
    return submissions


async def run_csat_incremental() -> dict:
    """Sync CSAT responses since the last cursor (or a default lookback on
    first run). Meant to run right after run_incremental, since matching
    needs the tickets it just synced."""
    since = await cursor_store.get_cursor(cursor_store.CSAT_KEY)
    since_ms = (
        int(since.timestamp() * 1000)
        if since
        else int((time.time() - _CSAT_DEFAULT_LOOKBACK_DAYS * 86400) * 1000)
    )
    started_at = datetime.now(timezone.utc)

    submissions = await extract_csat(since_ms)
    await db_writer.upsert_csat_responses(submissions)
    await cursor_store.set_cursor(started_at, cursor_store.CSAT_KEY)

    return {
        "total": len(submissions),
        "matched_to_ticket_count": sum(1 for s in submissions if s.ticket_id),
    }


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
        )
        if n
        else 0.0,
        "unknown_status_count": sum(t.canonical_status == "Unknown" for t in tickets),
    }


def write_jsonl(tickets: list[DashboardTicket], path: Path) -> None:
    with path.open("w") as f:
        for t in tickets:
            f.write(t.model_dump_json() + "\n")
