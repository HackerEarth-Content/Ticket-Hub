"""SQLAlchemy ORM models. Schema changes are managed via Alembic migrations --
this module only declares the mapped classes, it never creates or alters tables.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from fastapi_users.db import SQLAlchemyBaseUserTable, SQLAlchemyBaseOAuthAccountTable

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)

from sqlalchemy.orm import (
    Mapped,
    declarative_base,
    mapped_column,
    relationship,
    synonym,
    declared_attr,
)

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
    sub_category: Mapped[str | None]
    customer_name: Mapped[str | None] = mapped_column(index=True)

    priority: Mapped[str | None]
    derived_priority: Mapped[str]
    priority_inferred: Mapped[bool] = mapped_column(default=False)

    owner_id: Mapped[str | None]
    owner_name: Mapped[str | None]
    owner_assigned_at: Mapped[datetime | None]
    source_type: Mapped[str | None]

    created_at: Mapped[datetime | None] = mapped_column(index=True)
    closed_at: Mapped[datetime | None]
    last_modified_at: Mapped[datetime | None] = mapped_column(index=True)

    sla_first_response_status: Mapped[str | None]
    sla_close_status: Mapped[str | None]
    sla_met: Mapped[bool | None]
    csat_rating: Mapped[str | None]

    final_resolution: Mapped[str | None]
    resolution_bucket: Mapped[str]
    actionable: Mapped[bool] = mapped_column(default=True)
    fcr: Mapped[bool | None]
    backline_engineer: Mapped[str | None] = mapped_column(index=True)
    backline_path: Mapped[str | None]
    jira_link: Mapped[str | None]

    time_to_close_hours: Mapped[float | None]
    time_to_first_agent_reply_hours: Mapped[float | None]
    time_to_first_rep_assignment_hours: Mapped[float | None]

    # stage_key -> {entered_at, exited_at, cumulative_hours}, see
    # hubspot_pipeline.stage_timing.STAGE_TIMING_STAGES.
    stage_timings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class SyncCursor(Base):
    """Tracks the last successful incremental-sync timestamp per data source."""

    __tablename__ = "sync_cursors"

    key: Mapped[str] = mapped_column(primary_key=True)
    last_synced_at: Mapped[datetime]


class OAuthAccount(SQLAlchemyBaseOAuthAccountTable[str], Base):
    id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        default=lambda: str(uuid4()),
        server_default=text("uuid_generate_v4()::text"),
    )

    @declared_attr
    def user_id(cls) -> Mapped[str]:
        return mapped_column(
            Text, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False
        )



class User(SQLAlchemyBaseUserTable[str], Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(
        "user_id",
        Text,
        primary_key=True,
        default=lambda: str(uuid4()),
        server_default=text("uuid_generate_v4()::text"),
    )
    name: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )

    # We can keep this synonym or remove it if id maps to user_id column
    user_id = synonym("id")

    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined", cascade="all, delete-orphan"
    )