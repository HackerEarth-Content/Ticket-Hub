"""Query/aggregation logic backing the dashboard routes.

Routes in api.py stay thin -- all SQL and KPI math lives here so it's
testable and reusable independent of FastAPI.

Response fields spell out full words (no "pct"/"mttr"-style shorthand) so
the JSON is self-explanatory to whoever's building the frontend against it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.orm import SyncCursor, Ticket

_OPEN_STATUSES = ("New", "Open", "Pending", "Closing")
_BREACH_STATUSES = ("Due Soon", "Overdue")

_PERIODS = ("today", "yesterday", "week", "month")


def resolve_period(period: str) -> tuple[datetime, datetime]:
    """Map a period name to a (period_start, period_end) UTC datetime range."""
    if period not in _PERIODS:
        raise ValueError(f"Unknown period {period!r}, expected one of {_PERIODS}")

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "today":
        return today_start, now
    if period == "yesterday":
        return today_start - timedelta(days=1), today_start
    if period == "week":
        return now - timedelta(days=7), now
    return now - timedelta(days=30), now  # month


def _resolution_time_hours_expr():
    return func.extract("epoch", Ticket.closed_at - Ticket.created_at) / 3600


def _median_resolution_time_hours_expr():
    """Median (closed_at - created_at) in hours. Used instead of a mean --
    a handful of old backlog tickets closed in a period can drag a mean up
    to a number no actual ticket resembles (see handoff.md discussion);
    median reflects the typical ticket instead."""
    return func.percentile_cont(0.5).within_group(_resolution_time_hours_expr())


def _percentage(part: int | None, total: int | None) -> float | None:
    return round(100 * (part or 0) / total, 1) if total else None


def _utc_iso(value: datetime) -> str:
    """core.orm's datetime columns are TIMESTAMP WITHOUT TIME ZONE, storing
    UTC wall-clock values with no timezone marker attached. Serializing them
    with bare .isoformat() drops that context, so `new Date(...)` in the
    browser misreads them as local time instead of UTC. Attach it explicitly
    before returning any such value in a response."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


async def get_live_today(session: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    status_rows = await session.execute(
        select(Ticket.canonical_status, func.count())
        .where(Ticket.canonical_status.in_(_OPEN_STATUSES))
        .group_by(Ticket.canonical_status)
    )
    resolved_today = await session.scalar(
        select(func.count()).where(
            Ticket.canonical_status == "Resolved", Ticket.closed_at >= today_start
        )
    )
    breaching_soon = await session.scalar(
        select(func.count()).where(
            Ticket.canonical_status.in_(_OPEN_STATUSES),
            or_(
                Ticket.sla_first_response_status.in_(_BREACH_STATUSES),
                Ticket.sla_close_status.in_(_BREACH_STATUSES),
            ),
        )
    )

    return {
        "open_ticket_count_by_status": dict(status_rows.all()),
        "resolved_today_count": resolved_today or 0,
        "sla_breaching_soon_count": breaching_soon or 0,
        "generated_at": now.isoformat(),
    }


async def get_summary(session: AsyncSession, period: str) -> dict:
    period_start, period_end = resolve_period(period)

    created_count = await session.scalar(
        select(func.count()).where(Ticket.created_at.between(period_start, period_end))
    )
    resolved_count = await session.scalar(
        select(func.count()).where(Ticket.closed_at.between(period_start, period_end))
    )
    median_resolution_time_hours = await session.scalar(
        select(_median_resolution_time_hours_expr()).where(
            Ticket.closed_at.between(period_start, period_end)
        )
    )
    resolved_over_48_hours_count = await session.scalar(
        select(func.count()).where(
            Ticket.closed_at.between(period_start, period_end),
            _resolution_time_hours_expr() > 48,
        )
    )

    resolution_sla_rows = await session.execute(
        select(Ticket.sla_close_status, func.count())
        .where(
            Ticket.closed_at.between(period_start, period_end),
            Ticket.sla_close_status.isnot(None),
        )
        .group_by(Ticket.sla_close_status)
    )
    resolution_sla_breakdown = dict(resolution_sla_rows.all())
    resolution_sla_evaluated_count = resolution_sla_breakdown.get(
        "Completed on time", 0
    ) + resolution_sla_breakdown.get("Completed late", 0)

    return {
        "period": period,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "tickets_created_count": created_count or 0,
        "tickets_resolved_count": resolved_count or 0,
        "median_resolution_time_hours": (
            round(median_resolution_time_hours, 1) if median_resolution_time_hours is not None else None
        ),
        "tickets_resolved_over_48_hours_count": resolved_over_48_hours_count or 0,
        "sla_breach_percentage": _percentage(
            resolution_sla_breakdown.get("Completed late", 0), resolution_sla_evaluated_count
        ),
    }


async def get_volume_trend(session: AsyncSession, granularity: str, period: str) -> list[dict]:
    # "hour" matters for period=today/yesterday -- those spans collapse to a
    # single "day" bucket otherwise, which renders as one point on a line chart.
    if granularity not in ("hour", "day", "week", "month"):
        raise ValueError(f"Unknown granularity {granularity!r}")
    period_start, period_end = resolve_period(period)

    created_rows = await session.execute(
        select(func.date_trunc(granularity, Ticket.created_at).label("bucket"), func.count())
        .where(Ticket.created_at.between(period_start, period_end))
        .group_by("bucket")
    )
    resolved_rows = await session.execute(
        select(func.date_trunc(granularity, Ticket.closed_at).label("bucket"), func.count())
        .where(Ticket.closed_at.between(period_start, period_end))
        .group_by("bucket")
    )

    created_count_by_bucket = dict(created_rows.all())
    resolved_count_by_bucket = dict(resolved_rows.all())
    buckets = sorted(set(created_count_by_bucket) | set(resolved_count_by_bucket))

    return [
        {
            "date": _utc_iso(bucket),
            "tickets_created_count": created_count_by_bucket.get(bucket, 0),
            "tickets_resolved_count": resolved_count_by_bucket.get(bucket, 0),
        }
        for bucket in buckets
    ]


async def get_pipelines(session: AsyncSession) -> dict:
    """Lookup for the pipeline_id filter used elsewhere -- avoids needing to
    know HubSpot's numeric pipeline IDs by heart."""
    rows = await session.execute(select(Ticket.pipeline_id, Ticket.pipeline_label).distinct())
    return {
        "pipelines": [
            {"pipeline_id": pipeline_id, "pipeline_label": pipeline_label}
            for pipeline_id, pipeline_label in rows.all()
        ]
    }


async def get_stage_distribution(
    session: AsyncSession, period: str, pipeline_id: str | None
) -> dict:
    """Granular breakdown by raw HubSpot stage (e.g. "Pending on Engineering",
    "Pending on BE/AE") -- get_status_distribution collapses these into a
    single "Pending" bucket, which hides exactly this team-routing detail."""
    period_start, period_end = resolve_period(period)
    stmt = select(Ticket.pipeline_label, Ticket.stage_label, func.count()).where(
        Ticket.created_at.between(period_start, period_end)
    )
    if pipeline_id:
        stmt = stmt.where(Ticket.pipeline_id == pipeline_id)
    rows = await session.execute(stmt.group_by(Ticket.pipeline_label, Ticket.stage_label))

    breakdown: dict[str, dict[str, int]] = {}
    for pipeline_label, stage_label, count in rows.all():
        breakdown.setdefault(pipeline_label, {})[stage_label] = count
    return {"ticket_count_by_pipeline_and_stage": breakdown}


async def get_module_distribution(session: AsyncSession, period: str) -> dict:
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(Ticket.module, func.count())
        .where(Ticket.created_at.between(period_start, period_end))
        .group_by(Ticket.module)
    )
    return {"ticket_count_by_module": dict(rows.all())}


async def get_status_distribution(
    session: AsyncSession, period: str, pipeline_id: str | None
) -> dict:
    period_start, period_end = resolve_period(period)
    stmt = select(Ticket.canonical_status, func.count()).where(
        Ticket.created_at.between(period_start, period_end)
    )
    if pipeline_id:
        stmt = stmt.where(Ticket.pipeline_id == pipeline_id)
    rows = await session.execute(stmt.group_by(Ticket.canonical_status))
    return {"ticket_count_by_status": dict(rows.all())}


async def get_median_resolution_time_by_priority(session: AsyncSession, period: str) -> dict:
    """Median hours between a ticket being created and closed, broken down by
    priority. Median rather than mean -- see _median_resolution_time_hours_expr."""
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(Ticket.derived_priority, _median_resolution_time_hours_expr())
        .where(Ticket.closed_at.between(period_start, period_end))
        .group_by(Ticket.derived_priority)
    )
    return {
        "median_resolution_time_hours_by_priority": {
            priority: round(hours, 1) for priority, hours in rows.all() if hours is not None
        }
    }


async def get_sla_kpis(session: AsyncSession, period: str) -> dict:
    period_start, period_end = resolve_period(period)

    async def _breakdown(column) -> dict:
        rows = await session.execute(
            select(column, func.count())
            .where(Ticket.created_at.between(period_start, period_end), column.isnot(None))
            .group_by(column)
        )
        return dict(rows.all())

    def _breach_percentage(breakdown: dict) -> float | None:
        evaluated = breakdown.get("Completed on time", 0) + breakdown.get("Completed late", 0)
        return _percentage(breakdown.get("Completed late", 0), evaluated)

    first_response_status_breakdown = await _breakdown(Ticket.sla_first_response_status)
    resolution_status_breakdown = await _breakdown(Ticket.sla_close_status)

    return {
        "first_response_sla_status_breakdown": first_response_status_breakdown,
        "first_response_sla_breach_percentage": _breach_percentage(
            first_response_status_breakdown
        ),
        "resolution_sla_status_breakdown": resolution_status_breakdown,
        "resolution_sla_breach_percentage": _breach_percentage(resolution_status_breakdown),
    }


async def get_csat(session: AsyncSession, period: str) -> dict:
    """Raw rating distribution, not an average -- HubSpot exposes
    hs_last_csat_rating as an opaque rollup with no documented scale, so an
    averaged "score" would be a made-up number. Confirm the scale with
    whoever set up the survey before turning this into a single KPI value.
    """
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(Ticket.csat_rating, func.count())
        .where(
            Ticket.created_at.between(period_start, period_end), Ticket.csat_rating.isnot(None)
        )
        .group_by(Ticket.csat_rating)
    )
    response_count_by_rating = dict(rows.all())
    return {
        "total_response_count": sum(response_count_by_rating.values()),
        "response_count_by_rating": response_count_by_rating,
        "rating_scale_confirmed": False,
    }


async def get_agent_kpis(session: AsyncSession, period: str) -> list[dict]:
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(
            Ticket.owner_id,
            Ticket.owner_name,
            func.count(),
            _median_resolution_time_hours_expr(),
        )
        .where(Ticket.created_at.between(period_start, period_end), Ticket.owner_id.isnot(None))
        .group_by(Ticket.owner_id, Ticket.owner_name)
        .order_by(func.count().desc())
    )
    return [
        {
            "owner_id": owner_id,
            "owner_name": owner_name,
            "ticket_count": count,
            "median_resolution_time_hours": round(hours, 1) if hours is not None else None,
        }
        for owner_id, owner_name, count, hours in rows.all()
    ]


async def get_data_quality(session: AsyncSession, period: str) -> dict:
    period_start, period_end = resolve_period(period)

    total_count = await session.scalar(
        select(func.count()).where(Ticket.created_at.between(period_start, period_end))
    )
    priority_inferred_count = await session.scalar(
        select(func.count()).where(
            Ticket.created_at.between(period_start, period_end),
            Ticket.priority_inferred.is_(True),
        )
    )
    uncategorized_count = await session.scalar(
        select(func.count()).where(
            Ticket.created_at.between(period_start, period_end),
            Ticket.module == "Uncategorized",
        )
    )
    # Broken down by stage (e.g. "Pending on Engineering" vs "Pending on
    # BE/AE") rather than a single number -- this is the bottleneck-by-team
    # signal, so it needs to say which team, not just a total count.
    stuck_pending_rows = await session.execute(
        select(Ticket.stage_label, func.count())
        .where(
            Ticket.canonical_status == "Pending",
            Ticket.last_modified_at < datetime.now(timezone.utc) - timedelta(hours=48),
        )
        .group_by(Ticket.stage_label)
    )
    stuck_pending_by_stage = dict(stuck_pending_rows.all())

    return {
        "priority_inferred_percentage": _percentage(priority_inferred_count, total_count),
        "uncategorized_ticket_percentage": _percentage(uncategorized_count, total_count),
        "tickets_pending_over_48_hours_count_by_stage": stuck_pending_by_stage,
        "tickets_pending_over_48_hours_total": sum(stuck_pending_by_stage.values()),
    }


async def get_sync_status(session: AsyncSession) -> dict:
    cursor_row = await session.get(SyncCursor, "hubspot_tickets")
    total_ticket_count = await session.scalar(select(func.count()).select_from(Ticket))
    return {
        "last_synced_at": _utc_iso(cursor_row.last_synced_at) if cursor_row else None,
        "total_ticket_count": total_ticket_count or 0,
    }
