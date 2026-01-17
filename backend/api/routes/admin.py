"""Admin API endpoints for scheduler control and collection monitoring.

This module provides protected admin endpoints for:
- Viewing scheduler status and execution history
- Toggling scheduler on/off at runtime
- Triggering manual data collection
- Viewing data stats and preview

All endpoints require HTTP Basic Auth.

Endpoints:
    GET /api/admin/scheduler/status - Get scheduler status with execution history
    GET /api/admin/scheduler/jobs - List scheduled jobs with next run times
    POST /api/admin/scheduler/toggle - Start/stop scheduler
    POST /api/admin/collect/forecasts - Trigger manual forecast collection
    POST /api/admin/collect/observations - Trigger manual observation collection
    GET /api/admin/stats - Get total data counts
    GET /api/admin/data-preview - Get preview of recent collected data
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from api.dependencies.auth import verify_admin
from scheduler.jobs import (
    collect_all_forecasts,
    collect_all_observations,
    get_execution_history_async,
)
from scheduler.scheduler import get_scheduler, start_scheduler, stop_scheduler
from services.storage_service import get_data_stats, get_recent_data_preview


# Response schemas
class ExecutionRecord(BaseModel):
    """Schema for a single job execution record."""

    model_config = ConfigDict(populate_by_name=True)

    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")
    duration_seconds: float = Field(alias="durationSeconds")
    status: str
    records_collected: int = Field(alias="recordsCollected")
    records_persisted: int = Field(0, alias="recordsPersisted")
    errors: Optional[list[str]] = None


class AdminSchedulerStatusResponse(BaseModel):
    """Response schema for admin scheduler status endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    running: bool
    forecast_history: list[ExecutionRecord] = Field(alias="forecastHistory")
    observation_history: list[ExecutionRecord] = Field(alias="observationHistory")


class ScheduledJobInfo(BaseModel):
    """Schema for a scheduled job."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    next_run_time: Optional[str] = Field(None, alias="nextRunTime")
    trigger: str


class SchedulerJobsResponse(BaseModel):
    """Response schema for scheduler jobs endpoint."""

    jobs: list[ScheduledJobInfo]


class ToggleResponse(BaseModel):
    """Response schema for scheduler toggle endpoint."""

    running: bool
    message: str


class CollectionResponse(BaseModel):
    """Response schema for manual collection endpoints."""

    model_config = ConfigDict(populate_by_name=True)

    status: str
    records_collected: int = Field(alias="recordsCollected")
    records_persisted: int = Field(0, alias="recordsPersisted")
    duration_seconds: float = Field(alias="durationSeconds")
    errors: Optional[list[str]] = None


class DataStatsResponse(BaseModel):
    """Response schema for data statistics endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    total_forecasts: int = Field(alias="totalForecasts")
    total_observations: int = Field(alias="totalObservations")
    total_deviations: int = Field(alias="totalDeviations")
    total_pairs: int = Field(alias="totalPairs")
    total_sites: int = Field(alias="totalSites")


class DataPreviewResponse(BaseModel):
    """Response schema for data preview endpoint."""

    forecasts: dict[str, list[dict[str, Any]]]
    observations: dict[str, list[dict[str, Any]]]


# Create admin router with auth dependency applied to all routes
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin)],
)


@router.get("/scheduler/status", response_model=AdminSchedulerStatusResponse)
async def get_admin_scheduler_status() -> AdminSchedulerStatusResponse:
    """Get scheduler status with execution history.

    Returns:
        AdminSchedulerStatusResponse with running status and last 10 executions per job.
    """
    scheduler = get_scheduler()

    forecast_history = await get_execution_history_async("collect_forecasts", limit=10)
    observation_history = await get_execution_history_async("collect_observations", limit=10)

    return AdminSchedulerStatusResponse(
        running=scheduler.running,
        forecast_history=[ExecutionRecord(**record) for record in forecast_history],
        observation_history=[ExecutionRecord(**record) for record in observation_history],
    )


@router.get("/scheduler/jobs", response_model=SchedulerJobsResponse)
async def get_admin_scheduler_jobs() -> SchedulerJobsResponse:
    """List all scheduled jobs with next run times.

    Returns:
        SchedulerJobsResponse with list of jobs and their details.
    """
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()

    job_list = []
    for job in jobs:
        next_run = job.next_run_time
        job_list.append(
            ScheduledJobInfo(
                id=job.id,
                name=job.name,
                next_run_time=next_run.isoformat() if next_run else None,
                trigger=str(job.trigger),
            )
        )

    return SchedulerJobsResponse(jobs=job_list)


@router.post("/scheduler/toggle", response_model=ToggleResponse)
async def toggle_scheduler() -> ToggleResponse:
    """Toggle scheduler on/off.

    If scheduler is running, stops it. If stopped, starts it.

    Returns:
        ToggleResponse with new running state and message.
    """
    scheduler = get_scheduler()

    if scheduler.running:
        await stop_scheduler()
        return ToggleResponse(
            running=False,
            message="Scheduler stopped successfully",
        )
    else:
        await start_scheduler()
        return ToggleResponse(
            running=True,
            message="Scheduler started successfully",
        )


@router.post("/collect/forecasts", response_model=CollectionResponse)
async def trigger_forecast_collection() -> CollectionResponse:
    """Trigger immediate forecast collection.

    Runs the forecast collection job immediately, regardless of schedule.

    Returns:
        CollectionResponse with collection results.
    """
    try:
        result = await collect_all_forecasts()
        return CollectionResponse(
            status=result.get("status", "success"),
            records_collected=result.get("records_collected", 0),
            records_persisted=result.get("records_persisted", 0),
            duration_seconds=result.get("duration_seconds", 0),
            errors=result.get("errors"),
        )
    except Exception as e:
        logger.exception("Manual forecast collection failed")
        return CollectionResponse(
            status="failed",
            records_collected=0,
            records_persisted=0,
            duration_seconds=0,
            errors=[str(e)],
        )


@router.post("/collect/observations", response_model=CollectionResponse)
async def trigger_observation_collection() -> CollectionResponse:
    """Trigger immediate observation collection.

    Runs the observation collection job immediately, regardless of schedule.

    Returns:
        CollectionResponse with collection results.
    """
    try:
        result = await collect_all_observations()
        return CollectionResponse(
            status=result.get("status", "success"),
            records_collected=result.get("records_collected", 0),
            records_persisted=result.get("records_persisted", 0),
            duration_seconds=result.get("duration_seconds", 0),
            errors=result.get("errors"),
        )
    except Exception as e:
        logger.exception("Manual observation collection failed")
        return CollectionResponse(
            status="failed",
            records_collected=0,
            records_persisted=0,
            duration_seconds=0,
            errors=[str(e)],
        )


@router.get("/stats", response_model=DataStatsResponse)
async def get_admin_stats() -> DataStatsResponse:
    """Get total data statistics.

    Returns:
        DataStatsResponse with total counts for all data types.
    """
    stats = await get_data_stats()
    return DataStatsResponse(
        total_forecasts=stats.get("total_forecasts", 0),
        total_observations=stats.get("total_observations", 0),
        total_deviations=stats.get("total_deviations", 0),
        total_pairs=stats.get("total_pairs", 0),
        total_sites=stats.get("total_sites", 0),
    )


@router.get("/data-preview", response_model=DataPreviewResponse)
async def get_admin_data_preview() -> DataPreviewResponse:
    """Get preview of recently collected data.

    Returns last 5 records per source for quick verification.

    Returns:
        DataPreviewResponse with recent forecasts and observations grouped by source.
    """
    preview = await get_recent_data_preview(limit=5)
    return DataPreviewResponse(
        forecasts=preview.get("forecasts", {}),
        observations=preview.get("observations", {}),
    )
