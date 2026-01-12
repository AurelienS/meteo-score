"""Scheduler health monitoring API endpoints.

This module provides endpoints for monitoring the scheduler status
and listing scheduled jobs.

Endpoints:
    GET /api/scheduler/status - Get scheduler running status and last execution times
    GET /api/scheduler/jobs - List all scheduled jobs with next run times
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from scheduler.jobs import get_all_job_statuses, get_last_execution
from scheduler.scheduler import get_scheduler


# Response schemas
class JobExecutionInfo(BaseModel):
    """Schema for job execution information."""

    model_config = ConfigDict(populate_by_name=True)

    start_time: Optional[str] = Field(None, alias="startTime")
    end_time: Optional[str] = Field(None, alias="endTime")
    duration_seconds: Optional[float] = Field(None, alias="durationSeconds")
    status: Optional[str] = None
    records_collected: Optional[int] = Field(None, alias="recordsCollected")


class SchedulerStatusResponse(BaseModel):
    """Response schema for scheduler status endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    running: bool
    last_forecast_collection: Optional[JobExecutionInfo] = Field(
        None, alias="lastForecastCollection"
    )
    last_observation_collection: Optional[JobExecutionInfo] = Field(
        None, alias="lastObservationCollection"
    )


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


router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status() -> SchedulerStatusResponse:
    """Get scheduler status and last execution times.

    Returns:
        SchedulerStatusResponse with running status and last job execution times.
    """
    scheduler = get_scheduler()

    last_forecast = get_last_execution("collect_forecasts")
    last_observation = get_last_execution("collect_observations")

    return SchedulerStatusResponse(
        running=scheduler.running,
        last_forecast_collection=JobExecutionInfo(**last_forecast) if last_forecast else None,
        last_observation_collection=JobExecutionInfo(**last_observation) if last_observation else None,
    )


@router.get("/jobs", response_model=SchedulerJobsResponse)
async def get_scheduler_jobs() -> SchedulerJobsResponse:
    """List all scheduled jobs with next run times.

    Returns:
        SchedulerJobsResponse with list of jobs and their details.
    """
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()

    job_list = []
    for job in jobs:
        next_run = job.next_run_time
        job_list.append(ScheduledJobInfo(
            id=job.id,
            name=job.name,
            next_run_time=next_run.isoformat() if next_run else None,
            trigger=str(job.trigger),
        ))

    return SchedulerJobsResponse(jobs=job_list)
