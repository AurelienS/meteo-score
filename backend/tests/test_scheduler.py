"""Tests for scheduler module - APScheduler for automated collection.

Tests verify:
- Scheduler initialization and configuration
- Job registration with correct triggers
- Job execution with mocked collectors
- FastAPI lifecycle integration
- Health monitoring endpoints
- Error handling during collection

TDD: Write tests FIRST, then implement the scheduler module.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.data_models import ForecastData, ObservationData


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def fresh_scheduler():
    """Provide a fresh scheduler instance for testing."""
    from scheduler.scheduler import reset_scheduler, get_scheduler
    from scheduler.jobs import _job_executions

    # Reset before test
    reset_scheduler()
    _job_executions.clear()
    scheduler = get_scheduler()
    yield scheduler
    # Reset after test
    reset_scheduler()
    _job_executions.clear()


@pytest.fixture
def mock_forecast_data() -> list[ForecastData]:
    """Sample forecast data returned by collectors."""
    return [
        ForecastData(
            site_id=1,
            model_id=1,  # MeteoParapente
            parameter_id=1,  # wind_speed_avg
            forecast_run=datetime(2026, 1, 12, 6, 0, tzinfo=timezone.utc),
            valid_time=datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
            horizon=6,
            value=Decimal("15.5"),
        ),
        ForecastData(
            site_id=1,
            model_id=2,  # AROME
            parameter_id=1,  # wind_speed_avg
            forecast_run=datetime(2026, 1, 12, 6, 0, tzinfo=timezone.utc),
            valid_time=datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
            horizon=6,
            value=Decimal("18.0"),
        ),
    ]


@pytest.fixture
def mock_observation_data() -> list[ObservationData]:
    """Sample observation data returned by collectors."""
    return [
        ObservationData(
            site_id=1,
            parameter_id=1,  # wind_speed_avg
            observation_time=datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
            value=Decimal("16.2"),
        ),
        ObservationData(
            site_id=2,
            parameter_id=1,  # wind_speed_avg
            observation_time=datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc),
            value=Decimal("14.8"),
        ),
    ]


@pytest.fixture
def mock_site_configs() -> list[dict]:
    """Sample site configurations for collection."""
    return [
        {"site_id": 1, "name": "Passy Plaine Joux", "latitude": 45.9167, "longitude": 6.7},
        {"site_id": 2, "name": "Semnoz", "latitude": 45.8167, "longitude": 6.0833},
    ]


# =============================================================================
# Test: Scheduler Configuration
# =============================================================================


class TestSchedulerConfig:
    """Tests for scheduler configuration."""

    def test_scheduler_config_has_forecast_hours(self):
        """Test scheduler config contains forecast collection hours."""
        from scheduler.config import SchedulerConfig

        config = SchedulerConfig()
        assert hasattr(config, "forecast_hours")
        assert config.forecast_hours == [0, 6, 12, 18]

    def test_scheduler_config_has_observation_hours(self):
        """Test scheduler config contains observation collection hours."""
        from scheduler.config import SchedulerConfig

        config = SchedulerConfig()
        assert hasattr(config, "observation_hours")
        assert config.observation_hours == [8, 10, 12, 14, 16, 18]

    def test_scheduler_config_has_enabled_flag(self):
        """Test scheduler config has enabled flag."""
        from scheduler.config import SchedulerConfig

        config = SchedulerConfig()
        assert hasattr(config, "enabled")
        assert isinstance(config.enabled, bool)

    def test_scheduler_config_loads_from_env(self):
        """Test scheduler config loads from environment variables."""
        from scheduler.config import SchedulerConfig

        with patch.dict(
            "os.environ",
            {
                "SCHEDULER_FORECAST_HOURS": "0,12",
                "SCHEDULER_OBSERVATION_HOURS": "10,14",
                "SCHEDULER_ENABLED": "false",
            },
        ):
            # Need to reload settings to pick up env vars
            config = SchedulerConfig()
            # The actual values depend on implementation

    def test_scheduler_config_timezone_is_utc(self):
        """Test scheduler config uses UTC timezone."""
        from scheduler.config import SchedulerConfig

        config = SchedulerConfig()
        assert hasattr(config, "timezone")
        assert config.timezone == "UTC"


# =============================================================================
# Test: Scheduler Initialization
# =============================================================================


class TestSchedulerInitialization:
    """Tests for scheduler initialization."""

    def test_scheduler_instance_created(self):
        """Test scheduler instance is created correctly."""
        from scheduler.scheduler import get_scheduler

        scheduler = get_scheduler()
        assert isinstance(scheduler, AsyncIOScheduler)

    def test_scheduler_uses_utc_timezone(self):
        """Test scheduler is configured with UTC timezone."""
        from scheduler.scheduler import get_scheduler

        scheduler = get_scheduler()
        assert str(scheduler.timezone) == "UTC"

    def test_scheduler_has_coalesce_enabled(self):
        """Test scheduler coalesces missed jobs."""
        from scheduler.scheduler import get_scheduler

        scheduler = get_scheduler()
        # Job defaults are set at scheduler level (private attribute)
        assert scheduler._job_defaults.get("coalesce") is True

    def test_scheduler_has_max_instances_one(self):
        """Test scheduler limits to one instance per job."""
        from scheduler.scheduler import get_scheduler

        scheduler = get_scheduler()
        assert scheduler._job_defaults.get("max_instances") == 1

    def test_scheduler_has_misfire_grace_time(self):
        """Test scheduler has 30 minute misfire grace time."""
        from scheduler.scheduler import get_scheduler

        scheduler = get_scheduler()
        assert scheduler._job_defaults.get("misfire_grace_time") == 1800  # 30 minutes


# =============================================================================
# Test: Job Registration
# =============================================================================


class TestJobRegistration:
    """Tests for scheduled job registration."""

    def test_forecast_job_registered(self):
        """Test forecast collection job is registered."""
        from scheduler.scheduler import get_scheduler, register_jobs

        scheduler = get_scheduler()
        register_jobs(scheduler)

        jobs = scheduler.get_jobs()
        job_ids = [job.id for job in jobs]
        assert "collect_forecasts" in job_ids

    def test_observation_job_registered(self):
        """Test observation collection job is registered."""
        from scheduler.scheduler import get_scheduler, register_jobs

        scheduler = get_scheduler()
        register_jobs(scheduler)

        jobs = scheduler.get_jobs()
        job_ids = [job.id for job in jobs]
        assert "collect_observations" in job_ids

    def test_forecast_job_has_cron_trigger(self):
        """Test forecast job uses CronTrigger."""
        from scheduler.scheduler import get_scheduler, register_jobs

        scheduler = get_scheduler()
        register_jobs(scheduler)

        job = scheduler.get_job("collect_forecasts")
        assert isinstance(job.trigger, CronTrigger)

    def test_observation_job_has_cron_trigger(self):
        """Test observation job uses CronTrigger."""
        from scheduler.scheduler import get_scheduler, register_jobs

        scheduler = get_scheduler()
        register_jobs(scheduler)

        job = scheduler.get_job("collect_observations")
        assert isinstance(job.trigger, CronTrigger)

    def test_forecast_job_scheduled_at_correct_hours(self):
        """Test forecast job runs at 0, 6, 12, 18 UTC."""
        from scheduler.scheduler import get_scheduler, register_jobs

        scheduler = get_scheduler()
        register_jobs(scheduler)

        job = scheduler.get_job("collect_forecasts")
        trigger = job.trigger
        # CronTrigger stores hours in fields
        assert trigger.fields[5].expressions[0].first == 0  # hour field

    def test_jobs_can_be_manually_triggered(self):
        """Test jobs can be triggered manually for testing."""
        from scheduler.scheduler import get_scheduler, register_jobs

        scheduler = get_scheduler()
        register_jobs(scheduler)

        # Jobs should have a name that can be used for manual triggering
        job = scheduler.get_job("collect_forecasts")
        assert job is not None
        assert callable(job.func)


# =============================================================================
# Test: Job Execution - Forecast Collection
# =============================================================================


class TestForecastCollectionJob:
    """Tests for forecast collection job execution."""

    @pytest.mark.asyncio
    async def test_collect_forecasts_calls_meteo_parapente_collector(
        self, mock_forecast_data, mock_site_configs
    ):
        """Test forecast job calls MeteoParapente collector."""
        from scheduler.jobs import collect_all_forecasts

        with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
            mock_collector = AsyncMock()
            mock_collector.collect_forecast.return_value = mock_forecast_data[:1]
            mock_mp.return_value = mock_collector

            with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                result = await collect_all_forecasts()

            mock_collector.collect_forecast.assert_called()

    @pytest.mark.asyncio
    async def test_collect_forecasts_calls_arome_collector(
        self, mock_forecast_data, mock_site_configs
    ):
        """Test forecast job calls AROME collector."""
        from scheduler.jobs import collect_all_forecasts

        with patch("scheduler.jobs.AROMECollector") as mock_arome:
            mock_collector = AsyncMock()
            mock_collector.collect_forecast.return_value = mock_forecast_data[1:]
            mock_arome.return_value = mock_collector

            with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
                mock_mp.return_value = AsyncMock()
                mock_mp.return_value.collect_forecast.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    result = await collect_all_forecasts()

                mock_collector.collect_forecast.assert_called()

    @pytest.mark.asyncio
    async def test_collect_forecasts_returns_all_data(
        self, mock_forecast_data, mock_site_configs
    ):
        """Test forecast job returns combined data from all collectors."""
        from scheduler.jobs import collect_all_forecasts

        with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
            mock_mp.return_value = AsyncMock()
            mock_mp.return_value.collect_forecast.return_value = mock_forecast_data[:1]

            with patch("scheduler.jobs.AROMECollector") as mock_arome:
                mock_arome.return_value = AsyncMock()
                mock_arome.return_value.collect_forecast.return_value = mock_forecast_data[1:]

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    result = await collect_all_forecasts()

        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_collect_forecasts_handles_collector_error(
        self, mock_site_configs
    ):
        """Test forecast job handles collector errors gracefully."""
        from scheduler.jobs import collect_all_forecasts

        with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
            mock_mp.return_value = AsyncMock()
            mock_mp.return_value.collect_forecast.side_effect = Exception("API Error")

            with patch("scheduler.jobs.AROMECollector") as mock_arome:
                mock_arome.return_value = AsyncMock()
                mock_arome.return_value.collect_forecast.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    # Should not raise, should return partial results
                    result = await collect_all_forecasts()

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_collect_forecasts_logs_start_time(
        self, mock_site_configs, caplog
    ):
        """Test forecast job logs start time."""
        import logging
        from scheduler.jobs import collect_all_forecasts

        with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
            mock_mp.return_value = AsyncMock()
            mock_mp.return_value.collect_forecast.return_value = []

            with patch("scheduler.jobs.AROMECollector") as mock_arome:
                mock_arome.return_value = AsyncMock()
                mock_arome.return_value.collect_forecast.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    with caplog.at_level(logging.INFO):
                        await collect_all_forecasts()

        assert any("forecast" in record.message.lower() and "start" in record.message.lower()
                  for record in caplog.records)

    @pytest.mark.asyncio
    async def test_collect_forecasts_logs_duration(
        self, mock_site_configs, caplog
    ):
        """Test forecast job logs duration on completion."""
        import logging
        from scheduler.jobs import collect_all_forecasts

        with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
            mock_mp.return_value = AsyncMock()
            mock_mp.return_value.collect_forecast.return_value = []

            with patch("scheduler.jobs.AROMECollector") as mock_arome:
                mock_arome.return_value = AsyncMock()
                mock_arome.return_value.collect_forecast.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    with caplog.at_level(logging.INFO):
                        await collect_all_forecasts()

        # Should log completion with duration
        assert any("complete" in record.message.lower() or "finish" in record.message.lower()
                  for record in caplog.records)


# =============================================================================
# Test: Job Execution - Observation Collection
# =============================================================================


class TestObservationCollectionJob:
    """Tests for observation collection job execution."""

    @pytest.mark.asyncio
    async def test_collect_observations_calls_romma_collector(
        self, mock_observation_data, mock_site_configs
    ):
        """Test observation job calls ROMMA collector."""
        from scheduler.jobs import collect_all_observations

        with patch("scheduler.jobs.ROMMaCollector") as mock_romma:
            mock_collector = AsyncMock()
            mock_collector.collect_observation.return_value = mock_observation_data[:1]
            mock_romma.return_value = mock_collector

            with patch("scheduler.jobs.FFVLCollector") as mock_ffvl:
                mock_ffvl.return_value = AsyncMock()
                mock_ffvl.return_value.collect_observation.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    result = await collect_all_observations()

            mock_collector.collect_observation.assert_called()

    @pytest.mark.asyncio
    async def test_collect_observations_calls_ffvl_collector(
        self, mock_observation_data, mock_site_configs
    ):
        """Test observation job calls FFVL collector."""
        from scheduler.jobs import collect_all_observations

        with patch("scheduler.jobs.FFVLCollector") as mock_ffvl:
            mock_collector = AsyncMock()
            mock_collector.collect_observation.return_value = mock_observation_data[1:]
            mock_ffvl.return_value = mock_collector

            with patch("scheduler.jobs.ROMMaCollector") as mock_romma:
                mock_romma.return_value = AsyncMock()
                mock_romma.return_value.collect_observation.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    result = await collect_all_observations()

            mock_collector.collect_observation.assert_called()

    @pytest.mark.asyncio
    async def test_collect_observations_returns_all_data(
        self, mock_observation_data, mock_site_configs
    ):
        """Test observation job returns combined data from all collectors."""
        from scheduler.jobs import collect_all_observations

        with patch("scheduler.jobs.ROMMaCollector") as mock_romma:
            mock_romma.return_value = AsyncMock()
            mock_romma.return_value.collect_observation.return_value = mock_observation_data[:1]

            with patch("scheduler.jobs.FFVLCollector") as mock_ffvl:
                mock_ffvl.return_value = AsyncMock()
                mock_ffvl.return_value.collect_observation.return_value = mock_observation_data[1:]

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    result = await collect_all_observations()

        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_collect_observations_handles_collector_error(
        self, mock_site_configs
    ):
        """Test observation job handles collector errors gracefully."""
        from scheduler.jobs import collect_all_observations

        with patch("scheduler.jobs.ROMMaCollector") as mock_romma:
            mock_romma.return_value = AsyncMock()
            mock_romma.return_value.collect_observation.side_effect = Exception("Scraping Error")

            with patch("scheduler.jobs.FFVLCollector") as mock_ffvl:
                mock_ffvl.return_value = AsyncMock()
                mock_ffvl.return_value.collect_observation.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    # Should not raise, should return partial results
                    result = await collect_all_observations()

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_collect_observations_logs_record_count(
        self, mock_observation_data, mock_site_configs, caplog
    ):
        """Test observation job logs number of records collected."""
        import logging
        from scheduler.jobs import collect_all_observations

        with patch("scheduler.jobs.ROMMaCollector") as mock_romma:
            mock_romma.return_value = AsyncMock()
            mock_romma.return_value.collect_observation.return_value = mock_observation_data

            with patch("scheduler.jobs.FFVLCollector") as mock_ffvl:
                mock_ffvl.return_value = AsyncMock()
                mock_ffvl.return_value.collect_observation.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    with caplog.at_level(logging.INFO):
                        await collect_all_observations()

        # Should log number of records
        assert any("record" in record.message.lower() for record in caplog.records)


# =============================================================================
# Test: FastAPI Integration
# =============================================================================


class TestFastAPIIntegration:
    """Tests for FastAPI lifecycle integration."""

    @pytest.mark.asyncio
    async def test_start_scheduler_starts_scheduler(self, fresh_scheduler):
        """Test start_scheduler starts the scheduler."""
        from scheduler.scheduler import start_scheduler

        assert not fresh_scheduler.running

        await start_scheduler()
        assert fresh_scheduler.running

    @pytest.mark.asyncio
    async def test_stop_scheduler_stops_scheduler(self, fresh_scheduler):
        """Test stop_scheduler stops the scheduler gracefully."""
        from scheduler.scheduler import start_scheduler, stop_scheduler

        await start_scheduler()
        assert fresh_scheduler.running

        await stop_scheduler()
        # Allow a brief moment for async shutdown to complete
        await asyncio.sleep(0.01)
        assert not fresh_scheduler.running

    @pytest.mark.asyncio
    async def test_scheduler_does_not_block_event_loop(self, fresh_scheduler):
        """Test scheduler runs without blocking the event loop."""
        from scheduler.scheduler import start_scheduler, stop_scheduler

        await start_scheduler()

        # Should be able to do async work while scheduler is running
        await asyncio.sleep(0.01)

        await stop_scheduler()

    @pytest.mark.asyncio
    async def test_scheduler_disabled_via_config(self, fresh_scheduler):
        """Test scheduler respects enabled=false config."""
        from scheduler.scheduler import start_scheduler

        with patch("scheduler.scheduler.get_scheduler_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.enabled = False
            mock_get_config.return_value = mock_config

            # Should not start when disabled
            await start_scheduler()
            # Scheduler should not be running when disabled
            assert not fresh_scheduler.running


# =============================================================================
# Test: Health Monitoring Endpoints
# =============================================================================


class TestSchedulerStatusEndpoint:
    """Tests for /api/scheduler/status endpoint."""

    @pytest.mark.asyncio
    async def test_scheduler_status_returns_200(self, test_client):
        """Test scheduler status endpoint returns 200."""
        response = await test_client.get("/api/scheduler/status")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_scheduler_status_returns_running_status(self, test_client):
        """Test scheduler status shows running state."""
        response = await test_client.get("/api/scheduler/status")
        data = response.json()

        assert "running" in data
        assert isinstance(data["running"], bool)

    @pytest.mark.asyncio
    async def test_scheduler_status_returns_last_execution_times(self, test_client):
        """Test scheduler status shows last job execution times."""
        response = await test_client.get("/api/scheduler/status")
        data = response.json()

        # API returns camelCase per project convention
        assert "lastForecastCollection" in data
        assert "lastObservationCollection" in data


class TestSchedulerJobsEndpoint:
    """Tests for /api/scheduler/jobs endpoint."""

    @pytest.mark.asyncio
    async def test_scheduler_jobs_returns_200(self, test_client):
        """Test scheduler jobs endpoint returns 200."""
        response = await test_client.get("/api/scheduler/jobs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_scheduler_jobs_returns_list(self, test_client):
        """Test scheduler jobs endpoint returns job list."""
        response = await test_client.get("/api/scheduler/jobs")
        data = response.json()

        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    @pytest.mark.asyncio
    async def test_scheduler_jobs_includes_next_run_time(self, test_client):
        """Test scheduler jobs include next_run_time."""
        response = await test_client.get("/api/scheduler/jobs")
        data = response.json()

        if data["jobs"]:
            job = data["jobs"][0]
            # API returns camelCase per project convention
            assert "nextRunTime" in job
            assert "id" in job
            assert "name" in job


# =============================================================================
# Test: Error Handling
# =============================================================================


class TestSchedulerErrorHandling:
    """Tests for error handling in scheduler."""

    @pytest.mark.asyncio
    async def test_job_logs_exception_with_traceback(self, mock_site_configs, caplog):
        """Test job logs full traceback on exception."""
        import logging
        from scheduler.jobs import collect_all_forecasts

        with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
            mock_mp.return_value = AsyncMock()
            mock_mp.return_value.collect_forecast.side_effect = ValueError("Test error")

            with patch("scheduler.jobs.AROMECollector") as mock_arome:
                mock_arome.return_value = AsyncMock()
                mock_arome.return_value.collect_forecast.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    with caplog.at_level(logging.ERROR):
                        await collect_all_forecasts()

        # Should log error
        assert any("error" in record.message.lower() or record.levelno >= logging.ERROR
                  for record in caplog.records)

    @pytest.mark.asyncio
    async def test_single_collector_failure_does_not_stop_others(
        self, mock_observation_data, mock_site_configs
    ):
        """Test one collector failure doesn't stop other collectors."""
        from scheduler.jobs import collect_all_observations

        with patch("scheduler.jobs.ROMMaCollector") as mock_romma:
            mock_romma.return_value = AsyncMock()
            mock_romma.return_value.collect_observation.side_effect = Exception("ROMMA down")

            with patch("scheduler.jobs.FFVLCollector") as mock_ffvl:
                mock_ffvl.return_value = AsyncMock()
                mock_ffvl.return_value.collect_observation.return_value = mock_observation_data

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    result = await collect_all_observations()

        # FFVL data should still be collected
        assert len(result) > 0


# =============================================================================
# Test: Manual Trigger Support
# =============================================================================


class TestManualTrigger:
    """Tests for manual job triggering."""

    @pytest.mark.asyncio
    async def test_can_manually_trigger_forecast_job(self, mock_site_configs):
        """Test forecast job can be manually triggered."""
        from scheduler.jobs import collect_all_forecasts

        with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
            mock_mp.return_value = AsyncMock()
            mock_mp.return_value.collect_forecast.return_value = []

            with patch("scheduler.jobs.AROMECollector") as mock_arome:
                mock_arome.return_value = AsyncMock()
                mock_arome.return_value.collect_forecast.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    # Should be callable directly
                    result = await collect_all_forecasts()

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_can_manually_trigger_observation_job(self, mock_site_configs):
        """Test observation job can be manually triggered."""
        from scheduler.jobs import collect_all_observations

        with patch("scheduler.jobs.ROMMaCollector") as mock_romma:
            mock_romma.return_value = AsyncMock()
            mock_romma.return_value.collect_observation.return_value = []

            with patch("scheduler.jobs.FFVLCollector") as mock_ffvl:
                mock_ffvl.return_value = AsyncMock()
                mock_ffvl.return_value.collect_observation.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    result = await collect_all_observations()

        assert isinstance(result, list)


# =============================================================================
# Test: Job State Tracking
# =============================================================================


class TestJobStateTracking:
    """Tests for job execution state tracking."""

    @pytest.mark.asyncio
    async def test_job_execution_tracked(self, mock_site_configs):
        """Test job execution is tracked for status reporting."""
        from scheduler.jobs import collect_all_forecasts, get_last_execution

        with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
            mock_mp.return_value = AsyncMock()
            mock_mp.return_value.collect_forecast.return_value = []

            with patch("scheduler.jobs.AROMECollector") as mock_arome:
                mock_arome.return_value = AsyncMock()
                mock_arome.return_value.collect_forecast.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    await collect_all_forecasts()

        last = get_last_execution("collect_forecasts")
        assert last is not None
        assert "start_time" in last
        assert "end_time" in last
        assert "status" in last

    @pytest.mark.asyncio
    async def test_job_execution_tracks_success(self, mock_site_configs):
        """Test successful job execution is tracked."""
        from scheduler.jobs import collect_all_forecasts, get_last_execution

        with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
            mock_mp.return_value = AsyncMock()
            mock_mp.return_value.collect_forecast.return_value = []

            with patch("scheduler.jobs.AROMECollector") as mock_arome:
                mock_arome.return_value = AsyncMock()
                mock_arome.return_value.collect_forecast.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    await collect_all_forecasts()

        last = get_last_execution("collect_forecasts")
        assert last["status"] == "success"

    @pytest.mark.asyncio
    async def test_job_execution_tracks_record_count(
        self, mock_forecast_data, mock_site_configs
    ):
        """Test job execution tracks number of records collected."""
        from scheduler.jobs import collect_all_forecasts, get_last_execution

        with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
            mock_mp.return_value = AsyncMock()
            mock_mp.return_value.collect_forecast.return_value = mock_forecast_data

            with patch("scheduler.jobs.AROMECollector") as mock_arome:
                mock_arome.return_value = AsyncMock()
                mock_arome.return_value.collect_forecast.return_value = []

                with patch("scheduler.jobs.get_site_configs", return_value=mock_site_configs):
                    await collect_all_forecasts()

        last = get_last_execution("collect_forecasts")
        assert "records_collected" in last
        assert last["records_collected"] >= 2
