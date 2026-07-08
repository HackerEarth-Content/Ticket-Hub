"""Persists normalized Wootric NPS responses to Postgres.

Assumes the `nps_responses` table (core.orm.NpsResponse) already exists --
schema is managed via Alembic migrations, this module never creates or
alters tables.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert

from core.database import db_manager
from core.orm import NpsResponse
from wootric_pipeline.models import NpsSubmission

_BATCH_SIZE = 1000


async def upsert_nps_responses(responses: list[NpsSubmission]) -> None:
    """Insert-or-update NPS responses by response_id."""
    if not responses:
        return

    rows = []
    for r in responses:
        row = r.model_dump()
        row["created_at"] = datetime.fromisoformat(row["created_at"])
        rows.append(row)

    session_factory = db_manager.session_factory()
    async with session_factory() as session:
        for i in range(0, len(rows), _BATCH_SIZE):
            batch = rows[i : i + _BATCH_SIZE]
            stmt = insert(NpsResponse).values(batch)
            update_cols = {c: c for c in batch[0] if c != "response_id"}
            stmt = stmt.on_conflict_do_update(
                index_elements=["response_id"],
                set_={c: getattr(stmt.excluded, c) for c in update_cols},
            )
            await session.execute(stmt)
        await session.commit()
