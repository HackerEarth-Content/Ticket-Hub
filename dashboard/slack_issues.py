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


async def get_slack_issues(session: AsyncSession, period: str) -> dict:
    """One row per Slack-sourced ticket: who reported it, who it's assigned
    to, and its stage (e.g. "Pending on Content (Support Pipeline)", not the
    coarser canonical_status). "Reporter" is parsed from the ticket
    description's "Reported By:" line (see models._extract_reported_by),
    falling back to the assigned owner when that line is missing.
    """
    period_start, period_end = resolve_period(period)
    rows = await session.execute(
        select(
            Ticket.ticket_id,
            Ticket.subject,
            Ticket.reporter_contact_name,
            Ticket.owner_name,
            Ticket.stage_label,
            Ticket.created_at,
        )
        .where(
            Ticket.created_at.between(period_start, period_end),
            Ticket.source_type == "Slack",
        )
        .order_by(Ticket.created_at.desc())
    )

    issues = [
        {
            "ticket_id": ticket_id,
            "subject": subject,
            "reporter_name": reporter_contact_name or owner_name or "Unassigned",
            "reporter_is_fallback_owner": reporter_contact_name is None,
            "owner_name": owner_name,
            "stage_label": stage_label,
            "created_at": created_at.isoformat() if created_at else None,
        }
        for ticket_id, subject, reporter_contact_name, owner_name, stage_label, created_at in rows.all()
    ]

    truncated = len(issues) > _DRILLDOWN_LIMIT
    return {
        "issue_count": len(issues),
        "issues": issues[:_DRILLDOWN_LIMIT],
        "truncated": truncated,
    }
