"""Persists normalized tickets to Postgres.

Assumes the `tickets` table (core.orm.Ticket) already exists -- schema is
managed via Alembic migrations, this module never creates or alters tables.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from core.database import db_manager
from core.orm import CsatResponse, Ticket
from hubspot_pipeline.models import CsatSubmission, DashboardTicket

# Tickets created before this date were intentionally purged from the DB
# (2026-07-07). HubSpot's ticket search only filters by hs_lastmodifieddate,
# so an old ticket touched again after the purge (reopened, commented,
# closed) comes back through every sync -- with its true, older createdate --
# and undoes the purge one ticket at a time. Drop those here, the one place
# every sync path (--full/--days/--incremental) upserts through.
_CREATED_FLOOR = datetime(2026, 2, 2, tzinfo=timezone.utc)


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _to_row(t: DashboardTicket) -> dict:
    row = t.model_dump(exclude={"categories"})
    row["categories"] = list(t.categories)
    for field in ("created_at", "closed_at", "last_modified_at", "owner_assigned_at"):
        row[field] = parse_iso(row[field])
    return row


# Postgres caps a single query at 65535 bound parameters; Ticket has 34
# columns, so keep well under 65535/34 per statement.
_BATCH_SIZE = 1000


def _drop_pre_floor(rows: list[dict]) -> list[dict]:
    """Rows with no created_at pass through untouched (rare/unexpected, not our call to drop)."""
    return [r for r in rows if r["created_at"] is None or r["created_at"] >= _CREATED_FLOOR]


async def upsert_tickets(tickets: list[DashboardTicket]) -> None:
    """Insert-or-update tickets by ticket_id, batched to stay under Postgres's
    parameter-count limit on large historical/incremental pulls."""
    if not tickets:
        return

    rows = _drop_pre_floor([_to_row(t) for t in tickets])
    if not rows:
        return
    update_cols = {c: c for c in rows[0] if c != "ticket_id"}

    session_factory = db_manager.session_factory()
    async with session_factory() as session:
        for i in range(0, len(rows), _BATCH_SIZE):
            batch = rows[i : i + _BATCH_SIZE]
            stmt = insert(Ticket).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticket_id"],
                set_={c: getattr(stmt.excluded, c) for c in update_cols},
            )
            await session.execute(stmt)
        await session.commit()


async def fetch_ticket_owner_info(ticket_ids: list[str]) -> dict[str, tuple]:
    """ticket_id -> (closed_at, owner_id, owner_name), for matching a CSAT
    submission's candidate tickets against already-synced ticket data (see
    hubspot_pipeline.pipeline._match_ticket)."""
    if not ticket_ids:
        return {}
    session_factory = db_manager.session_factory()
    async with session_factory() as session:
        rows = await session.execute(
            select(Ticket.ticket_id, Ticket.closed_at, Ticket.owner_id, Ticket.owner_name)
            .where(Ticket.ticket_id.in_(ticket_ids))
        )
        return {tid: (closed_at, owner_id, owner_name) for tid, closed_at, owner_id, owner_name in rows.all()}


async def upsert_csat_responses(responses: list[CsatSubmission]) -> None:
    """Insert-or-update CSAT responses by submission_id."""
    if not responses:
        return

    rows = []
    for r in responses:
        row = r.model_dump()
        row["submitted_at"] = parse_iso(row["submitted_at"])
        rows.append(row)

    session_factory = db_manager.session_factory()
    async with session_factory() as session:
        for i in range(0, len(rows), _BATCH_SIZE):
            batch = rows[i : i + _BATCH_SIZE]
            stmt = insert(CsatResponse).values(batch)
            update_cols = {c: c for c in batch[0] if c != "submission_id"}
            stmt = stmt.on_conflict_do_update(
                index_elements=["submission_id"],
                set_={c: getattr(stmt.excluded, c) for c in update_cols},
            )
            await session.execute(stmt)
        await session.commit()
