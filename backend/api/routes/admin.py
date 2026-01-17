"""Admin API endpoints for scheduler control and collection monitoring.

This module provides protected admin endpoints for:
- Viewing scheduler status and execution history
- Toggling scheduler on/off at runtime
- Triggering manual data collection

All endpoints require HTTP Basic Auth.

Endpoints:
    GET /api/admin/scheduler/status - Get scheduler status with execution history
    GET /api/admin/scheduler/jobs - List scheduled jobs with next run times
    POST /api/admin/scheduler/toggle - Start/stop scheduler
    POST /api/admin/collect/forecasts - Trigger manual forecast collection
    POST /api/admin/collect/observations - Trigger manual observation collection
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from api.dependencies.auth import verify_admin
from scheduler.jobs import (
    collect_all_forecasts,
    collect_all_observations,
    get_execution_history,
)
from scheduler.scheduler import get_scheduler, start_scheduler, stop_scheduler


# Response schemas
class ExecutionRecord(BaseModel):
    """Schema for a single job execution record."""

    model_config = ConfigDict(populate_by_name=True)

    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")
    duration_seconds: float = Field(alias="durationSeconds")
    status: str
    records_collected: int = Field(alias="recordsCollected")
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
    duration_seconds: float = Field(alias="durationSeconds")
    errors: Optional[list[str]] = None


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

    forecast_history = get_execution_history("collect_forecasts", limit=10)
    observation_history = get_execution_history("collect_observations", limit=10)

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
    start_time = datetime.now(timezone.utc)

    try:
        data = await collect_all_forecasts()
        status = "success"
        errors = None
    except Exception as e:
        logger.exception("Manual forecast collection failed")
        data = []
        status = "failed"
        errors = [str(e)]

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Get the latest execution record for accurate status
    history = get_execution_history("collect_forecasts", limit=1)
    if history:
        latest = history[0]
        return CollectionResponse(
            status=latest.get("status", status),
            records_collected=latest.get("records_collected", len(data)),
            duration_seconds=latest.get("duration_seconds", duration),
            errors=latest.get("errors"),
        )

    return CollectionResponse(
        status=status,
        records_collected=len(data),
        duration_seconds=duration,
        errors=errors,
    )


@router.post("/collect/observations", response_model=CollectionResponse)
async def trigger_observation_collection() -> CollectionResponse:
    """Trigger immediate observation collection.

    Runs the observation collection job immediately, regardless of schedule.

    Returns:
        CollectionResponse with collection results.
    """
    start_time = datetime.now(timezone.utc)

    try:
        data = await collect_all_observations()
        status = "success"
        errors = None
    except Exception as e:
        logger.exception("Manual observation collection failed")
        data = []
        status = "failed"
        errors = [str(e)]

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Get the latest execution record for accurate status
    history = get_execution_history("collect_observations", limit=1)
    if history:
        latest = history[0]
        return CollectionResponse(
            status=latest.get("status", status),
            records_collected=latest.get("records_collected", len(data)),
            duration_seconds=latest.get("duration_seconds", duration),
            errors=latest.get("errors"),
        )

    return CollectionResponse(
        status=status,
        records_collected=len(data),
        duration_seconds=duration,
        errors=errors,
    )
