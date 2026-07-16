"""Dashboard routes. Thin -- all query/KPI logic lives in utils.py,
backline.py, and frontline.py."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.users import current_active_user, current_active_user_optional
from dashboard import backline, customers, export, frontline, slack_issues, utils
from hubspot_pipeline import pipeline as sync_pipeline

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


PeriodParam = Query("week", pattern=r"^(today|yesterday|week|month|custom:\d{4}-\d{2}-\d{2}:\d{4}-\d{2}-\d{2})$")


@router.get("/live/today")
async def live_today(session: AsyncSession = Depends(get_session)):
    return await utils.get_live_today(session)


@router.get("/summary")
async def summary(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await utils.get_summary(session, period)


@router.get("/volume/trend")
async def volume_trend(
    granularity: str = Query("day", pattern="^(hour|day|week|month)$"),
    period: str = PeriodParam,
    session: AsyncSession = Depends(get_session),
):
    return await utils.get_volume_trend(session, granularity, period)


@router.get("/distribution/module")
async def distribution_module(
    period: str = PeriodParam, session: AsyncSession = Depends(get_session)
):
    return await utils.get_module_distribution(session, period)


@router.get("/distribution/module/tickets")
async def distribution_module_tickets(
    period: str = PeriodParam,
    session: AsyncSession = Depends(get_session),
    user=Depends(current_active_user),
):
    return await utils.get_module_tickets(session, period)


@router.get("/distribution/source")
async def distribution_source(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await utils.get_source_distribution(session, period)


@router.get("/distribution/status")
async def distribution_status(
    period: str = PeriodParam,
    pipeline_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    return await utils.get_status_distribution(session, period, pipeline_id)


@router.get("/distribution/status/tickets")
async def distribution_status_tickets(
    period: str = PeriodParam,
    pipeline_id: str | None = None,
    session: AsyncSession = Depends(get_session),
    user=Depends(current_active_user),
):
    return await utils.get_status_tickets(session, period, pipeline_id)


@router.get("/distribution/stage")
async def distribution_stage(
    period: str = PeriodParam,
    pipeline_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """Granular per-stage breakdown (e.g. "Pending on Engineering" vs
    "Pending on BE/AE") that /distribution/status collapses into "Pending"."""
    return await utils.get_stage_distribution(session, period, pipeline_id)


@router.get("/kpis/mttr")
async def kpis_mttr(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await utils.get_median_resolution_time_by_priority(session, period)


@router.get("/kpis/sla")
async def kpis_sla(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await utils.get_sla_kpis(session, period)


@router.get("/kpis/csat")
async def kpis_csat(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await utils.get_csat(session, period)


@router.get("/kpis/nps")
async def kpis_nps(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await utils.get_nps(session, period)


@router.get("/kpis/agents")
async def kpis_agents(
    period: str = PeriodParam,
    session: AsyncSession = Depends(get_session),
    user=Depends(current_active_user),
):
    return await utils.get_agent_kpis(session, period)


@router.get("/kpis/data-quality")
async def kpis_data_quality(
    period: str = PeriodParam, session: AsyncSession = Depends(get_session)
):
    return await utils.get_data_quality(session, period)


@router.get("/backline/overview")
async def backline_overview(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await backline.get_backline_overview(session, period)


@router.get("/backline/ae-performance")
async def backline_ae_performance(
    period: str = PeriodParam,
    session: AsyncSession = Depends(get_session),
    user=Depends(current_active_user),
):
    return await backline.get_backline_ae_performance(session, period)


@router.get("/backline/escalations")
async def backline_escalations(
    period: str = PeriodParam,
    session: AsyncSession = Depends(get_session),
    user=Depends(current_active_user),
):
    return await backline.get_backline_escalations(session, period)


@router.get("/backline/stage-timing")
async def backline_stage_timing(
    period: str = PeriodParam, session: AsyncSession = Depends(get_session)
):
    return await backline.get_backline_stage_timing(session, period)


@router.get("/frontline/frt")
async def frontline_frt(
    period: str = PeriodParam,
    session: AsyncSession = Depends(get_session),
    user=Depends(current_active_user_optional),
):
    """`by_owner` breaks out named agents -- only included for logged-in
    team members, not the org-wide aggregate consumers of this endpoint."""
    result = await frontline.get_frontline_frt(session, period)
    if user is None:
        result.pop("by_owner", None)
    return result


@router.get("/frontline/fcr")
async def frontline_fcr(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await frontline.get_frontline_fcr(session, period)


@router.get("/frontline/resolution-ownership")
async def frontline_resolution_ownership(
    period: str = PeriodParam, session: AsyncSession = Depends(get_session)
):
    return await frontline.get_frontline_resolution_ownership(session, period)


@router.get("/quality/anomalies")
async def quality_anomalies(
    period: str = PeriodParam,
    session: AsyncSession = Depends(get_session),
    user=Depends(current_active_user),
):
    return await frontline.get_data_anomalies(session, period)


@router.get("/quality/uncategorized")
async def quality_uncategorized(
    period: str = PeriodParam,
    session: AsyncSession = Depends(get_session),
    user=Depends(current_active_user),
):
    return await frontline.get_uncategorized_tickets(session, period)


@router.get("/customers/volume")
async def customers_volume(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await customers.get_customer_ticket_volume(session, period)


@router.get("/customers/export")
async def customers_export(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    """Excel of per-customer issue counts -- same aggregate the Customers tab
    shows, so it shares that tab's (open) gating rather than /export's."""
    content = await export.build_customer_counts_workbook(session, period)
    filename = f"customer-issues-{period.replace(':', '_')}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/customers/status")
async def customers_status(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await customers.get_customer_status_breakdown(session, period)


@router.get("/customers/details")
async def customers_details(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await customers.get_customer_details(session, period)


@router.get("/slack/issues")
async def slack_issues_route(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await slack_issues.get_slack_issues(session, period)


@router.get("/slack/workflow-issues")
async def slack_workflow_issues_route(
    period: str = PeriodParam, session: AsyncSession = Depends(get_session)
):
    return await slack_issues.get_slack_workflow_breakdown(session, period)


@router.get("/export")
async def export_workbook(
    period: str = PeriodParam,
    session: AsyncSession = Depends(get_session),
    user=Depends(current_active_user),
):
    """Excel download of the period's raw tickets + the same KPI numbers the
    dashboard cards show -- gated behind sign-in like the other ticket-level
    drill-downs (module/status tickets, agent KPIs), since it's row-level
    detail with owner attribution, not the org-wide aggregate view."""
    content = await export.build_export_workbook(session, period)
    filename = f"helpdesk-export-{period.replace(':', '_')}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/meta/sync-status")
async def sync_status(session: AsyncSession = Depends(get_session)):
    return await utils.get_sync_status(session)


@router.get("/meta/pipelines")
async def pipelines(session: AsyncSession = Depends(get_session)):
    """Pipeline ID -> label lookup, so /distribution/status and
    /distribution/stage's pipeline_id filter doesn't require memorizing
    HubSpot's numeric pipeline IDs."""
    return await utils.get_pipelines(session)


@router.post("/meta/sync-now")
async def sync_now(session: AsyncSession = Depends(get_session)):
    """Runs the same incremental sync the cron job runs, on demand.
    Synchronous -- a normal incremental run takes a few seconds, so no
    background task queue is needed for this."""
    stats = await sync_pipeline.run_incremental()
    status = await utils.get_sync_status(session)
    return {"sync_stats": stats, **status}
