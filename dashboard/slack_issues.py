"""Content/On-Call tab -- tickets reported through the Slack source.

Only ~15 tickets total have source_type "Slack" (verified live 2026-07-07),
all content requests (test creation/review, question issues).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.orm import Ticket
from dashboard.utils import resolve_period

# Same cap/shape convention as the other ticket-level drill-downs
# (backline.py's escalations, utils.py's module/status drill-downs).
_DRILLDOWN_LIMIT = 100


def _classify_workflow(slack_workflow: str | None) -> str | None:
    """Buckets the raw "Workflow: <type>" line into one of the two types
    tracked on the dashboard. Returns None for anything else -- including
    tickets with no Workflow line at all (they predate this field) -- so
    callers decide whether that means "uncategorized" (get_slack_issues'
    table) or "drop it" (get_slack_workflow_breakdown's pie charts)."""
    if not slack_workflow:
        return None
    value = slack_workflow.lower()
    if "content" in value:
        return "content"
    if "oncall" in value or "engg" in value:
        return "engg_oncall"
    return None


async def get_slack_issues(session: AsyncSession, period: str) -> dict:
    """One row per Slack-sourced ticket: who reported it, who it's assigned
    to, and its stage (e.g. "Pending on Content (Support Pipeline)", not the
    coarser canonical_status). "Reporter" is parsed from the ticket
    description's "Reported By:" line (see models._extract_reported_by),
    falling back to the assigned owner when that line is missing.

    tickets_by_workflow_category splits the same tickets by the "Workflow:"
    line (see _classify_workflow) for the Content/Engg Oncall table filter --
    "uncategorized" here means no recognized Workflow line, shown separately
    rather than dropped (unlike get_slack_workflow_breakdown's pie charts).

    priority_by_team / priority_by_channel are the same priority histogram
    sliced by team ("content"/"engg_oncall"/"uncategorized") and by Slack
    channel ("Unknown" when no Channel line, see _extract_channel) -- they
    feed the priority chart's filter dropdown, computed server-side so counts
    stay correct past the drilldown cap.
    """
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(
            Ticket.ticket_id,
            Ticket.subject,
            Ticket.reporter_contact_name,
            Ticket.owner_name,
            Ticket.stage_label,
            Ticket.canonical_status,
            Ticket.created_at,
            Ticket.closed_at,
            Ticket.slack_workflow,
            Ticket.slack_channel,
            Ticket.derived_priority,
            Ticket.ticket_validity,
        )
        .where(
            Ticket.created_at.between(period_start, period_end),
            Ticket.source_type == "Slack",
            Ticket.actionable.is_(True),
        )
        .order_by(Ticket.created_at.desc())
    )

    issues = []
    by_reporter: dict[str, dict] = {}
    priority_counts: dict[str, int] = {}
    channel_counts: dict[str, int] = {}
    priority_by_team: dict[str, dict[str, int]] = {}
    priority_by_channel: dict[str, dict[str, int]] = {}
    issues_by_category: dict[str, list[dict]] = {
        "content": [],
        "engg_oncall": [],
        "uncategorized": [],
    }
    for (
        ticket_id,
        subject,
        reporter_contact_name,
        owner_name,
        stage_label,
        canonical_status,
        created_at,
        closed_at,
        slack_workflow,
        slack_channel,
        derived_priority,
        ticket_validity,
    ) in rows.all():
        reporter_name = reporter_contact_name or owner_name or "Unassigned"
        team = _classify_workflow(slack_workflow) or "uncategorized"
        channel = slack_channel or "Unknown"
        issue = {
            "ticket_id": ticket_id,
            "subject": subject,
            "reporter_name": reporter_name,
            "reporter_is_fallback_owner": reporter_contact_name is None,
            "owner_name": owner_name,
            "stage_label": stage_label,
            "created_at": created_at.isoformat() if created_at else None,
            "closed_at": closed_at.isoformat() if closed_at else None,
            "priority": derived_priority,
            "team": team,
            "channel": channel,
            "ticket_validity": ticket_validity,
        }
        issues.append(issue)
        issues_by_category[team].append(issue)

        # Aggregated across every matching ticket, not just the truncated
        # page below -- a chart summarizing "who reports issues" shouldn't
        # undercount past the drilldown cap. Same goes for the per-team/
        # per-channel priority counts feeding the priority chart's filters.
        bucket = by_reporter.setdefault(
            reporter_name, {"reported_count": 0, "solved_count": 0}
        )
        bucket["reported_count"] += 1
        if canonical_status == "Resolved":
            bucket["solved_count"] += 1
        priority_counts[derived_priority] = priority_counts.get(derived_priority, 0) + 1
        channel_counts[channel] = channel_counts.get(channel, 0) + 1
        team_counts = priority_by_team.setdefault(team, {})
        team_counts[derived_priority] = team_counts.get(derived_priority, 0) + 1
        chan_counts = priority_by_channel.setdefault(channel, {})
        chan_counts[derived_priority] = chan_counts.get(derived_priority, 0) + 1

    def _category_group(category: str) -> dict:
        category_issues = issues_by_category[category]
        return {
            "count": len(category_issues),
            "tickets": category_issues[:_DRILLDOWN_LIMIT],
            "truncated": len(category_issues) > _DRILLDOWN_LIMIT,
        }

    truncated = len(issues) > _DRILLDOWN_LIMIT
    return {
        "issue_count": len(issues),
        "issues": issues[:_DRILLDOWN_LIMIT],
        "truncated": truncated,
        "issue_count_by_priority": priority_counts,
        "issue_count_by_channel": channel_counts,
        "priority_by_team": priority_by_team,
        "priority_by_channel": priority_by_channel,
        "by_reporter": sorted(
            ({"reporter_name": name, **counts} for name, counts in by_reporter.items()),
            key=lambda r: r["reported_count"],
            reverse=True,
        ),
        "tickets_by_workflow_category": {
            "content": _category_group("content"),
            "engg_oncall": _category_group("engg_oncall"),
            "uncategorized": _category_group("uncategorized"),
        },
    }


async def get_slack_workflow_breakdown(session: AsyncSession, period: str) -> dict:
    """Reporter breakdown for the two Slack ticket-creation workflows
    (Content Request, Engg On-call), for the two pie charts on the
    Content/engg On-call tab. Tickets with no recognized Workflow line --
    including the legacy Slack tickets that predate this field -- are
    dropped from both buckets rather than shown as "uncategorized" (see
    _classify_workflow)."""
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(
            Ticket.slack_workflow,
            Ticket.reporter_contact_name,
            Ticket.owner_name,
            Ticket.canonical_status,
        ).where(
            Ticket.created_at.between(period_start, period_end),
            Ticket.source_type == "Slack",
            Ticket.actionable.is_(True),
        )
    )

    by_reporter: dict[str, dict[str, dict]] = {"content": {}, "engg_oncall": {}}
    for (
        slack_workflow,
        reporter_contact_name,
        owner_name,
        canonical_status,
    ) in rows.all():
        bucket = _classify_workflow(slack_workflow)
        if bucket is None:
            continue
        reporter_name = reporter_contact_name or owner_name or "Unassigned"
        counts = by_reporter[bucket].setdefault(
            reporter_name, {"reported_count": 0, "solved_count": 0}
        )
        counts["reported_count"] += 1
        if canonical_status == "Resolved":
            counts["solved_count"] += 1

    def _bucket_result(bucket: str) -> dict:
        reporters = sorted(
            (
                {"reporter_name": name, **counts}
                for name, counts in by_reporter[bucket].items()
            ),
            key=lambda r: r["reported_count"],
            reverse=True,
        )
        return {
            "issue_count": sum(r["reported_count"] for r in reporters),
            "by_reporter": reporters,
        }

    return {
        "content": _bucket_result("content"),
        "engg_oncall": _bucket_result("engg_oncall"),
    }
