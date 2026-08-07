"""Per-event ticket lookup -- powers the "download issues for an event"
export, same pattern as dashboard/customers.py's customer-name lookup, but
simpler: event_name is a controlled HubSpot dropdown (see
hubspot_pipeline.models._resolve_event_name), not free text with aliasing
problems, so no fuzzy-matching layer is needed here.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.orm import Ticket


async def get_event_names(session: AsyncSession) -> dict:
    """Every distinct event name in the DB, all-time -- feeds the event
    export's dropdown. Not period-scoped: an event from 3 months ago should
    still be pickable, and the list grows on its own as new events show up
    in synced tickets, no code change needed."""
    rows = await session.execute(
        select(Ticket.event_name).where(Ticket.event_name.isnot(None)).distinct().order_by(Ticket.event_name)
    )
    return {"event_names": [name for (name,) in rows.all()]}
