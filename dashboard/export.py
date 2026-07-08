"""Excel export -- one workbook per period, built from the same KPI dicts
the dashboard's own cards render (get_summary, get_sla_kpis, etc.) plus a raw
ticket-level sheet, so "download the data" means the same numbers, not a
second definition that can drift from what's on screen.
"""

from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.orm import NpsResponse, Ticket
from dashboard import backline, frontline, utils

_TICKET_COLUMNS = [
    "ticket_id",
    "subject",
    "pipeline_label",
    "stage_label",
    "canonical_status",
    "module",
    "primary_category",
    "customer_name",
    "priority",
    "derived_priority",
    "priority_inferred",
    "owner_name",
    "source_type",
    "reporter_contact_name",
    "created_at",
    "closed_at",
    "sla_first_response_status",
    "sla_close_status",
    "final_resolution",
    "resolution_bucket",
    "actionable",
    "fcr",
    "backline_engineer",
    "backline_path",
    "jira_link",
    "time_to_first_agent_reply_hours",
    "time_to_close_hours",
]


def _cell_value(value):
    """openpyxl can't write tz-aware datetimes or lists directly."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if hasattr(value, "isoformat"):
        return value.replace(tzinfo=None).isoformat() if value.tzinfo else value.isoformat()
    return value


def _autosize(ws: Worksheet) -> None:
    for i, column_cells in enumerate(ws.columns, start=1):
        length = max((len(str(c.value)) for c in column_cells if c.value is not None), default=8)
        ws.column_dimensions[get_column_letter(i)].width = min(length + 2, 60)


def _write_table(ws: Worksheet, rows: list[dict]) -> None:
    if not rows:
        ws.append(["No data for this period"])
        return
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([_cell_value(row.get(h)) for h in headers])
    _autosize(ws)


def _flatten(prefix: str, value, out: list[tuple[str, object]]) -> None:
    """Turns a KPI function's nested dict (breakdowns, sub-percentages) into
    flat "dotted.key -> value" rows -- one routine covers every KPI dict here
    instead of a bespoke formatter per metric."""
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(f"{prefix}.{k}" if prefix else str(k), v, out)
    else:
        out.append((prefix, _cell_value(value)))


def _write_kv_section(ws: Worksheet, title: str, data: dict) -> None:
    ws.append([title])
    rows: list[tuple[str, object]] = []
    _flatten("", data, rows)
    for key, value in rows:
        ws.append([key, value])
    ws.append([])


async def _fetch_tickets(session: AsyncSession, period: str) -> list[dict]:
    period_start, period_end = utils.resolve_period(period)
    rows = await session.execute(
        select(*[getattr(Ticket, c) for c in _TICKET_COLUMNS])
        .where(Ticket.created_at.between(period_start, period_end))
        .order_by(Ticket.created_at.desc())
    )
    return [dict(zip(_TICKET_COLUMNS, row)) for row in rows.all()]


_NPS_COLUMNS = [
    "response_id",
    "email",
    "score",
    "text",
    "created_at",
    "tags",
    "excluded_from_calculations",
]


async def _fetch_nps_responses(session: AsyncSession, period: str) -> list[dict]:
    period_start, period_end = utils.resolve_period(period)
    rows = await session.execute(
        select(*[getattr(NpsResponse, c) for c in _NPS_COLUMNS])
        .where(NpsResponse.created_at.between(period_start, period_end))
        .order_by(NpsResponse.created_at.desc())
    )
    return [dict(zip(_NPS_COLUMNS, row)) for row in rows.all()]


async def build_export_workbook(session: AsyncSession, period: str) -> bytes:
    tickets = await _fetch_tickets(session, period)
    nps_responses = await _fetch_nps_responses(session, period)
    agents = await utils.get_agent_kpis(session, period)

    summary = await utils.get_summary(session, period)
    sla = await utils.get_sla_kpis(session, period)
    csat = await utils.get_csat(session, period)
    nps = await utils.get_nps(session, period)
    data_quality = await utils.get_data_quality(session, period)
    backline_overview = await backline.get_backline_overview(session, period)
    frt = await frontline.get_frontline_frt(session, period)
    fcr = await frontline.get_frontline_fcr(session, period)

    wb = Workbook()
    ws_summary = wb.active
    ws_summary.title = "Summary"
    for title, data in [
        ("Summary", summary),
        ("SLA", sla),
        ("CSAT", csat),
        ("NPS", nps),
        ("Data quality", data_quality),
        ("Backline overview", backline_overview),
        # Per-owner breakdown is covered by the Agents sheet instead.
        ("Frontline FRT", {k: v for k, v in frt.items() if k != "by_owner"}),
        ("Frontline FCR", fcr),
    ]:
        _write_kv_section(ws_summary, title, data)
    _autosize(ws_summary)

    _write_table(wb.create_sheet("Tickets"), tickets)
    _write_table(wb.create_sheet("NPS Responses"), nps_responses)
    _write_table(wb.create_sheet("Agents"), agents)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
