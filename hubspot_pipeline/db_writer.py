"""Persists normalized tickets to Postgres.

Assumes the `tickets` table (core.orm.Ticket) already exists -- schema is
managed via Alembic migrations, this module never creates or alters tables.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert

from core.database import db_manager
from core.orm import Ticket
from hubspot_pipeline.models import DashboardTicket


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _to_row(t: DashboardTicket) -> dict:
    row = t.model_dump(exclude={"categories"})
    row["categories"] = list(t.categories)
    for field in ("created_at", "closed_at", "last_modified_at"):
        row[field] = _parse_dt(row[field])
    return row


# Postgres caps a single query at 65535 bound parameters; Ticket has 21
# columns, so keep well under 65535/21 per statement.
_BATCH_SIZE = 1000


async def upsert_tickets(tickets: list[DashboardTicket]) -> None:
    """Insert-or-update tickets by ticket_id, batched to stay under Postgres's
    parameter-count limit on large historical/incremental pulls."""
    if not tickets:
        return

    rows = [_to_row(t) for t in tickets]
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
