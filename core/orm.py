"""SQLAlchemy ORM models. Schema changes are managed via Alembic migrations --
this module only declares the mapped classes, it never creates or alters tables.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any
from uuid import uuid4


from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from fastapi_users.db import SQLAlchemyBaseUserTable, SQLAlchemyBaseOAuthAccountTable

from sqlalchemy import (
    TIMESTAMP,
    ForeignKey,
    Time,
    Text,
    text,
)

from sqlalchemy.orm import (
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
    hubspot_module: Mapped[str | None]
    sub_category: Mapped[str | None]
    customer_name: Mapped[str | None] = mapped_column(index=True)
    event_name: Mapped[str | None] = mapped_column(index=True)
    other_event_name: Mapped[str | None]

    priority: Mapped[str | None]
    derived_priority: Mapped[str]
    priority_inferred: Mapped[bool] = mapped_column(default=False)

    owner_id: Mapped[str | None]
    owner_name: Mapped[str | None]
    owner_assigned_at: Mapped[datetime | None]
    source_type: Mapped[str | None]
    record_source: Mapped[str | None]
    reporter_contact_name: Mapped[str | None]
    slack_workflow: Mapped[str | None]
    slack_channel: Mapped[str | None]

    created_at: Mapped[datetime | None] = mapped_column(index=True)
    closed_at: Mapped[datetime | None]
    last_modified_at: Mapped[datetime | None] = mapped_column(index=True)

    sla_first_response_status: Mapped[str | None]
    sla_close_status: Mapped[str | None]
    sla_met: Mapped[bool | None]

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


class CsatResponse(Base):
    """An email CSAT survey response (HubSpot Feedback Submissions, survey
    "Customer Satisfaction Survey - Support") -- replaces the old
    Ticket.csat_rating (hs_last_csat_rating) chat rollup, which had an
    unconfirmed rating scale. This survey's scale is confirmed via
    hs_response_group: 0=Detractor, 1=Passive, 2=Promoter.

    ticket_id/owner_id/owner_name are a best-effort match, not a HubSpot
    association -- see hubspot_pipeline.pipeline._match_ticket for why.
    """

    __tablename__ = "csat_responses"

    submission_id: Mapped[str] = mapped_column(primary_key=True)
    rating: Mapped[int]
    submitted_at: Mapped[datetime] = mapped_column(index=True)
    contact_id: Mapped[str | None]
    ticket_id: Mapped[str | None] = mapped_column(index=True)
    owner_id: Mapped[str | None]
    owner_name: Mapped[str | None]


class NpsResponse(Base):
    """A Wootric NPS survey response. Unlike CsatResponse, this isn't tied to
    a ticket -- NPS is a relationship-level survey, not a per-interaction one
    -- so it's scoped for KPIs by its own created_at (see dashboard.utils.get_nps).
    """

    __tablename__ = "nps_responses"

    response_id: Mapped[str] = mapped_column(primary_key=True)
    end_user_id: Mapped[str | None]
    email: Mapped[str | None]
    score: Mapped[int]
    text: Mapped[str | None]
    completed: Mapped[bool | None]
    excluded_from_calculations: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(index=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    properties: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class SyncCursor(Base):
    """Tracks the last successful incremental-sync timestamp per data source."""

    __tablename__ = "sync_cursors"

    key: Mapped[str] = mapped_column(primary_key=True)
    last_synced_at: Mapped[datetime]


class DashboardLink(Base):
    """A user-added name+URL shortcut shown on a dashboard card (currently
    just the Frontline Metric Dashboard's "Links" button) -- editable and
    deletable in place."""

    __tablename__ = "dashboard_links"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    url: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class FrontlineAgent(Base):
    """A support agent shown on the "Frontline Agents" shift roster --
    editable in place (add/remove/edit), same as DashboardLink. The roster
    is the single source of truth for who's on shift: the live-status strip
    derives "who's active now" from this table + AgentShift rather than
    keeping a separate status flag that could drift out of sync."""

    __tablename__ = "frontline_agents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    email: Mapped[str]
    slack_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class AgentShift(Base):
    """One day's shift for one agent (7 rows/agent, one per day_of_week).
    start_time/end_time are IST wall-clock times (Asia/Kolkata, same
    convention as dashboard.utils._IST) -- end_time < start_time means the
    shift crosses midnight (e.g. 16:00-01:00)."""

    __tablename__ = "agent_shifts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("frontline_agents.id", ondelete="CASCADE")
    )
    day_of_week: Mapped[int]  # 0=Monday .. 6=Sunday
    is_week_off: Mapped[bool] = mapped_column(default=False)
    # A holiday (e.g. a public holiday) is off-shift like a week-off, but
    # tracked separately so the roster can tell "doesn't normally work this
    # day" apart from "would normally work, but not this particular day".
    is_holiday: Mapped[bool] = mapped_column(default=False)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)


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
