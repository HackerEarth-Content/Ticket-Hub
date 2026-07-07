"""Query/aggregation logic backing the dashboard's core/overview routes.

Routes in dashboard_routes.py stay thin -- all SQL and KPI math lives here so it's
testable and reusable independent of FastAPI.

Response fields spell out full words (no "pct"/"mttr"-style shorthand) so
the JSON is self-explanatory to whoever's building the frontend against it.

Backline-specific and frontline-specific KPIs live in backline.py and
frontline.py -- this module holds the shared helpers (resolve_period,
_percentage, _utc_iso, _parse_iso) both of those import, plus the
overview/summary/agent/sync KPIs that don't belong to either team.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.orm import SyncCursor, Ticket

_OPEN_STATUSES = ("New", "Open", "Pending", "Closing")
_BREACH_STATUSES = ("Due Soon", "Overdue")

_PERIODS = ("today", "yesterday", "week", "month")

# The support team works in IST -- "today"/"yesterday" must split on IST
# midnight, not UTC midnight, or a ticket from the first ~5.5 hours of the
# IST day gets counted into "yesterday" instead.
_IST = ZoneInfo("Asia/Kolkata")

# First Response Time SLA threshold, per the backline/frontline reporting
# spec (build_frontline_report.py FRT_SLA_MINS = 30).
_FRT_SLA_HOURS = 0.5


def _ist_today_start(now: datetime) -> datetime:
    """IST midnight for the calendar day `now` falls on, expressed back in
    UTC. Every "today" boundary in this module must go through this -- a
    plain UTC midnight is 5.5h off from the support team's actual day
    boundary, over- or under-counting whatever happened in that window."""
    return now.astimezone(_IST).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def resolve_period(period: str) -> tuple[datetime, datetime]:
    """Map a period name to a (period_start, period_end) UTC datetime range.

    Also accepts "custom:YYYY-MM-DD:YYYY-MM-DD" (both dates are IST calendar
    dates, inclusive) for user-picked ranges.
    """
    now = datetime.now(timezone.utc)

    if period.startswith("custom:"):
        parts = period.split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid custom period {period!r}, expected custom:YYYY-MM-DD:YYYY-MM-DD")
        try:
            start_date = datetime.strptime(parts[1], "%Y-%m-%d").replace(tzinfo=_IST)
            end_date = datetime.strptime(parts[2], "%Y-%m-%d").replace(tzinfo=_IST)
        except ValueError:
            raise ValueError(f"Invalid custom period {period!r}, expected custom:YYYY-MM-DD:YYYY-MM-DD")
        range_start = start_date.astimezone(timezone.utc)
        range_end = (end_date + timedelta(days=1)).astimezone(timezone.utc)
        return range_start, min(range_end, now)

    if period not in _PERIODS:
        raise ValueError(f"Unknown period {period!r}, expected one of {_PERIODS} or custom:START:END")

    today_start = _ist_today_start(now)
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


def _actionable_and_resolved():
    """Scope to actionable, resolved tickets -- matches the reference
    frontline report's `closed_df` (excludes "No Action Taken" and anything
    still open), so FRT/FCR/CSAT rates aren't diluted by tickets that were
    never in scope for those SLAs in the first place."""
    return Ticket.actionable.is_(True) & (Ticket.canonical_status == "Resolved")


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


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def get_live_today(session: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    today_start = _ist_today_start(now)

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
    # MTTR (mean) alongside the median -- the reference frontline report's
    # TTR group tracks both; median stays the primary signal (see
    # _median_resolution_time_hours_expr) but the mean is worth surfacing too.
    mean_resolution_time_hours = await session.scalar(
        select(func.avg(_resolution_time_hours_expr())).where(
            Ticket.closed_at.between(period_start, period_end)
        )
    )
    resolved_over_48_hours_count = await session.scalar(
        select(func.count()).where(
            Ticket.closed_at.between(period_start, period_end),
            _resolution_time_hours_expr() > 48,
        )
    )

    # Resolution SLA Compliance per the reference frontline report's TTR
    # group: actionable tickets resolved within 3 days (72h), out of all
    # actionable tickets resolved in the period -- a 48h staleness flag
    # (above) is a different signal from this named SLA target.
    actionable_resolved = _actionable_and_resolved() & Ticket.closed_at.between(
        period_start, period_end
    )
    actionable_resolved_count = await session.scalar(
        select(func.count()).where(actionable_resolved)
    )
    actionable_resolved_within_72_hours_count = await session.scalar(
        select(func.count()).where(actionable_resolved, _resolution_time_hours_expr() <= 72)
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
        "mean_resolution_time_hours": (
            round(mean_resolution_time_hours, 1) if mean_resolution_time_hours is not None else None
        ),
        "tickets_resolved_over_48_hours_count": resolved_over_48_hours_count or 0,
        "sla_breach_percentage": _percentage(
            resolution_sla_breakdown.get("Completed late", 0), resolution_sla_evaluated_count
        ),
        "resolution_within_72_hours_percentage": _percentage(
            actionable_resolved_within_72_hours_count, actionable_resolved_count
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


async def get_source_distribution(session: AsyncSession, period: str) -> dict:
    """Channel mix (source_type) across all tickets in the period -- e.g.
    EMAIL vs CHAT vs Slack. General/org-wide, not scoped to any team or
    customer."""
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(Ticket.source_type, func.count())
        .where(Ticket.created_at.between(period_start, period_end))
        .group_by(Ticket.source_type)
        .order_by(func.count().desc())
    )
    by_source = {(source or "Unknown"): count for source, count in rows.all()}
    return {"by_source": by_source, "total_ticket_count": sum(by_source.values())}


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
    priority. Median rather than mean -- see _median_resolution_time_hours_expr.

    Also returns the resolved count behind each median -- with only 1-2
    tickets closed in a bucket (common for URGENT on a single-day period),
    the "median" is just those tickets' raw values, including any old
    backlog ticket that happened to close in that window. The count lets
    the frontend flag that instead of presenting it as a stable trend."""
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(Ticket.derived_priority, _median_resolution_time_hours_expr(), func.count())
        .where(Ticket.closed_at.between(period_start, period_end))
        .group_by(Ticket.derived_priority)
    )
    all_rows = rows.all()
    return {
        "median_resolution_time_hours_by_priority": {
            priority: round(hours, 1) for priority, hours, _ in all_rows if hours is not None
        },
        "resolved_ticket_count_by_priority": {
            priority: count for priority, hours, count in all_rows if hours is not None
        },
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


def _normalized_csat_percentage(rating_counts: dict) -> float | None:
    """(Happy*2 + Neutral) / (total*2) * 100, per the reference frontline
    report's CSAT formula -- assumes hs_last_csat_rating uses that report's
    0=Unhappy/1=Neutral/2=Happy scale, which HubSpot doesn't document and
    this portal hasn't confirmed (see get_csat's rating_scale_confirmed)."""
    happy = rating_counts.get("2", 0)
    neutral = rating_counts.get("1", 0)
    unhappy = rating_counts.get("0", 0)
    total = happy + neutral + unhappy
    if not total:
        return None
    return round((happy * 2 + neutral) / (total * 2) * 100, 1)


async def get_csat(session: AsyncSession, period: str) -> dict:
    """Raw rating distribution plus a normalized CSAT % -- HubSpot exposes
    hs_last_csat_rating as an opaque rollup with no documented scale, so the
    normalized % below assumes the reference report's 0/1/2 scale and should
    be confirmed with whoever set up the survey before treating it as ground
    truth (see rating_scale_confirmed).

    Also broken down by channel (source_type) -- verified live values in this
    portal are EMAIL/CHAT/Slack, not the generic "LIVE_CHAT" a HubSpot doc
    might suggest, so channel labels here reflect actual data, not a guess.
    """
    period_start, period_end = resolve_period(period)
    in_scope = (
        Ticket.created_at.between(period_start, period_end),
        _actionable_and_resolved(),
        Ticket.csat_rating.isnot(None),
    )
    rows = await session.execute(
        select(Ticket.csat_rating, func.count()).where(*in_scope).group_by(Ticket.csat_rating)
    )
    response_count_by_rating = dict(rows.all())

    channel_rows = await session.execute(
        select(Ticket.source_type, Ticket.csat_rating, func.count())
        .where(*in_scope)
        .group_by(Ticket.source_type, Ticket.csat_rating)
    )
    response_count_by_channel: dict[str, dict[str, int]] = {}
    for source_type, rating, count in channel_rows.all():
        channel = source_type or "Unknown"
        response_count_by_channel.setdefault(channel, {})[rating] = count

    return {
        "total_response_count": sum(response_count_by_rating.values()),
        "response_count_by_rating": response_count_by_rating,
        "response_count_by_rating_and_channel": response_count_by_channel,
        "normalized_csat_percentage": _normalized_csat_percentage(response_count_by_rating),
        "normalized_csat_percentage_by_channel": {
            channel: _normalized_csat_percentage(ratings)
            for channel, ratings in response_count_by_channel.items()
        },
        "rating_scale_confirmed": False,
    }


async def get_agent_kpis(session: AsyncSession, period: str) -> list[dict]:
    """Per-owner rollup -- volume, resolution speed, actionability, and the
    frontline/backline quality signals (FRT/FCR/backline escalation, backline
    resolution, engineering escalation) the reference report's "By Owner"
    sheets (frontline + backline) track per team member. This dashboard
    merges both reference sheets into one endpoint rather than keeping them
    separate, since they're both "per frontline owner" views."""
    period_start, period_end = resolve_period(period)
    in_period = Ticket.created_at.between(period_start, period_end)
    actionable_resolved = _actionable_and_resolved()

    # Unassigned tickets stay in their own group (owner_id/name = None) rather
    # than being dropped -- the reference report calls these out as a
    # dedicated "Unassigned" row precisely because they're a routing gap.
    async def _count_by_owner(*extra_filters) -> dict:
        rows = await session.execute(
            select(Ticket.owner_id, func.count())
            .where(in_period, *extra_filters)
            .group_by(Ticket.owner_id)
        )
        return dict(rows.all())

    async def _count_total(*extra_filters) -> int:
        return await session.scalar(select(func.count()).where(in_period, *extra_filters)) or 0

    base_rows = await session.execute(
        select(
            Ticket.owner_id,
            Ticket.owner_name,
            func.count(),
            _median_resolution_time_hours_expr(),
            func.avg(_resolution_time_hours_expr()),
        )
        .where(in_period)
        .group_by(Ticket.owner_id, Ticket.owner_name)
        .order_by(func.count().desc())
    )
    base = base_rows.all()

    actionable_by_owner = await _count_by_owner(Ticket.actionable.is_(True))
    closed_by_owner = await _count_by_owner(actionable_resolved)
    frt_evaluated_by_owner = await _count_by_owner(Ticket.time_to_first_agent_reply_hours.isnot(None))
    frt_on_time_by_owner = await _count_by_owner(
        Ticket.time_to_first_agent_reply_hours.isnot(None),
        Ticket.time_to_first_agent_reply_hours <= _FRT_SLA_HOURS,
    )
    frt_missed_by_owner = await _count_by_owner(
        Ticket.time_to_first_agent_reply_hours.isnot(None),
        Ticket.time_to_first_agent_reply_hours > _FRT_SLA_HOURS,
    )
    fcr_evaluated_by_owner = await _count_by_owner(Ticket.fcr.isnot(None))
    fcr_true_by_owner = await _count_by_owner(Ticket.fcr.is_(True))
    escalated_by_owner = await _count_by_owner(Ticket.backline_path.isnot(None))
    # "Backline Engineering" is resolution_taxonomy.json's bucket name for
    # final_resolution == "Issue Resolved Backline Engineering".
    backline_resolved_by_owner = await _count_by_owner(
        Ticket.resolution_bucket == "Backline Engineering"
    )

    # Escalation into the Engineering stage lives in the stage_timings JSONB
    # blob, not a plain column -- same pattern backline.py uses, aggregated
    # here in Python rather than via a JSONB path query.
    eng_stage_rows = await session.execute(
        select(Ticket.owner_id, Ticket.stage_timings).where(in_period)
    )
    eng_escalated_by_owner: dict[str, int] = {}
    for owner_id, stage_timings in eng_stage_rows.all():
        if (stage_timings.get("engineering") or {}).get("entered_at"):
            eng_escalated_by_owner[owner_id] = eng_escalated_by_owner.get(owner_id, 0) + 1

    def _owner_row(owner_id, owner_name, count, median_hours, mean_hours) -> dict:
        actionable_count = actionable_by_owner.get(owner_id, 0)
        closed_count = closed_by_owner.get(owner_id, 0)
        frt_on_time = frt_on_time_by_owner.get(owner_id, 0)
        frt_missed = frt_missed_by_owner.get(owner_id, 0)
        fcr_true = fcr_true_by_owner.get(owner_id, 0)
        return {
            "owner_id": owner_id or "unassigned",
            "owner_name": owner_name or "Unassigned",
            "ticket_count": count,
            "actionable_count": actionable_count,
            "non_actionable_count": count - actionable_count,
            "closed_count": closed_count,
            "still_open_count": actionable_count - closed_count,
            "closure_rate_percentage": _percentage(closed_count, actionable_count),
            "median_resolution_time_hours": round(median_hours, 1) if median_hours is not None else None,
            "mean_resolution_time_hours": round(mean_hours, 1) if mean_hours is not None else None,
            "first_response_sla_on_time_count": frt_on_time,
            "first_response_sla_missed_count": frt_missed,
            "first_response_sla_on_time_percentage": _percentage(
                frt_on_time, frt_evaluated_by_owner.get(owner_id, 0)
            ),
            "first_contact_resolution_true_count": fcr_true,
            "first_contact_resolution_percentage": _percentage(
                fcr_true, fcr_evaluated_by_owner.get(owner_id, 0)
            ),
            "backline_escalation_count": escalated_by_owner.get(owner_id, 0),
            "backline_escalation_percentage": _percentage(escalated_by_owner.get(owner_id, 0), count),
            "resolved_by_backline_engineering_count": backline_resolved_by_owner.get(owner_id, 0),
            "escalated_to_engineering_count": eng_escalated_by_owner.get(owner_id, 0),
        }

    rows = [_owner_row(owner_id, owner_name, count, median_hours, mean_hours) for owner_id, owner_name, count, median_hours, mean_hours in base]

    # Team-total row -- mirrors the reference reports' "TEAM TOTAL" row,
    # computed independently over every ticket in the period (assigned or
    # not) rather than summed from the per-owner rows, so its median/mean
    # are the true period-wide values, not an average of averages.
    team_total_count = await _count_total()
    team_median_hours = await session.scalar(
        select(_median_resolution_time_hours_expr()).where(in_period)
    )
    team_mean_hours = await session.scalar(
        select(func.avg(_resolution_time_hours_expr())).where(in_period)
    )
    team_row = _owner_row(
        "team_total", "Team Total", team_total_count, team_median_hours, team_mean_hours
    )
    # actionable/closed/etc. sub-counts above are per-owner-id and don't have
    # a "team_total" key, so total them across every group instead.
    team_row["actionable_count"] = sum(actionable_by_owner.values())
    team_row["non_actionable_count"] = team_total_count - team_row["actionable_count"]
    team_row["closed_count"] = sum(closed_by_owner.values())
    team_row["still_open_count"] = team_row["actionable_count"] - team_row["closed_count"]
    team_row["closure_rate_percentage"] = _percentage(
        team_row["closed_count"], team_row["actionable_count"]
    )
    team_row["first_response_sla_on_time_count"] = sum(frt_on_time_by_owner.values())
    team_row["first_response_sla_missed_count"] = sum(frt_missed_by_owner.values())
    team_row["first_response_sla_on_time_percentage"] = _percentage(
        team_row["first_response_sla_on_time_count"], sum(frt_evaluated_by_owner.values())
    )
    team_row["first_contact_resolution_true_count"] = sum(fcr_true_by_owner.values())
    team_row["first_contact_resolution_percentage"] = _percentage(
        team_row["first_contact_resolution_true_count"], sum(fcr_evaluated_by_owner.values())
    )
    team_row["backline_escalation_count"] = sum(escalated_by_owner.values())
    team_row["backline_escalation_percentage"] = _percentage(
        team_row["backline_escalation_count"], team_total_count
    )
    team_row["resolved_by_backline_engineering_count"] = sum(backline_resolved_by_owner.values())
    team_row["escalated_to_engineering_count"] = sum(eng_escalated_by_owner.values())

    return [*rows, team_row]


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
    return {
        "priority_inferred_percentage": _percentage(priority_inferred_count, total_count),
        "uncategorized_ticket_percentage": _percentage(uncategorized_count, total_count),
    }


async def get_sync_status(session: AsyncSession) -> dict:
    cursor_row = await session.get(SyncCursor, "hubspot_tickets")
    total_ticket_count = await session.scalar(select(func.count()).select_from(Ticket))
    return {
        "last_synced_at": _utc_iso(cursor_row.last_synced_at) if cursor_row else None,
        "total_ticket_count": total_ticket_count or 0,
    }
