"""SQLAlchemy ORM models. Schema changes are managed via Alembic migrations --
this module only declares the mapped classes, it never creates or alters tables.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Ticket(Base):
    """A HubSpot ticket normalized for dashboard KPIs/charts."""

    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(default="")

    pipeline_id: Mapped[str]
    pipeline_label: Mapped[str]
    stage_id: Mapped[str]
    stage_label: Mapped[str]
    canonical_status: Mapped[str]

    categories: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    primary_category: Mapped[str | None]
    module: Mapped[str]

    priority: Mapped[str | None]
    derived_priority: Mapped[str]
    priority_inferred: Mapped[bool] = mapped_column(default=False)

    owner_id: Mapped[str | None]
    owner_name: Mapped[str | None]
    source_type: Mapped[str | None]

    created_at: Mapped[datetime | None] = mapped_column(index=True)
    closed_at: Mapped[datetime | None]
    last_modified_at: Mapped[datetime | None] = mapped_column(index=True)

    sla_first_response_status: Mapped[str | None]
    sla_close_status: Mapped[str | None]
    csat_rating: Mapped[str | None]


class SyncCursor(Base):
    """Tracks the last successful incremental-sync timestamp per data source."""

    __tablename__ = "sync_cursors"

    key: Mapped[str] = mapped_column(primary_key=True)
    last_synced_at: Mapped[datetime]
