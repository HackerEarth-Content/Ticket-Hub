"""Backline-team KPIs -- AE performance, escalations, and stage timing.

Split out of utils.py (which keeps the shared helpers and core/overview
KPIs) purely by domain; nothing here is architecturally special.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.orm import Ticket
from dashboard.utils import _parse_iso, _percentage, resolve_period
from hubspot_pipeline.stage_timing import STAGE_TIMING_STAGES

_QA_PLATFORM_STAGE_KEY = "qa_platform"
_ENGINEERING_STAGE_KEY = "engineering"

# Every stage a backline-originated ticket can escalate into, checked in this
# order so a ticket that hit more than one reports its furthest/first-entered
# stop. Support/Content are frontline-side team routing, not backline itself,
# but a backline ticket that gets kicked to one of them is still an
# escalation past backline the same way Engineering/QA-Platform are.
_ESCALATION_STAGE_LABELS = {
    _ENGINEERING_STAGE_KEY: "Engineering",
    _QA_PLATFORM_STAGE_KEY: "QA/Platform",
    "support": "Support",
    "content": "Content",
}

# Anomaly/uncategorized drill-down lists are capped so a bad data period
# can't return an unbounded payload -- callers see `truncated` when it bites.
_DRILLDOWN_LIMIT = 100


def _stage_hours(stage_timings: dict, stage_key: str | None) -> float | None:
    if not stage_key:
        return None
    return (stage_timings.get(stage_key) or {}).get("cumulative_hours")


def _numeric_stats(values: list[float]) -> dict:
    values = [v for v in values if v is not None]
    if not values:
        return {"average": None, "median": None, "minimum": None, "maximum": None}
    return {
        "average": round(sum(values) / len(values), 1),
        "median": round(statistics.median(values), 1),
        "minimum": round(min(values), 1),
        "maximum": round(max(values), 1),
    }


async def get_backline_ae_performance(session: AsyncSession, period: str) -> dict:
    """Per-backline-AE workload and speed, split by which door the ticket
    came through (Bug Bounty vs Frontline Escalation) -- mirrors the
    reference report's AE Performance sheet, but AEs come from live
    `backline_engineer` data instead of a hardcoded name list."""
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(
            Ticket.backline_engineer,
            Ticket.backline_path,
            Ticket.stage_timings,
            Ticket.derived_priority,
            Ticket.owner_name,
            Ticket.categories,
            Ticket.created_at,
            Ticket.closed_at,
            Ticket.final_resolution,
        ).where(
            Ticket.created_at.between(period_start, period_end),
            Ticket.backline_engineer.isnot(None),
        )
    )

    by_ae: dict[str, list] = {}
    for row in rows.all():
        by_ae.setdefault(row.backline_engineer, []).append(row)

    ae_performance = []
    for ae, tickets in sorted(by_ae.items()):
        path_counts: dict[str, int] = {}
        ae_stage_hours: list[float] = []
        ticket_ttr_hours: list[float] = []
        # Also broken out per path (Bug Bounty vs Frontline Escalation) --
        # the reference report's AE Performance sheet gives each path its own
        # avg/min/max section since the two paths run through different
        # stages with very different SLAs.
        ae_stage_hours_by_path: dict[str, list[float]] = {}
        ticket_ttr_hours_by_path: dict[str, list[float]] = {}
        escalated_to_engineering = 0
        high_priority = 0
        resolved_count = 0
        owners: set[str] = set()
        categories: set[str] = set()

        for t in tickets:
            if t.backline_path:
                path_counts[t.backline_path] = path_counts.get(t.backline_path, 0) + 1
            stage_key = "backline_ae" if t.backline_path == "Bug Bounty" else "be_ae"
            hours = _stage_hours(t.stage_timings, stage_key)
            if hours is not None:
                ae_stage_hours.append(hours)
                if t.backline_path:
                    ae_stage_hours_by_path.setdefault(t.backline_path, []).append(hours)
            if t.closed_at and t.created_at:
                ttr = (t.closed_at - t.created_at).total_seconds() / 3600
                ticket_ttr_hours.append(ttr)
                if t.backline_path:
                    ticket_ttr_hours_by_path.setdefault(t.backline_path, []).append(ttr)
            if (t.stage_timings.get(_ENGINEERING_STAGE_KEY) or {}).get("entered_at"):
                escalated_to_engineering += 1
            if t.derived_priority in ("HIGH", "URGENT"):
                high_priority += 1
            if t.final_resolution and t.final_resolution.startswith("Issue Resolved"):
                resolved_count += 1
            if t.owner_name:
                owners.add(t.owner_name)
            categories.update(t.categories)

        ae_performance.append({
            "backline_engineer": ae,
            "tickets_handled_count": len(tickets),
            "all_resolved": resolved_count == len(tickets),
            "path_breakdown": path_counts,
            "ae_stage_time_hours": _numeric_stats(ae_stage_hours),
            "ae_stage_time_hours_by_path": {
                path: _numeric_stats(hours) for path, hours in ae_stage_hours_by_path.items()
            },
            "ticket_resolution_time_hours": _numeric_stats(ticket_ttr_hours),
            "ticket_resolution_time_hours_by_path": {
                path: _numeric_stats(hours) for path, hours in ticket_ttr_hours_by_path.items()
            },
            "escalated_to_engineering_count": escalated_to_engineering,
            "high_priority_ticket_count": high_priority,
            "frontline_owners_supported_count": len(owners),
            "categories_handled_count": len(categories),
        })

    return {"ae_performance": ae_performance}


async def get_backline_escalations(session: AsyncSession, period: str) -> dict:
    """Tickets that escalated past backline into QA/Platform or Engineering --
    the reference report's Escalations sheet."""
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(
            Ticket.ticket_id,
            Ticket.subject,
            Ticket.owner_name,
            Ticket.backline_engineer,
            Ticket.canonical_status,
            Ticket.final_resolution,
            Ticket.stage_timings,
            Ticket.jira_link,
        ).where(
            Ticket.created_at.between(period_start, period_end),
            Ticket.backline_path.isnot(None),
        )
    )

    now = datetime.now(timezone.utc)
    escalations = []
    for row in rows.all():
        escalation_path, timing = None, None
        for stage_key, label in _ESCALATION_STAGE_LABELS.items():
            t = row.stage_timings.get(stage_key) or {}
            if t.get("entered_at"):
                escalation_path, timing = label, t
                break
        if escalation_path is None:
            continue

        entered_at = _parse_iso(timing.get("entered_at"))
        live_wait_hours = None
        if entered_at and not timing.get("exited_at"):
            live_wait_hours = round((now - entered_at).total_seconds() / 3600, 1)

        escalations.append({
            "ticket_id": row.ticket_id,
            "subject": row.subject,
            "owner_name": row.owner_name,
            "backline_engineer": row.backline_engineer,
            "escalation_path": escalation_path,
            "canonical_status": row.canonical_status,
            "final_resolution": row.final_resolution,
            "entered_at": timing.get("entered_at"),
            "exited_at": timing.get("exited_at"),
            "cumulative_time_hours": timing.get("cumulative_hours"),
            "live_wait_time_hours": live_wait_hours,
            "jira_link": row.jira_link,
        })

    truncated = len(escalations) > _DRILLDOWN_LIMIT
    return {
        "escalation_count": len(escalations),
        "escalations": escalations[:_DRILLDOWN_LIMIT],
        "truncated": truncated,
    }


async def get_backline_stage_timing(session: AsyncSession, period: str) -> dict:
    """Aggregate entered/exited/still-queued/live-wait per backline stage --
    the reference report's "P0 STAGE A/B" sections, generalized to all 4
    tracked stages instead of just 2."""
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(Ticket.stage_timings).where(Ticket.created_at.between(period_start, period_end))
    )
    all_timings = [r[0] for r in rows.all()]
    now = datetime.now(timezone.utc)

    stage_timing = {}
    for stage_key, stage in STAGE_TIMING_STAGES.items():
        entered_count = 0
        exited_count = 0
        cumulative_hours: list[float] = []
        live_wait_hours: list[float] = []

        for timings in all_timings:
            t = timings.get(stage_key) or {}
            entered_at = _parse_iso(t.get("entered_at"))
            if not entered_at:
                continue
            entered_count += 1
            if t.get("exited_at"):
                exited_count += 1
            if t.get("cumulative_hours") is not None:
                cumulative_hours.append(t["cumulative_hours"])
            else:
                live_wait_hours.append((now - entered_at).total_seconds() / 3600)

        stage_timing[stage_key] = {
            "label": stage["label"],
            "entered_count": entered_count,
            "exited_count": exited_count,
            "still_in_queue_count": entered_count - exited_count,
            "average_cumulative_time_hours": (
                round(sum(cumulative_hours) / len(cumulative_hours), 1) if cumulative_hours else None
            ),
            "minimum_cumulative_time_hours": (
                round(min(cumulative_hours), 1) if cumulative_hours else None
            ),
            "maximum_cumulative_time_hours": (
                round(max(cumulative_hours), 1) if cumulative_hours else None
            ),
            "max_live_wait_time_hours": round(max(live_wait_hours), 1) if live_wait_hours else None,
        }

    return {"stage_timing": stage_timing}


async def get_backline_overview(session: AsyncSession, period: str) -> dict:
    """Overall ticket metrics scoped like the reference backline report's
    Summary sheet: total/actionable/closed/still-open across every ticket in
    the period, the 3 backline-specific call-outs (resolved-by-backline,
    escalated-to-engineering, FCR) as a % of actionable tickets, and the raw
    final_resolution breakdown as a % of closed tickets."""
    period_start, period_end = resolve_period(period)
    in_period = Ticket.created_at.between(period_start, period_end)
    actionable = Ticket.actionable.is_(True)
    closed = Ticket.canonical_status == "Resolved"

    async def _count(*extra_filters) -> int:
        return await session.scalar(select(func.count()).where(in_period, *extra_filters)) or 0

    total_count = await _count()
    actionable_count = await _count(actionable)
    closed_count = await _count(actionable, closed)
    still_open_count = actionable_count - closed_count
    # "Backline Engineering" is resolution_taxonomy.json's bucket name for
    # final_resolution == "Issue Resolved Backline Engineering".
    resolved_by_backline_count = await _count(actionable, Ticket.resolution_bucket == "Backline Engineering")
    fcr_true_count = await _count(actionable, Ticket.fcr.is_(True))

    # Engineering-stage escalation lives in the stage_timings JSONB blob, so
    # it's aggregated in Python rather than via a JSONB path query.
    stage_timing_rows = await session.execute(
        select(Ticket.stage_timings).where(in_period, actionable)
    )
    escalated_to_engineering_count = sum(
        1
        for (stage_timings,) in stage_timing_rows.all()
        if (stage_timings.get(_ENGINEERING_STAGE_KEY) or {}).get("entered_at")
    )

    final_resolution_rows = await session.execute(
        select(Ticket.final_resolution, func.count())
        .where(in_period, actionable, closed)
        .group_by(Ticket.final_resolution)
        .order_by(func.count().desc())
    )
    final_resolution_breakdown = {
        (final_resolution or "No Resolution (open)"): count
        for final_resolution, count in final_resolution_rows.all()
    }

    return {
        "total_ticket_count": total_count,
        "actionable_ticket_count": actionable_count,
        "actionable_percentage": _percentage(actionable_count, total_count),
        "closed_ticket_count": closed_count,
        "closed_percentage_of_actionable": _percentage(closed_count, actionable_count),
        "still_open_ticket_count": still_open_count,
        "resolved_by_backline_count": resolved_by_backline_count,
        "resolved_by_backline_percentage_of_actionable": _percentage(
            resolved_by_backline_count, actionable_count
        ),
        "escalated_to_engineering_count": escalated_to_engineering_count,
        "escalated_to_engineering_percentage_of_actionable": _percentage(
            escalated_to_engineering_count, actionable_count
        ),
        "fcr_true_count": fcr_true_count,
        "fcr_percentage_of_actionable": _percentage(fcr_true_count, actionable_count),
        "final_resolution_breakdown": final_resolution_breakdown,
        "final_resolution_percentage_of_closed": {
            label: _percentage(count, closed_count)
            for label, count in final_resolution_breakdown.items()
        },
    }
