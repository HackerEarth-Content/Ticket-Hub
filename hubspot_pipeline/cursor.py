"""Incremental sync cursor, persisted in Postgres so a scheduled run only
pulls tickets that changed since the last run instead of rescanning windows.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert

from core.database import db_manager
from core.orm import SyncCursor

_KEY = "hubspot_tickets"


async def get_cursor() -> datetime | None:
    session_factory = db_manager.session_factory()
    async with session_factory() as session:
        row = await session.get(SyncCursor, _KEY)
        return row.last_synced_at if row else None


async def set_cursor(value: datetime) -> None:
    session_factory = db_manager.session_factory()
    async with session_factory() as session:
        stmt = insert(SyncCursor).values(key=_KEY, last_synced_at=value)
        stmt = stmt.on_conflict_do_update(
            index_elements=["key"], set_={"last_synced_at": stmt.excluded.last_synced_at}
        )
        await session.execute(stmt)
        await session.commit()
