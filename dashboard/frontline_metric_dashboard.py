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

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import db_manager
from core.orm import CsatResponse, NpsResponse, Ticket
from dashboard import frontline, utils
from dashboard.utils import _normalized_csat_percentage, _percentage, _resolution_time_hours_expr, resolve_period
from hubspot_pipeline.resolution_map import UNRESOLVED_BUCKET
from hubspot_pipeline.stage_timing import BUG_BOUNTY_PATH

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

    frt = await frontline.get_frontline_frt(session, period)
    fcr = await frontline.get_frontline_fcr(session, period)
    summary = await utils.get_summary(session, period)
    sla = await utils.get_sla_kpis(session, period)
    ownership = await frontline.get_frontline_resolution_ownership(session, period)
    csat_raised = await utils.get_csat(session, period)
    csat_overall = await _get_csat_overall(session, period_start, period_end)
    nps = await utils.get_nps(session, period)
    nps_mean = await _get_nps_mean_score(session, period_start, period_end)
    engineering = await _ttr_block(session, period_start, period_end, Ticket.resolution_bucket == "Engineering")
    backline_incl = await _ttr_block(
        session, period_start, period_end, Ticket.resolution_bucket == "Backline Engineering"
    )
    backline_excl = await _ttr_block(
        session,
        period_start,
        period_end,
        Ticket.resolution_bucket == "Backline Engineering",
        Ticket.backline_path.is_distinct_from(BUG_BOUNTY_PATH),
    )

    actionable_total = await session.scalar(
        select(func.count()).where(
            Ticket.created_at.between(period_start, period_end), Ticket.actionable.is_(True)
        )
    )
    created_total = await session.scalar(
        select(func.count()).where(Ticket.created_at.between(period_start, period_end))
    )
    overdue_count = sla["resolution_sla_status_breakdown"].get("Completed late", 0)

    bucket_counts = ownership["ticket_count_by_resolution_bucket"]
    resolved_total = sum(count for bucket, count in bucket_counts.items() if bucket != UNRESOLVED_BUCKET)
    support_count = bucket_counts.get("Support", 0)
    automation_count = bucket_counts.get("Automation", 0)
    mttr_hours = summary["mean_resolution_time_hours"]
    median_hours = summary["median_resolution_time_hours"]

    return {
        "actionable_tickets": actionable_total or 0,
        "frt_on_time_count": frt["on_time_count"],
        "frt_missed_count": frt["missed_count"],
        "overdue_tickets": overdue_count,
        "frt_on_time_percentage": frt["on_time_percentage"],
        "frt_missed_percentage": _percentage(frt["missed_count"], frt["on_time_count"] + frt["missed_count"]),
        "overdue_percentage": _percentage(overdue_count, created_total),
        "fcr_true_count": fcr["fcr_true_count"],
        "fcr_false_count": fcr["fcr_false_count"],
        "fcr_within_24h_count": fcr["fcr_resolved_within_24_hours_count"],
        "fcr_percentage": fcr["first_contact_resolution_percentage"],
        "fcr_within_24h_percentage": fcr["fcr_resolved_within_24_hours_percentage"],
        "mttr_hours": mttr_hours,
        "mttr_days": round(mttr_hours / 24, 2) if mttr_hours is not None else None,
        "median_resolution_hours": median_hours,
        "median_resolution_days": round(median_hours / 24, 2) if median_hours is not None else None,
        "resolved_within_3_days_percentage": summary["resolution_within_72_hours_percentage"],
        "resolved_by_support_count": support_count,
        "resolved_by_automation_count": automation_count,
        "resolved_by_engineering_count": bucket_counts.get("Engineering", 0),
        "resolved_by_backline_count": bucket_counts.get("Backline Engineering", 0),
        "resolved_by_support_automation_percentage": _percentage(
            support_count + automation_count, resolved_total
        ),
        "resolved_by_engineering_percentage": ownership["percentage_of_resolved_by_bucket"].get("Engineering"),
        "resolved_by_backline_percentage": ownership["percentage_of_resolved_by_bucket"].get(
            "Backline Engineering"
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
        "engineering_resolved_count": engineering["count"],
        "engineering_resolved_within_3_days_count": engineering["within_3_days_count"],
        "engineering_resolved_within_3_days_percentage": engineering["within_3_days_percentage"],
        "engineering_mttr_hours": engineering["mean_hours"],
        "engineering_mttr_days": engineering["mean_days"],
        "backline_incl_bug_bounty_resolved_count": backline_incl["count"],
        "backline_incl_bug_bounty_within_3_days_count": backline_incl["within_3_days_count"],
        "backline_incl_bug_bounty_within_3_days_percentage": backline_incl["within_3_days_percentage"],
        "backline_incl_bug_bounty_mttr_hours": backline_incl["mean_hours"],
        "backline_incl_bug_bounty_mttr_days": backline_incl["mean_days"],
        "backline_excl_bug_bounty_resolved_count": backline_excl["count"],
        "backline_excl_bug_bounty_within_3_days_count": backline_excl["within_3_days_count"],
        "backline_excl_bug_bounty_within_3_days_percentage": backline_excl["within_3_days_percentage"],
        "backline_excl_bug_bounty_mttr_hours": backline_excl["mean_hours"],
        "backline_excl_bug_bounty_mttr_days": backline_excl["mean_days"],
    }


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
            {"key": "overdue_tickets", "label": "# of overdue tickets", "format": "number", "target": "-"},
            {"key": "frt_on_time_percentage", "label": "% of on-time FRT SLA (30 min) tickets", "format": "percent", "target": ">=80%"},
            {"key": "frt_missed_percentage", "label": "% of missed FRT SLA tickets", "format": "percent", "target": "<=20%"},
            {"key": "overdue_percentage", "label": "% of overdue tickets", "format": "percent", "target": "<=1%"},
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
            {"key": "engineering_resolved_count", "label": "Engineering: # resolved", "format": "number", "target": "-"},
            {"key": "engineering_resolved_within_3_days_count", "label": "Engineering: # resolved <3 days", "format": "number", "target": "-"},
            {"key": "engineering_resolved_within_3_days_percentage", "label": "Engineering: % resolved <3 days", "format": "percent", "target": ">=80%"},
            {"key": "engineering_mttr_hours", "label": "Engineering: MTTR (hrs)", "format": "hours", "target": "<=72 Hrs"},
            {"key": "engineering_mttr_days", "label": "Engineering: MTTR (days)", "format": "days", "target": "<=3 Days"},
            {"key": "backline_incl_bug_bounty_resolved_count", "label": "Backline (incl. Bug Bounty): # resolved", "format": "number", "target": "-"},
            {"key": "backline_incl_bug_bounty_within_3_days_count", "label": "Backline (incl. Bug Bounty): # resolved <3 days", "format": "number", "target": "-"},
            {"key": "backline_incl_bug_bounty_within_3_days_percentage", "label": "Backline (incl. Bug Bounty): % resolved <3 days", "format": "percent", "target": ">=80%"},
            {"key": "backline_incl_bug_bounty_mttr_hours", "label": "Backline (incl. Bug Bounty): MTTR (hrs)", "format": "hours", "target": "<=72 Hrs"},
            {"key": "backline_incl_bug_bounty_mttr_days", "label": "Backline (incl. Bug Bounty): MTTR (days)", "format": "days", "target": "<=3 Days"},
            {"key": "backline_excl_bug_bounty_resolved_count", "label": "Backline (excl. Bug Bounty): # resolved", "format": "number", "target": "-"},
            {"key": "backline_excl_bug_bounty_within_3_days_count", "label": "Backline (excl. Bug Bounty): # resolved <3 days", "format": "number", "target": "-"},
            {"key": "backline_excl_bug_bounty_within_3_days_percentage", "label": "Backline (excl. Bug Bounty): % resolved <3 days", "format": "percent", "target": ">=80%"},
            {"key": "backline_excl_bug_bounty_mttr_hours", "label": "Backline (excl. Bug Bounty): MTTR (hrs)", "format": "hours", "target": "<=72 Hrs"},
            {"key": "backline_excl_bug_bounty_mttr_days", "label": "Backline (excl. Bug Bounty): MTTR (days)", "format": "days", "target": "<=3 Days"},
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
