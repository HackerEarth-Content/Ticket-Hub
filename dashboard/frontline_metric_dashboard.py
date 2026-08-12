"""Live data behind the "Frontline Metric Dashboard" card -- mirrors the
team's manually-tracked quarterly Excel of the same name, but every number
here is queried fresh off Ticket/CsatResponse/NpsResponse for the exact
month requested. Only the target thresholds (METRIC_GROUPS below) are
static config -- those are business goals, not observed data, same
convention as utils._FRT_SLA_HOURS.

Quarters are 3-month blocks on a fixed Feb/May/Aug/Nov cycle (FMA/MJJ/ASO/
NDJ -- NDJ crosses a calendar year boundary). The card always shows the
window [2 quarters ago, 1 quarter ago, this quarter, next quarter] computed
off "now", so it slides forward on its own as time passes instead of being
pinned to whichever quarter names were current when this was written.
"""

from __future__ import annotations

import asyncio
import calendar
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import db_manager
from core.orm import CsatResponse, DashboardLink, NpsResponse, Ticket
from dashboard import frontline, utils
from dashboard.utils import (
    _actionable_and_resolved,
    _FRT_ALWAYS_ON_TIME,
    _FRT_SLA_HOURS,
    _median_resolution_time_hours_expr,
    _normalized_csat_percentage,
    _percentage,
    _resolution_time_hours_expr,
    resolve_period,
)

_IST = ZoneInfo("Asia/Kolkata")

_QUARTER_START_MONTHS = (2, 5, 8, 11)
_QUARTER_CODES = ("FMA", "MJJ", "ASO", "NDJ")


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = month - 1 + delta
    return year + idx // 12, idx % 12 + 1


def _current_quarter_start(now_ist: datetime) -> tuple[int, int]:
    candidates = [m for m in _QUARTER_START_MONTHS if m <= now_ist.month]
    if candidates:
        return now_ist.year, max(candidates)
    return now_ist.year - 1, 11  # January belongs to the NDJ that started last November


def _quarter_window(now: datetime) -> list[dict]:
    """The 4 quarters to show -- the 2 just completed, the current one, and
    the next -- always relative to `now`."""
    now_ist = now.astimezone(_IST)
    cur_year, cur_month = _current_quarter_start(now_ist)
    cur_idx = _QUARTER_START_MONTHS.index(cur_month)

    quarters = []
    for offset in (-2, -1, 0, 1):
        year, month = _add_months(cur_year, cur_month, offset * 3)
        code = _QUARTER_CODES[(cur_idx + offset) % 4]
        months = []
        y, m = year, month
        for _ in range(3):
            months.append((y, m))
            y, m = _add_months(y, m, 1)
        start_year, end_year = months[0][0], months[-1][0]
        label = (
            f"{code} {start_year}"
            if start_year == end_year
            else f"{code} {start_year}-{end_year % 100:02d}"
        )
        quarters.append({"code": code, "label": label, "months": months})
    return quarters


def _period_for_month(year: int, month: int) -> str:
    last_day = calendar.monthrange(year, month)[1]
    return f"custom:{year:04d}-{month:02d}-01:{year:04d}-{month:02d}-{last_day:02d}"


def _period_for_quarter(months: list[tuple[int, int]]) -> str:
    start_year, start_month = months[0]
    end_year, end_month = months[-1]
    last_day = calendar.monthrange(end_year, end_month)[1]
    return f"custom:{start_year:04d}-{start_month:02d}-01:{end_year:04d}-{end_month:02d}-{last_day:02d}"


async def _get_csat_overall(session: AsyncSession, start: datetime, end: datetime) -> dict:
    """Same normalized-CSAT formula as utils.get_csat, but over every survey
    response in the window regardless of whether it matched a ticket -- the
    sheet's "includes feedback for tickets that are not yet raised" row."""
    rows = await session.execute(
        select(CsatResponse.rating, func.count())
        .where(CsatResponse.submitted_at.between(start, end))
        .group_by(CsatResponse.rating)
    )
    response_count_by_rating = dict(rows.all())
    return {
        "response_count_by_rating": response_count_by_rating,
        "normalized_csat_percentage": _normalized_csat_percentage(response_count_by_rating),
    }


async def _get_nps_mean_score(session: AsyncSession, start: datetime, end: datetime) -> float | None:
    mean_score = await session.scalar(
        select(func.avg(NpsResponse.score)).where(
            NpsResponse.created_at.between(start, end),
            NpsResponse.excluded_from_calculations.is_(False),
        )
    )
    return round(mean_score, 2) if mean_score is not None else None


async def _ttr_block(session: AsyncSession, start: datetime, end: datetime, *filters) -> dict:
    """Count / <=3-day count / mean resolution time for tickets closed in
    the window and matching `filters` -- shared shape behind the sheet's
    per-resolving-team TTR blocks (Engineering, Backline incl/excl bug bounty)."""
    resolved_in_window = Ticket.closed_at.between(start, end)
    total = await session.scalar(select(func.count()).where(resolved_in_window, *filters))
    within_3_days = await session.scalar(
        select(func.count()).where(resolved_in_window, *filters, _resolution_time_hours_expr() <= 72)
    )
    mean_hours = await session.scalar(
        select(func.avg(_resolution_time_hours_expr())).where(resolved_in_window, *filters)
    )
    return {
        "count": total or 0,
        "within_3_days_count": within_3_days or 0,
        "within_3_days_percentage": _percentage(within_3_days, total),
        "mean_hours": round(mean_hours, 1) if mean_hours is not None else None,
        "mean_days": round(mean_hours / 24, 2) if mean_hours is not None else None,
    }


async def _period_metrics(session: AsyncSession, period: str) -> dict:
    period_start, period_end = resolve_period(period)

    fcr = await frontline.get_frontline_fcr(session, period)
    ownership = await frontline.get_frontline_resolution_ownership(session, period)
    csat_raised = await utils.get_csat(session, period)
    csat_overall = await _get_csat_overall(session, period_start, period_end)
    nps = await utils.get_nps(session, period)
    nps_mean = await _get_nps_mean_score(session, period_start, period_end)
    engineering = await _ttr_block(session, period_start, period_end, Ticket.resolution_bucket == "Engineering")
    backline = await _ttr_block(
        session, period_start, period_end, Ticket.resolution_bucket == "Backline Engineering"
    )

    in_period = Ticket.created_at.between(period_start, period_end)
    actionable_resolved = _actionable_and_resolved()

    actionable_total = await session.scalar(
        select(func.count()).where(in_period, Ticket.actionable.is_(True))
    )

    # FRT on-time/missed, per the reference report: Automation, Passed On
    # (Passed to AM / Passed to Other Team), and CRM-UI-created tickets count
    # as on-time unconditionally -- none of them had a real "customer
    # waiting on a reply" clock running, regardless of what (if anything)
    # time_to_first_agent_reply_hours recorded for them.
    replied = Ticket.time_to_first_agent_reply_hours.isnot(None)
    on_time = Ticket.time_to_first_agent_reply_hours <= _FRT_SLA_HOURS
    frt_credited_count = await session.scalar(
        select(func.count()).where(in_period, actionable_resolved, _FRT_ALWAYS_ON_TIME)
    )
    frt_on_time_count = (
        await session.scalar(
            select(func.count()).where(in_period, actionable_resolved, replied, on_time, ~_FRT_ALWAYS_ON_TIME)
        )
        + frt_credited_count
    )
    frt_missed_count = await session.scalar(
        select(func.count()).where(in_period, actionable_resolved, replied, ~on_time, ~_FRT_ALWAYS_ON_TIME)
    )

    # HubSpot's own native SLA status, alongside this card's own custom
    # thresholds above -- first response here (FRT group), resolution/close
    # further down (TTR group), never mixed into the other's rows. on_time/
    # breached share one denominator (tickets with a definitive verdict), so
    # each pair always sums to 100%.
    sla = await utils.get_sla_kpis(session, period)
    first_response_sla_breakdown = sla["first_response_sla_status_breakdown"]
    frt_sla_on_time_count = first_response_sla_breakdown.get("Completed on time", 0)
    frt_sla_breached_count = first_response_sla_breakdown.get("Completed late", 0)
    frt_sla_evaluated_count = frt_sla_on_time_count + frt_sla_breached_count

    # TTR/MTTR, scoped like every other metric on this card -- by the
    # ticket's created_at month, actionable tickets only -- instead of
    # utils.get_summary's closed_at/all-tickets scope (which pulls in
    # Automation's near-instant auto-closes and drags outliers from
    # Non-Actionable backlog, matching neither the mean nor the median the
    # reference report shows).
    actionable_resolved_created = actionable_resolved & in_period
    ttr_resolved_count = await session.scalar(select(func.count()).where(actionable_resolved_created))
    mttr_hours = await session.scalar(
        select(func.avg(_resolution_time_hours_expr())).where(actionable_resolved_created)
    )
    median_hours = await session.scalar(
        select(_median_resolution_time_hours_expr()).where(actionable_resolved_created)
    )
    ttr_within_3_days_count = await session.scalar(
        select(func.count()).where(actionable_resolved_created, _resolution_time_hours_expr() <= 72)
    )
    resolution_sla_breakdown = sla["resolution_sla_status_breakdown"]
    resolution_sla_on_time_count = resolution_sla_breakdown.get("Completed on time", 0)
    resolution_sla_breached_count = resolution_sla_breakdown.get("Completed late", 0)
    resolution_sla_evaluated_count = resolution_sla_on_time_count + resolution_sla_breached_count

    bucket_counts = ownership["ticket_count_by_resolution_bucket"]
    support_count = bucket_counts.get("Support", 0)
    automation_count = bucket_counts.get("Automation", 0)

    return {
        "actionable_tickets": actionable_total or 0,
        "frt_on_time_count": frt_on_time_count,
        "frt_missed_count": frt_missed_count,
        "frt_sla_breached_count": frt_sla_breached_count,
        "frt_on_time_percentage": _percentage(frt_on_time_count, actionable_total),
        "frt_missed_percentage": _percentage(frt_missed_count, actionable_total),
        "frt_sla_on_time_percentage": _percentage(frt_sla_on_time_count, frt_sla_evaluated_count),
        "frt_sla_breached_percentage": _percentage(frt_sla_breached_count, frt_sla_evaluated_count),
        "fcr_true_count": fcr["fcr_true_count"],
        "fcr_false_count": fcr["fcr_false_count"],
        "fcr_within_24h_count": fcr["fcr_resolved_within_24_hours_count"],
        "fcr_percentage": fcr["first_contact_resolution_percentage"],
        "fcr_within_24h_percentage": _percentage(
            fcr["fcr_resolved_within_24_hours_count"], fcr["fcr_true_count"] + fcr["fcr_false_count"]
        ),
        "mttr_hours": round(mttr_hours, 1) if mttr_hours is not None else None,
        "mttr_days": round(mttr_hours / 24, 2) if mttr_hours is not None else None,
        "median_resolution_hours": round(median_hours, 1) if median_hours is not None else None,
        "median_resolution_days": round(median_hours / 24, 2) if median_hours is not None else None,
        "resolved_within_3_days_percentage": _percentage(ttr_within_3_days_count, ttr_resolved_count),
        "resolution_sla_breached_count": resolution_sla_breached_count,
        "resolution_sla_on_time_percentage": _percentage(
            resolution_sla_on_time_count, resolution_sla_evaluated_count
        ),
        "resolution_sla_breached_percentage": _percentage(
            resolution_sla_breached_count, resolution_sla_evaluated_count
        ),
        "resolved_by_support_count": support_count,
        "resolved_by_automation_count": automation_count,
        "resolved_by_engineering_count": bucket_counts.get("Engineering", 0),
        "resolved_by_backline_count": bucket_counts.get("Backline Engineering", 0),
        "resolved_by_support_automation_percentage": _percentage(
            support_count + automation_count, actionable_total
        ),
        "resolved_by_engineering_percentage": _percentage(bucket_counts.get("Engineering", 0), actionable_total),
        "resolved_by_backline_percentage": _percentage(
            bucket_counts.get("Backline Engineering", 0), actionable_total
        ),
        "csat_overall_unhappy_count": csat_overall["response_count_by_rating"].get(0, 0),
        "csat_overall_neutral_count": csat_overall["response_count_by_rating"].get(1, 0),
        "csat_overall_happy_count": csat_overall["response_count_by_rating"].get(2, 0),
        "csat_overall_normalized_percentage": csat_overall["normalized_csat_percentage"],
        "csat_raised_unhappy_count": csat_raised["response_count_by_rating"].get(0, 0),
        "csat_raised_neutral_count": csat_raised["response_count_by_rating"].get(1, 0),
        "csat_raised_happy_count": csat_raised["response_count_by_rating"].get(2, 0),
        "csat_raised_normalized_percentage": csat_raised["normalized_csat_percentage"],
        "nps_promoter_count": nps["promoter_count"],
        "nps_passive_count": nps["passive_count"],
        "nps_detractor_count": nps["detractor_count"],
        "nps_promoter_percentage": _percentage(nps["promoter_count"], nps["total_response_count"]),
        "nps_detractor_percentage": _percentage(nps["detractor_count"], nps["total_response_count"]),
        "nps_score": nps["nps_score"],
        "nps_mean_score": nps_mean,
        # engineering["count"]/backline["count"] aren't exposed here -- they'd
        # just repeat resolved_by_engineering_count/resolved_by_backline_count
        # above (this dict's TTR rows add the *timing* view: how fast, not
        # how many, which the ownership rows already cover).
        "engineering_resolved_within_3_days_count": engineering["within_3_days_count"],
        "engineering_resolved_within_3_days_percentage": engineering["within_3_days_percentage"],
        "engineering_mttr_hours": engineering["mean_hours"],
        "engineering_mttr_days": engineering["mean_days"],
        "backline_resolved_within_3_days_count": backline["within_3_days_count"],
        "backline_resolved_within_3_days_percentage": backline["within_3_days_percentage"],
        "backline_mttr_hours": backline["mean_hours"],
        "backline_mttr_days": backline["mean_days"],
    }


_FRT_SLA_NOTE = (
    "HubSpot's own first-response SLA status, across every ticket -- "
    "unlike this group's FRT (30 min) on-time/missed rows above, which are "
    "narrowed to actionable tickets with the Automation/Passed-On/CRM-UI/"
    "Non-Actionable credit rule applied. On-time % and breached % share one denominator "
    "(only tickets with a definitive verdict), so they always sum to 100%."
)
_RESOLUTION_SLA_NOTE = (
    "HubSpot's own resolution/close SLA status, across every ticket -- "
    "unlike this group's MTTR/median rows above, which are narrowed to "
    "actionable tickets only. On-time % and breached % share one "
    "denominator (only tickets with a definitive verdict), so they always "
    "sum to 100%."
)

# Static schema for the card: group/metric labels, display format, and the
# business-goal target for each row. Targets are config, not observed data --
# same convention as utils._FRT_SLA_HOURS -- so they don't need a DB query.
METRIC_GROUPS: list[dict] = [
    {
        "key": "frt",
        "label": "First Response Time (FRT)",
        "metrics": [
            {"key": "actionable_tickets", "label": "# of actionable tickets", "format": "number", "target": "-"},
            {"key": "frt_on_time_count", "label": "# of on-time FRT SLA (30 min) tickets", "format": "number", "target": "-"},
            {"key": "frt_missed_count", "label": "# of missed FRT SLA tickets", "format": "number", "target": "-"},
            {"key": "frt_sla_breached_count", "label": "# of SLA breached tickets (first response, HubSpot native)", "format": "number", "target": "-", "note": _FRT_SLA_NOTE},
            {"key": "frt_on_time_percentage", "label": "% of on-time FRT SLA (30 min) tickets", "format": "percent", "target": ">=80%"},
            {"key": "frt_missed_percentage", "label": "% of missed FRT SLA tickets", "format": "percent", "target": "<=20%"},
            {"key": "frt_sla_on_time_percentage", "label": "% SLA on-time (first response, HubSpot native)", "format": "percent", "target": "-", "note": _FRT_SLA_NOTE},
            {"key": "frt_sla_breached_percentage", "label": "% SLA breached (first response, HubSpot native)", "format": "percent", "target": "<=20%", "note": _FRT_SLA_NOTE},
        ],
    },
    {
        "key": "fcr",
        "label": "First Contact Resolution (FCR)",
        "metrics": [
            {"key": "fcr_true_count", "label": "# of tickets FCR (<=3 email) = Yes", "format": "number", "target": "-"},
            {"key": "fcr_false_count", "label": "# of tickets FCR (<=3 email) = No", "format": "number", "target": "-"},
            {"key": "fcr_within_24h_count", "label": "# of FCR=Yes tickets resolved <=24h", "format": "number", "target": "-"},
            {"key": "fcr_percentage", "label": "FCR %", "format": "percent", "target": ">=60%"},
            {"key": "fcr_within_24h_percentage", "label": "% of FCR tickets resolved within 24h", "format": "percent", "target": ">=50%"},
        ],
    },
    {
        "key": "ttr",
        "label": "Time To Resolve (TTR)",
        "metrics": [
            {"key": "mttr_hours", "label": "MTTR (avg resolution time, hrs)", "format": "hours", "target": "<=72 Hrs"},
            {"key": "mttr_days", "label": "MTTR (avg resolution time, days)", "format": "days", "target": "<=3 Days"},
            {"key": "median_resolution_hours", "label": "Median resolution (hrs)", "format": "hours", "target": "6 Hrs"},
            {"key": "median_resolution_days", "label": "Median resolution (days)", "format": "days", "target": "0.25 Days"},
            {"key": "resolved_within_3_days_percentage", "label": "% resolved within 3 days (SLA compliance)", "format": "percent", "target": ">=70%"},
            {"key": "resolution_sla_breached_count", "label": "# of SLA breached tickets (resolution, HubSpot native)", "format": "number", "target": "-", "note": _RESOLUTION_SLA_NOTE},
            {"key": "resolution_sla_on_time_percentage", "label": "% SLA on-time (resolution, HubSpot native)", "format": "percent", "target": "-", "note": _RESOLUTION_SLA_NOTE},
            {"key": "resolution_sla_breached_percentage", "label": "% SLA breached (resolution, HubSpot native)", "format": "percent", "target": "<=20%", "note": _RESOLUTION_SLA_NOTE},
        ],
    },
    {
        "key": "ownership",
        "label": "Resolution Ownership by Team",
        "metrics": [
            {"key": "resolved_by_support_count", "label": "# resolved by Support", "format": "number", "target": "-"},
            {"key": "resolved_by_automation_count", "label": "# resolved by Automation", "format": "number", "target": "-"},
            {"key": "resolved_by_engineering_count", "label": "# resolved by Engineering", "format": "number", "target": "-"},
            {"key": "resolved_by_backline_count", "label": "# resolved by Backline Engineering", "format": "number", "target": "-"},
            {"key": "resolved_by_support_automation_percentage", "label": "% resolved by Support + Automation", "format": "percent", "target": ">=70%"},
            {"key": "resolved_by_engineering_percentage", "label": "% resolved by Engineering (escalation rate)", "format": "percent", "target": "<=5%"},
            {"key": "resolved_by_backline_percentage", "label": "% resolved by Backline Engineering", "format": "percent", "target": "-"},
        ],
    },
    {
        "key": "csat",
        "label": "CSAT",
        "metrics": [
            {"key": "csat_overall_unhappy_count", "label": "Overall: # rated Unhappy (0)", "format": "number", "target": "-"},
            {"key": "csat_overall_neutral_count", "label": "Overall: # rated Neutral (1)", "format": "number", "target": "-"},
            {"key": "csat_overall_happy_count", "label": "Overall: # rated Happy (2)", "format": "number", "target": "-"},
            {"key": "csat_overall_normalized_percentage", "label": "Overall normalized CSAT %", "format": "percent", "target": ">=60%"},
            {"key": "csat_raised_unhappy_count", "label": "Raised tickets: # rated Unhappy (0)", "format": "number", "target": "-"},
            {"key": "csat_raised_neutral_count", "label": "Raised tickets: # rated Neutral (1)", "format": "number", "target": "-"},
            {"key": "csat_raised_happy_count", "label": "Raised tickets: # rated Happy (2)", "format": "number", "target": "-"},
            {"key": "csat_raised_normalized_percentage", "label": "Raised tickets normalized CSAT %", "format": "percent", "target": ">=60%"},
        ],
    },
    {
        "key": "nps",
        "label": "NPS",
        "metrics": [
            {"key": "nps_promoter_count", "label": "# of Promoters", "format": "number", "target": "-"},
            {"key": "nps_passive_count", "label": "# of Passives", "format": "number", "target": "-"},
            {"key": "nps_detractor_count", "label": "# of Detractors", "format": "number", "target": "-"},
            {"key": "nps_promoter_percentage", "label": "% Promoters", "format": "percent", "target": "-"},
            {"key": "nps_detractor_percentage", "label": "% Detractors", "format": "percent", "target": "-"},
            {"key": "nps_score", "label": "NPS score (Promoters - Detractors)", "format": "number", "target": "40"},
            {"key": "nps_mean_score", "label": "NPS mean score (out of 10)", "format": "score", "target": "8.2"},
        ],
    },
    {
        "key": "ttr_by_team",
        "label": "TTR by Resolving Team",
        "metrics": [
            {"key": "engineering_resolved_within_3_days_count", "label": "Engineering: # resolved <3 days", "format": "number", "target": "-"},
            {"key": "engineering_resolved_within_3_days_percentage", "label": "Engineering: % resolved <3 days", "format": "percent", "target": ">=80%"},
            {"key": "engineering_mttr_hours", "label": "Engineering: MTTR (hrs)", "format": "hours", "target": "<=72 Hrs"},
            {"key": "engineering_mttr_days", "label": "Engineering: MTTR (days)", "format": "days", "target": "<=3 Days"},
            {"key": "backline_resolved_within_3_days_count", "label": "Backline: # resolved <3 days", "format": "number", "target": "-"},
            {"key": "backline_resolved_within_3_days_percentage", "label": "Backline: % resolved <3 days", "format": "percent", "target": ">=80%"},
            {"key": "backline_mttr_hours", "label": "Backline: MTTR (hrs)", "format": "hours", "target": "<=72 Hrs"},
            {"key": "backline_mttr_days", "label": "Backline: MTTR (days)", "format": "days", "target": "<=3 Days"},
        ],
    },
]


async def _period_metrics_isolated(period: str) -> dict:
    """Runs one period's worth of queries on its own connection, pulled from
    the shared pool -- an AsyncSession can't be shared across concurrent
    coroutines, and every period below (16 of them: 3 months + 1 quarter
    total, x4 quarters) is independent of every other, so this is what lets
    them run concurrently instead of one after another."""
    async with db_manager.session_factory()() as session:
        return await _period_metrics(session, period)


async def get_frontline_metric_dashboard() -> dict:
    now = datetime.now(timezone.utc)
    quarters = _quarter_window(now)

    # Flatten to one list of periods (3 months + achieved, per quarter) and
    # fan them all out at once -- sequentially this endpoint was ~16 periods
    # x ~13 queries each, one at a time; concurrently it's bounded by the
    # slowest single period instead of their sum.
    periods = []
    for q in quarters:
        periods.extend(_period_for_month(y, m) for y, m in q["months"])
        periods.append(_period_for_quarter(q["months"]))
    all_metrics = await asyncio.gather(*(_period_metrics_isolated(p) for p in periods))

    result_quarters = []
    for i, q in enumerate(quarters):
        base = i * 4
        result_quarters.append(
            {
                "code": q["code"],
                "label": q["label"],
                "month_labels": [calendar.month_abbr[m] for _, m in q["months"]],
                "months": list(all_metrics[base : base + 3]),
                "achieved": all_metrics[base + 3],
            }
        )

    return {"quarters": result_quarters, "groups": METRIC_GROUPS}


def _link_dict(link: DashboardLink) -> dict:
    return {"id": link.id, "name": link.name, "url": link.url}


async def list_dashboard_links(session: AsyncSession) -> list[dict]:
    rows = await session.scalars(select(DashboardLink).order_by(DashboardLink.id))
    return [_link_dict(row) for row in rows]


async def add_dashboard_link(session: AsyncSession, name: str, url: str) -> dict:
    link = DashboardLink(name=name, url=url)
    session.add(link)
    await session.commit()
    return _link_dict(link)


async def update_dashboard_link(session: AsyncSession, link_id: int, name: str, url: str) -> dict | None:
    link = await session.get(DashboardLink, link_id)
    if link is None:
        return None
    link.name, link.url = name, url
    await session.commit()
    return _link_dict(link)


async def delete_dashboard_link(session: AsyncSession, link_id: int) -> None:
    await session.execute(sa_delete(DashboardLink).where(DashboardLink.id == link_id))
    await session.commit()
