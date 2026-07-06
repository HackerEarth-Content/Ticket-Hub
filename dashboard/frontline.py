"""Frontline-team KPIs -- FRT, FCR, resolution ownership, data anomalies.

Split out of utils.py (which keeps the shared helpers and core/overview
KPIs) purely by domain; nothing here is architecturally special.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.orm import Ticket
from dashboard.utils import (
    _actionable_and_resolved,
    _FRT_SLA_HOURS,
    _OPEN_STATUSES,
    _percentage,
    _utc_iso,
    resolve_period,
)
from hubspot_pipeline.resolution_map import UNRESOLVED_BUCKET

# A ticket counts as "resolved within a day" for the FCR-quality metric.
_FCR_FAST_RESOLUTION_HOURS = 24

# Anomaly/uncategorized drill-down lists are capped so a bad data period
# can't return an unbounded payload -- callers see `truncated` when it bites.
_DRILLDOWN_LIMIT = 100


async def get_frontline_frt(session: AsyncSession, period: str) -> dict:
    """First Response Time against the 30-minute SLA -- on-time/missed for
    tickets that got a reply, plus "still waiting past SLA" for ones that
    haven't. Overall and per-owner, matching the reference frontline report's
    flagship FRT metric block."""
    period_start, period_end = resolve_period(period)
    in_period = Ticket.created_at.between(period_start, period_end)
    # On-time/missed is scored against actionable, resolved tickets only --
    # matches the reference report's closed_df scope, so a "No Action Taken"
    # or still-open ticket can't skew the rate.
    actionable_resolved = _actionable_and_resolved()
    replied = Ticket.time_to_first_agent_reply_hours.isnot(None)
    on_time = Ticket.time_to_first_agent_reply_hours <= _FRT_SLA_HOURS
    still_waiting_overdue = (
        Ticket.actionable.is_(True)
        & Ticket.time_to_first_agent_reply_hours.is_(None)
        & Ticket.canonical_status.in_(_OPEN_STATUSES)
        & (func.extract("epoch", func.now() - Ticket.created_at) / 3600 > _FRT_SLA_HOURS)
    )

    async def _counts(*extra_filters):
        return await session.scalar(select(func.count()).where(in_period, *extra_filters))

    on_time_count = await _counts(actionable_resolved, replied, on_time)
    late_count = await _counts(actionable_resolved, replied, ~on_time)
    overdue_count = await _counts(still_waiting_overdue)
    evaluated = (on_time_count or 0) + (late_count or 0)

    by_owner_rows = await session.execute(
        select(
            Ticket.owner_id,
            Ticket.owner_name,
            func.count().filter(actionable_resolved, replied, on_time),
            func.count().filter(actionable_resolved, replied, ~on_time),
            func.count().filter(still_waiting_overdue),
        )
        .where(in_period)
        .group_by(Ticket.owner_id, Ticket.owner_name)
    )
    by_owner = [
        {
            "owner_id": owner_id or "unassigned",
            "owner_name": owner_name or "Unassigned",
            "on_time_count": on_time_n,
            "missed_count": late_n,
            "awaiting_reply_overdue_count": overdue_n,
            "on_time_percentage": _percentage(on_time_n, on_time_n + late_n),
        }
        for owner_id, owner_name, on_time_n, late_n, overdue_n in by_owner_rows.all()
    ]

    return {
        "sla_threshold_minutes": int(_FRT_SLA_HOURS * 60),
        "on_time_count": on_time_count or 0,
        "missed_count": late_count or 0,
        "awaiting_reply_overdue_count": overdue_count or 0,
        "on_time_percentage": _percentage(on_time_count, evaluated),
        "by_owner": by_owner,
    }


async def get_frontline_fcr(session: AsyncSession, period: str) -> dict:
    """First Contact Resolution -- overall rate and the "resolved fast"
    quality signal (FCR tickets closed within 24h)."""
    period_start, period_end = resolve_period(period)
    in_period = Ticket.created_at.between(period_start, period_end)
    # Scored against actionable, resolved tickets only -- matches the
    # reference report's closed_df scope.
    actionable_resolved = _actionable_and_resolved()
    resolved_within_a_day = (
        Ticket.closed_at.isnot(None)
        & (func.extract("epoch", Ticket.closed_at - Ticket.created_at) / 3600 <= _FCR_FAST_RESOLUTION_HOURS)
    )

    fcr_true = await session.scalar(
        select(func.count()).where(in_period, actionable_resolved, Ticket.fcr.is_(True))
    )
    fcr_false = await session.scalar(
        select(func.count()).where(in_period, actionable_resolved, Ticket.fcr.is_(False))
    )
    fcr_fast = await session.scalar(
        select(func.count()).where(
            in_period, actionable_resolved, Ticket.fcr.is_(True), resolved_within_a_day
        )
    )
    evaluated = (fcr_true or 0) + (fcr_false or 0)

    return {
        "fcr_true_count": fcr_true or 0,
        "fcr_false_count": fcr_false or 0,
        "first_contact_resolution_percentage": _percentage(fcr_true, evaluated),
        "fcr_resolved_within_24_hours_count": fcr_fast or 0,
        "fcr_resolved_within_24_hours_percentage": _percentage(fcr_fast, fcr_true),
    }


async def get_frontline_resolution_ownership(session: AsyncSession, period: str) -> dict:
    """Who actually resolves tickets -- Support/Engineering/Backline/
    Automation/etc, off the final_resolution -> bucket taxonomy. Reference
    report's Resolution Ownership / Dependency Distribution block."""
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(Ticket.resolution_bucket, func.count())
        .where(Ticket.created_at.between(period_start, period_end))
        .group_by(Ticket.resolution_bucket)
    )
    breakdown = dict(rows.all())
    total = sum(breakdown.values())
    resolved_total = total - breakdown.get(UNRESOLVED_BUCKET, 0)

    return {
        "ticket_count_by_resolution_bucket": breakdown,
        "percentage_of_resolved_by_bucket": {
            bucket: _percentage(count, resolved_total)
            for bucket, count in breakdown.items()
            if bucket != UNRESOLVED_BUCKET
        },
    }


_ANOMALY_DEFINITIONS: dict[str, tuple] = {
    "resolution_without_resolved_status": (
        "Final Resolution set but ticket not Resolved",
        (Ticket.final_resolution.isnot(None), Ticket.canonical_status != "Resolved"),
    ),
    "resolved_without_resolution": (
        "Resolved but no Final Resolution",
        (Ticket.canonical_status == "Resolved", Ticket.final_resolution.is_(None)),
    ),
    "escalated_without_backline_engineer": (
        "Escalated to backline but no Backline Engineer assigned",
        (Ticket.backline_path.isnot(None), Ticket.backline_engineer.is_(None)),
    ),
    "non_actionable_category_but_resolved": (
        "Non-Actionable category but a real resolution was recorded",
        (
            Ticket.module == "Non-Actionable",
            Ticket.resolution_bucket.notin_([UNRESOLVED_BUCKET, "Non-Actionable"]),
        ),
    ),
    "actionable_category_marked_no_action": (
        "Actionable category but Final Resolution is No Action Taken",
        (
            Ticket.module.notin_(["Non-Actionable", "Uncategorized"]),
            Ticket.resolution_bucket == "Non-Actionable",
        ),
    ),
    "resolved_actionable_without_owner": (
        "Resolved, actionable ticket with no Ticket Owner",
        (Ticket.canonical_status == "Resolved", Ticket.actionable.is_(True), Ticket.owner_id.is_(None)),
    ),
}
# Duplicate-ticket-ID isn't checkable here: ticket_id is the table's primary
# key, so Postgres already makes that class of anomaly impossible.


async def get_data_anomalies(session: AsyncSession, period: str) -> dict:
    period_start, period_end = resolve_period(period)
    in_period = Ticket.created_at.between(period_start, period_end)

    anomalies_by_type = {}
    counts = {}
    for key, (label, filters) in _ANOMALY_DEFINITIONS.items():
        total = await session.scalar(select(func.count()).where(in_period, *filters))
        rows = await session.execute(
            select(
                Ticket.ticket_id,
                Ticket.subject,
                Ticket.canonical_status,
                Ticket.module,
                Ticket.final_resolution,
                Ticket.owner_name,
            )
            .where(in_period, *filters)
            .order_by(Ticket.created_at.desc())
            .limit(_DRILLDOWN_LIMIT)
        )
        tickets = [
            {
                "ticket_id": r.ticket_id,
                "subject": r.subject,
                "canonical_status": r.canonical_status,
                "module": r.module,
                "final_resolution": r.final_resolution,
                "owner_name": r.owner_name,
            }
            for r in rows.all()
        ]
        counts[key] = total or 0
        anomalies_by_type[key] = {
            "label": label,
            "count": total or 0,
            "tickets": tickets,
            "truncated": (total or 0) > _DRILLDOWN_LIMIT,
        }

    return {
        "anomaly_count_by_type": counts,
        "total_anomaly_count": sum(counts.values()),
        "anomalies_by_type": anomalies_by_type,
    }


async def get_uncategorized_tickets(session: AsyncSession, period: str) -> dict:
    """Drill-down list behind the data-quality `uncategorized_ticket_percentage`
    number -- resolved tickets that never got a category."""
    period_start, period_end = resolve_period(period)
    filters = (
        Ticket.created_at.between(period_start, period_end),
        Ticket.module == "Uncategorized",
        Ticket.canonical_status == "Resolved",
    )
    total = await session.scalar(select(func.count()).where(*filters))
    rows = await session.execute(
        select(Ticket.ticket_id, Ticket.subject, Ticket.owner_name, Ticket.final_resolution, Ticket.created_at)
        .where(*filters)
        .order_by(Ticket.created_at.desc())
        .limit(_DRILLDOWN_LIMIT)
    )
    tickets = [
        {
            "ticket_id": r.ticket_id,
            "subject": r.subject,
            "owner_name": r.owner_name,
            "final_resolution": r.final_resolution,
            "created_at": _utc_iso(r.created_at) if r.created_at else None,
        }
        for r in rows.all()
    ]
    return {
        "uncategorized_count": total or 0,
        "tickets": tickets,
        "truncated": (total or 0) > _DRILLDOWN_LIMIT,
    }
