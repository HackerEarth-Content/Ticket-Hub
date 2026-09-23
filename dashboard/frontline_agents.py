"""CRUD behind the "Frontline Agents" shift roster tab -- same shape as
DashboardLink in frontline_metric_dashboard.py (session-scoped functions,
thin routes). The roster (agents + their weekly shifts) is the single
source of truth for "who's on shift right now" -- the frontend derives that
from this data plus the current time instead of a separate status flag,
so there's nothing to keep in sync.
"""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.orm import AgentShift, FrontlineAgent

DAYS_PER_WEEK = 7

# Same convention as dashboard.utils._IST -- the support team's shifts are
# IST wall-clock times.
_IST = ZoneInfo("Asia/Kolkata")


def _shift_dict(shift: AgentShift) -> dict:
    return {
        "day_of_week": shift.day_of_week,
        "is_week_off": shift.is_week_off,
        "is_holiday": shift.is_holiday,
        "start_time": shift.start_time.isoformat(timespec="minutes")
        if shift.start_time
        else None,
        "end_time": shift.end_time.isoformat(timespec="minutes")
        if shift.end_time
        else None,
    }


def _agent_dict(agent: FrontlineAgent, shifts: list[AgentShift]) -> dict:
    by_day = {s.day_of_week: _shift_dict(s) for s in shifts}
    return {
        "id": agent.id,
        "name": agent.name,
        "email": agent.email,
        "slack_id": agent.slack_id,
        # Always all 7 days, even for a freshly-added agent with no shifts
        # saved yet -- the table renders a full week regardless.
        "shifts": [
            by_day.get(
                day,
                {
                    "day_of_week": day,
                    "is_week_off": True,
                    "is_holiday": False,
                    "start_time": None,
                    "end_time": None,
                },
            )
            for day in range(DAYS_PER_WEEK)
        ],
    }


async def list_agents(session: AsyncSession) -> list[dict]:
    agents = (
        await session.scalars(select(FrontlineAgent).order_by(FrontlineAgent.id))
    ).all()
    shifts = (await session.scalars(select(AgentShift))).all()
    shifts_by_agent: dict[int, list[AgentShift]] = {}
    for shift in shifts:
        shifts_by_agent.setdefault(shift.agent_id, []).append(shift)
    return [_agent_dict(agent, shifts_by_agent.get(agent.id, [])) for agent in agents]


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _shift_covers(shift: AgentShift, now_dow: int, now_minutes: int) -> bool:
    """Mirrors the frontend's agentShifts.ts shiftCovers -- handles shifts
    that cross midnight (end_time <= start_time) by also matching the
    tail-end on the following day_of_week."""
    if (
        shift.is_week_off
        or shift.is_holiday
        or shift.start_time is None
        or shift.end_time is None
    ):
        return False
    start, end = _to_minutes(shift.start_time), _to_minutes(shift.end_time)
    wraps = end <= start
    if not wraps:
        return shift.day_of_week == now_dow and start <= now_minutes < end
    return (shift.day_of_week == now_dow and now_minutes >= start) or (
        shift.day_of_week == (now_dow + 1) % 7 and now_minutes < end
    )


async def list_on_shift_now(session: AsyncSession) -> list[dict]:
    """Public counterpart to list_agents -- returns only the minimal contact
    info (name/email/slack_id) for agents whose shift covers this exact
    moment, computed server-side. Deliberately never exposes an agent's full
    week schedule or the contact info of anyone NOT currently on shift, so
    it's safe to leave unauthenticated (unlike /frontline/agents)."""
    now_ist = datetime.now(_IST)
    now_dow = (
        now_ist.weekday()
    )  # Python's Monday=0..Sunday=6 already matches day_of_week
    now_minutes = now_ist.hour * 60 + now_ist.minute

    agents = (
        await session.scalars(select(FrontlineAgent).order_by(FrontlineAgent.id))
    ).all()
    shifts = (await session.scalars(select(AgentShift))).all()
    shifts_by_agent: dict[int, list[AgentShift]] = {}
    for shift in shifts:
        shifts_by_agent.setdefault(shift.agent_id, []).append(shift)

    return [
        {
            "id": agent.id,
            "name": agent.name,
            "email": agent.email,
            "slack_id": agent.slack_id,
        }
        for agent in agents
        if any(
            _shift_covers(s, now_dow, now_minutes)
            for s in shifts_by_agent.get(agent.id, [])
        )
    ]


async def add_agent(
    session: AsyncSession, name: str, email: str, slack_id: str | None
) -> dict:
    agent = FrontlineAgent(name=name, email=email, slack_id=slack_id)
    session.add(agent)
    await session.commit()
    return _agent_dict(agent, [])


async def update_agent(
    session: AsyncSession, agent_id: int, name: str, email: str, slack_id: str | None
) -> dict | None:
    agent = await session.get(FrontlineAgent, agent_id)
    if agent is None:
        return None
    agent.name, agent.email, agent.slack_id = name, email, slack_id
    await session.commit()
    shifts = (
        await session.scalars(select(AgentShift).where(AgentShift.agent_id == agent_id))
    ).all()
    return _agent_dict(agent, list(shifts))


async def delete_agent(session: AsyncSession, agent_id: int) -> None:
    await session.execute(
        sa_delete(FrontlineAgent).where(FrontlineAgent.id == agent_id)
    )
    await session.commit()


async def swap_agent_shifts(
    session: AsyncSession, agent_a_id: int, agent_b_id: int
) -> dict | None:
    """Swaps two agents' entire weekly shift patterns (all 7 days, including
    week-off/holiday flags) -- for the common case where the *time slots*
    stay the same month to month and only who's in each one rotates. Only
    AgentShift.agent_id moves; each agent keeps their own name/email/Slack
    ID, since it's the schedule that's changing hands, not the person."""
    if agent_a_id == agent_b_id:
        return None
    agent_a = await session.get(FrontlineAgent, agent_a_id)
    agent_b = await session.get(FrontlineAgent, agent_b_id)
    if agent_a is None or agent_b is None:
        return None
    shifts_a = list(
        (
            await session.scalars(
                select(AgentShift).where(AgentShift.agent_id == agent_a_id)
            )
        ).all()
    )
    shifts_b = list(
        (
            await session.scalars(
                select(AgentShift).where(AgentShift.agent_id == agent_b_id)
            )
        ).all()
    )
    for shift in shifts_a:
        shift.agent_id = agent_b_id
    for shift in shifts_b:
        shift.agent_id = agent_a_id
    await session.commit()
    return {
        "a": _agent_dict(agent_a, shifts_b),
        "b": _agent_dict(agent_b, shifts_a),
    }


async def set_agent_shifts(
    session: AsyncSession, agent_id: int, shifts: list[dict]
) -> dict | None:
    """Replaces an agent's full week in one call -- the table always edits
    and saves a whole week's shape, never a single day in isolation."""
    agent = await session.get(FrontlineAgent, agent_id)
    if agent is None:
        return None
    await session.execute(sa_delete(AgentShift).where(AgentShift.agent_id == agent_id))
    for shift in shifts:
        session.add(
            AgentShift(
                agent_id=agent_id,
                day_of_week=shift["day_of_week"],
                is_week_off=shift.get("is_week_off", False),
                is_holiday=shift.get("is_holiday", False),
                start_time=shift.get("start_time"),
                end_time=shift.get("end_time"),
            )
        )
    await session.commit()
    saved = (
        await session.scalars(select(AgentShift).where(AgentShift.agent_id == agent_id))
    ).all()
    return _agent_dict(agent, list(saved))
