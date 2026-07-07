"""Per-customer/account KPIs -- ticket volume and status breakdown.

Only ~4% of Support Pipeline tickets carry an identifiable customer/account
name (verified live 2026-07-06 -- most tickets here are individual
candidates doing assessments/hackathons, not B2B accounts), so every query
here explicitly separates "identified customer" tickets from the rest
rather than pretending full coverage.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.orm import CsatResponse, Ticket
from dashboard.utils import (
    _actionable_and_resolved,
    _csat_native_module_allowed,
    _median_resolution_time_hours_expr,
    _normalized_csat_percentage,
    _OPEN_STATUSES,
    _percentage,
    resolve_period,
)

# A status/stage breakdown for hundreds of one-ticket accounts isn't a
# chart, it's noise -- scope both KPIs to the same top-N customers by volume.
_TOP_N_CUSTOMERS = 15


async def _top_customer_names(session: AsyncSession, in_period, limit: int) -> list[str]:
    rows = await session.execute(
        select(Ticket.customer_name, func.count())
        .where(in_period, Ticket.customer_name.isnot(None))
        .group_by(Ticket.customer_name)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [name for name, _ in rows.all()]


async def get_customer_ticket_volume(session: AsyncSession, period: str) -> dict:
    """Ticket count per identified customer, plus how much volume has no
    identified customer at all -- that split is the headline here, not an
    afterthought, given how low identification coverage is."""
    period_start, period_end = resolve_period(period)
    in_period = Ticket.created_at.between(period_start, period_end)

    rows = await session.execute(
        select(Ticket.customer_name, func.count())
        .where(in_period, Ticket.customer_name.isnot(None))
        .group_by(Ticket.customer_name)
        .order_by(func.count().desc())
    )
    identified = [{"customer_name": name, "ticket_count": count} for name, count in rows.all()]

    no_account_count = await session.scalar(
        select(func.count()).where(in_period, Ticket.customer_name.is_(None))
    )
    identified_total = sum(r["ticket_count"] for r in identified)

    return {
        "top_customers": identified[:_TOP_N_CUSTOMERS],
        "other_identified_customer_count": max(0, len(identified) - _TOP_N_CUSTOMERS),
        "other_identified_ticket_count": identified_total
        - sum(r["ticket_count"] for r in identified[:_TOP_N_CUSTOMERS]),
        "identified_customer_count": len(identified),
        "identified_ticket_count": identified_total,
        "no_account_ticket_count": no_account_count or 0,
        "total_ticket_count": identified_total + (no_account_count or 0),
    }


async def get_customer_status_breakdown(session: AsyncSession, period: str) -> dict:
    """Per top-N customer: counts by canonical_status (few categories, for
    the stacked-bar chart) and by the more granular stage_label (for the
    drill-down table) -- same status/stage split the rest of this dashboard
    already uses (see /distribution/status vs /distribution/stage)."""
    period_start, period_end = resolve_period(period)
    in_period = Ticket.created_at.between(period_start, period_end)

    top_customers = await _top_customer_names(session, in_period, _TOP_N_CUSTOMERS)
    if not top_customers:
        return {"customers": []}

    scoped = in_period, Ticket.customer_name.in_(top_customers)

    status_rows = await session.execute(
        select(Ticket.customer_name, Ticket.canonical_status, func.count())
        .where(*scoped)
        .group_by(Ticket.customer_name, Ticket.canonical_status)
    )
    stage_rows = await session.execute(
        select(Ticket.customer_name, Ticket.stage_label, func.count())
        .where(*scoped)
        .group_by(Ticket.customer_name, Ticket.stage_label)
    )

    by_customer = {
        name: {"customer_name": name, "status_counts": {}, "stage_counts": {}}
        for name in top_customers
    }
    for name, status, count in status_rows.all():
        by_customer[name]["status_counts"][status] = count
    for name, stage, count in stage_rows.all():
        by_customer[name]["stage_counts"][stage] = count

    # Preserve volume-descending order -- the frontend renders top-to-bottom.
    return {"customers": [by_customer[name] for name in top_customers]}


async def get_customer_details(session: AsyncSession, period: str) -> dict:
    """Per top-N customer: who resolves their tickets (resolution_bucket),
    priority mix, SLA compliance, resolution/first-response speed, and
    escalation rate -- all period-scoped -- plus current open backlog, which
    is deliberately NOT period-scoped (backlog means "right now", same
    convention the live-status panel elsewhere on this dashboard uses)."""
    period_start, period_end = resolve_period(period)
    in_period = Ticket.created_at.between(period_start, period_end)

    top_customers = await _top_customer_names(session, in_period, _TOP_N_CUSTOMERS)
    if not top_customers:
        return {"customers": []}

    scoped = in_period, Ticket.customer_name.in_(top_customers)

    resolver_rows = await session.execute(
        select(Ticket.customer_name, Ticket.resolution_bucket, func.count())
        .where(*scoped)
        .group_by(Ticket.customer_name, Ticket.resolution_bucket)
    )
    priority_rows = await session.execute(
        select(Ticket.customer_name, Ticket.derived_priority, func.count())
        .where(*scoped)
        .group_by(Ticket.customer_name, Ticket.derived_priority)
    )
    sla_rows = await session.execute(
        select(
            Ticket.customer_name,
            func.count().filter(Ticket.sla_met.is_(True)),
            func.count().filter(Ticket.sla_met.is_(False)),
        )
        .where(*scoped)
        .group_by(Ticket.customer_name)
    )
    speed_rows = await session.execute(
        select(
            Ticket.customer_name,
            _median_resolution_time_hours_expr(),
            func.percentile_cont(0.5).within_group(Ticket.time_to_first_agent_reply_hours),
        )
        .where(*scoped, _actionable_and_resolved())
        .group_by(Ticket.customer_name)
    )
    escalation_rows = await session.execute(
        select(
            Ticket.customer_name,
            func.count().filter(Ticket.backline_path.isnot(None)),
            func.count(),
        )
        .where(*scoped)
        .group_by(Ticket.customer_name)
    )
    # Backlog is "right now" -- deliberately not scoped to `in_period`.
    backlog_rows = await session.execute(
        select(Ticket.customer_name, func.count())
        .where(Ticket.customer_name.in_(top_customers), Ticket.canonical_status.in_(_OPEN_STATUSES))
        .group_by(Ticket.customer_name)
    )
    # CSAT responses matched to one of this customer's tickets (see get_csat's
    # unmatched_to_ticket_count caveat -- unmatched responses can't be
    # attributed to a customer at all).
    csat_rows = await session.execute(
        select(Ticket.customer_name, CsatResponse.rating, func.count())
        .join(CsatResponse, CsatResponse.ticket_id == Ticket.ticket_id)
        .where(*scoped, _csat_native_module_allowed())
        .group_by(Ticket.customer_name, CsatResponse.rating)
    )

    by_customer = {
        name: {
            "customer_name": name,
            "resolution_bucket_counts": {},
            "priority_counts": {},
            "sla_met_count": 0,
            "sla_breached_count": 0,
            "median_resolution_time_hours": None,
            "median_first_response_hours": None,
            "escalated_count": 0,
            "escalated_percentage": None,
            "open_backlog_count": 0,
            "normalized_csat_percentage": None,
        }
        for name in top_customers
    }
    csat_rating_counts: dict[str, dict[int, int]] = {name: {} for name in top_customers}
    for name, bucket, count in resolver_rows.all():
        by_customer[name]["resolution_bucket_counts"][bucket] = count
    for name, priority, count in priority_rows.all():
        by_customer[name]["priority_counts"][priority] = count
    for name, met_count, breached_count in sla_rows.all():
        by_customer[name]["sla_met_count"] = met_count
        by_customer[name]["sla_breached_count"] = breached_count
    for name, median_resolution, median_first_response in speed_rows.all():
        by_customer[name]["median_resolution_time_hours"] = (
            round(median_resolution, 1) if median_resolution is not None else None
        )
        by_customer[name]["median_first_response_hours"] = (
            round(median_first_response, 1) if median_first_response is not None else None
        )
    for name, escalated_count, total_count in escalation_rows.all():
        by_customer[name]["escalated_count"] = escalated_count
        by_customer[name]["escalated_percentage"] = _percentage(escalated_count, total_count)
    for name, count in backlog_rows.all():
        by_customer[name]["open_backlog_count"] = count
    for name, rating, count in csat_rows.all():
        csat_rating_counts[name][rating] = count
    for name in top_customers:
        by_customer[name]["normalized_csat_percentage"] = _normalized_csat_percentage(
            csat_rating_counts[name]
        )

    return {"customers": [by_customer[name] for name in top_customers]}
