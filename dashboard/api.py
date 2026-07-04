"""Dashboard routes. Thin -- all query/KPI logic lives in utils.py."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from dashboard import utils
from hubspot_pipeline import pipeline as sync_pipeline

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

PeriodParam = Query("week", pattern="^(today|yesterday|week|month)$")


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


@router.get("/distribution/status")
async def distribution_status(
    period: str = PeriodParam,
    pipeline_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    return await utils.get_status_distribution(session, period, pipeline_id)


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


@router.get("/kpis/agents")
async def kpis_agents(period: str = PeriodParam, session: AsyncSession = Depends(get_session)):
    return await utils.get_agent_kpis(session, period)


@router.get("/kpis/data-quality")
async def kpis_data_quality(
    period: str = PeriodParam, session: AsyncSession = Depends(get_session)
):
    return await utils.get_data_quality(session, period)


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
