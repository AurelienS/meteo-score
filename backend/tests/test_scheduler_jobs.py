"""Tests for scheduler job functions.

Tests verify:
- Site configuration loading from database
- Forecast collection with data persistence
- Observation collection with backup beacon fallback
- Execution logging
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Site


class TestGetSiteConfigs:
    """Tests for get_site_configs_async function."""

    @pytest.mark.asyncio
    async def test_get_site_configs_returns_site_data(self, test_db: AsyncSession):
        """Test that site configs are loaded from database."""
        # Create a site with beacon IDs
        site = Site(
            name="Passy Plaine Joux",
            latitude=Decimal("45.9167"),
            longitude=Decimal("6.7"),
            altitude=1360,
            romma_beacon_id=21,
            romma_beacon_id_backup=22,
            ffvl_beacon_id=67,
            ffvl_beacon_id_backup=None,
        )
        test_db.add(site)
        await test_db.commit()
        await test_db.refresh(site)

        from scheduler.jobs import get_site_configs_async

        with patch("scheduler.jobs.get_async_session_factory") as mock_factory:
            mock_factory.return_value = lambda: test_db

            # Need to mock the context manager
            async def mock_session_cm():
                yield test_db

            with patch("scheduler.jobs.get_async_session_factory") as mock_factory:
                # Create mock that returns the session properly
                mock_session_maker = MagicMock()
                mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=test_db)
                mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
                mock_factory.return_value = mock_session_maker

                configs = await get_site_configs_async()

        assert len(configs) == 1
        config = configs[0]
        assert config["site_id"] == site.id
        assert config["name"] == "Passy Plaine Joux"
        assert config["latitude"] == 45.9167
        assert config["romma_beacon_id"] == 21
        assert config["romma_beacon_id_backup"] == 22
        assert config["ffvl_beacon_id"] == 67
        assert config["ffvl_beacon_id_backup"] is None


class TestCollectAllForecasts:
    """Tests for collect_all_forecasts function."""

    @pytest.mark.asyncio
    async def test_collect_forecasts_returns_dict(self):
        """Test that collect_all_forecasts returns expected dict structure."""
        from scheduler.jobs import collect_all_forecasts

        # Mock all dependencies
        mock_sites = [
            {
                "site_id": 1,
                "name": "Test Site",
                "latitude": 45.5,
                "longitude": 6.5,
                "romma_beacon_id": 21,
                "romma_beacon_id_backup": None,
                "ffvl_beacon_id": 67,
                "ffvl_beacon_id_backup": None,
            }
        ]

        with patch("scheduler.jobs.get_site_configs_async", new_callable=AsyncMock, return_value=mock_sites):
            with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
                with patch("scheduler.jobs.AROMECollector") as mock_arome:
                    with patch("scheduler.jobs.save_forecasts", new_callable=AsyncMock, return_value=(0, 0)):
                        with patch("scheduler.jobs.save_execution_log", new_callable=AsyncMock):
                            # Make collectors return empty data
                            mock_mp.return_value.collect_forecast = AsyncMock(return_value=[])
                            mock_arome.return_value.collect_forecast = AsyncMock(return_value=[])

                            result = await collect_all_forecasts()

        assert isinstance(result, dict)
        assert "status" in result
        assert "records_collected" in result
        assert "records_persisted" in result
        assert "duration_seconds" in result

    @pytest.mark.asyncio
    async def test_collect_forecasts_persists_data(self):
        """Test that collected forecasts are persisted."""
        from core.data_models import ForecastData
        from scheduler.jobs import collect_all_forecasts

        mock_sites = [
            {
                "site_id": 1,
                "name": "Test Site",
                "latitude": 45.5,
                "longitude": 6.5,
                "romma_beacon_id": 21,
                "romma_beacon_id_backup": None,
                "ffvl_beacon_id": 67,
                "ffvl_beacon_id_backup": None,
            }
        ]

        mock_forecast_data = [
            ForecastData(
                site_id=1,
                model_id=1,
                parameter_id=1,
                forecast_run=datetime.now(timezone.utc),
                valid_time=datetime.now(timezone.utc) + timedelta(hours=6),
                value=Decimal("15.5"),
            )
        ]

        with patch("scheduler.jobs.get_site_configs_async", new_callable=AsyncMock, return_value=mock_sites):
            with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
                with patch("scheduler.jobs.AROMECollector") as mock_arome:
                    with patch("scheduler.jobs.save_forecasts", new_callable=AsyncMock, return_value=(1, 1)) as mock_save:
                        with patch("scheduler.jobs.save_execution_log", new_callable=AsyncMock):
                            mock_mp.return_value.collect_forecast = AsyncMock(return_value=mock_forecast_data)
                            mock_arome.return_value.collect_forecast = AsyncMock(return_value=[])

                            result = await collect_all_forecasts()

        # Verify save_forecasts was called
        assert mock_save.called
        assert result["records_collected"] == 1
        assert result["records_persisted"] == 1


class TestCollectAllObservations:
    """Tests for collect_all_observations function."""

    @pytest.mark.asyncio
    async def test_collect_observations_returns_dict(self):
        """Test that collect_all_observations returns expected dict structure."""
        from scheduler.jobs import collect_all_observations

        mock_sites = [
            {
                "site_id": 1,
                "name": "Test Site",
                "latitude": 45.5,
                "longitude": 6.5,
                "romma_beacon_id": 21,
                "romma_beacon_id_backup": None,
                "ffvl_beacon_id": 67,
                "ffvl_beacon_id_backup": None,
            }
        ]

        with patch("scheduler.jobs.get_site_configs_async", new_callable=AsyncMock, return_value=mock_sites):
            with patch("scheduler.jobs.ROMMaCollector") as mock_romma:
                with patch("scheduler.jobs.FFVLCollector") as mock_ffvl:
                    with patch("scheduler.jobs.save_observations", new_callable=AsyncMock, return_value=(0, 0)):
                        with patch("scheduler.jobs.save_execution_log", new_callable=AsyncMock):
                            mock_romma.return_value.collect_observation = AsyncMock(return_value=[])
                            mock_ffvl.return_value.collect_observation = AsyncMock(return_value=[])

                            result = await collect_all_observations()

        assert isinstance(result, dict)
        assert "status" in result
        assert "records_collected" in result
        assert "records_persisted" in result
        assert "duration_seconds" in result

    @pytest.mark.asyncio
    async def test_collect_observations_tries_backup_on_failure(self):
        """Test that backup beacon is tried when primary fails."""
        from scheduler.jobs import collect_all_observations

        mock_sites = [
            {
                "site_id": 1,
                "name": "Test Site",
                "latitude": 45.5,
                "longitude": 6.5,
                "romma_beacon_id": 21,
                "romma_beacon_id_backup": 22,  # Has backup
                "ffvl_beacon_id": None,
                "ffvl_beacon_id_backup": None,
            }
        ]

        call_count = 0
        beacon_ids_called = []

        def mock_collector_factory(beacon_id=None):
            mock = MagicMock()
            beacon_ids_called.append(beacon_id)

            async def mock_collect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call (primary) fails
                    raise Exception("Primary beacon timeout")
                # Second call (backup) succeeds
                return []

            mock.collect_observation = mock_collect
            return mock

        with patch("scheduler.jobs.get_site_configs_async", new_callable=AsyncMock, return_value=mock_sites):
            with patch("scheduler.jobs.ROMMaCollector", side_effect=mock_collector_factory):
                with patch("scheduler.jobs.FFVLCollector") as mock_ffvl:
                    with patch("scheduler.jobs.save_observations", new_callable=AsyncMock, return_value=(0, 0)):
                        with patch("scheduler.jobs.save_execution_log", new_callable=AsyncMock):
                            mock_ffvl.return_value.collect_observation = AsyncMock(return_value=[])

                            result = await collect_all_observations()

        # Verify backup was tried
        assert 21 in beacon_ids_called  # Primary
        assert 22 in beacon_ids_called  # Backup
        # Status should be partial since primary failed
        assert result["status"] == "success"  # Backup succeeded

    @pytest.mark.asyncio
    async def test_collect_observations_no_beacons_logs_warning(self):
        """Test that missing beacons are logged as warning."""
        from scheduler.jobs import collect_all_observations

        mock_sites = [
            {
                "site_id": 1,
                "name": "Site Without Beacons",
                "latitude": 45.5,
                "longitude": 6.5,
                "romma_beacon_id": None,
                "romma_beacon_id_backup": None,
                "ffvl_beacon_id": None,
                "ffvl_beacon_id_backup": None,
            }
        ]

        with patch(
            "scheduler.jobs.get_site_configs_async",
            new_callable=AsyncMock,
            return_value=mock_sites,
        ):
            with patch("scheduler.jobs.ROMMaCollector"):
                with patch("scheduler.jobs.FFVLCollector"):
                    with patch(
                        "scheduler.jobs.save_observations",
                        new_callable=AsyncMock,
                        return_value=(0, 0),
                    ):
                        with patch(
                            "scheduler.jobs.save_execution_log",
                            new_callable=AsyncMock,
                        ):
                            with patch("scheduler.jobs.logger") as mock_logger:
                                await collect_all_observations()

        # Should warn about missing beacons
        warning_calls = list(mock_logger.warning.call_args_list)
        warning_messages = [str(call) for call in warning_calls]
        assert any("No ROMMA beacons" in msg for msg in warning_messages)
        assert any("No FFVL beacons" in msg for msg in warning_messages)


class TestExecutionLogging:
    """Tests for execution log creation."""

    @pytest.mark.asyncio
    async def test_execution_log_saved_after_forecast_collection(self):
        """Test that execution log is saved after forecast collection."""
        from scheduler.jobs import collect_all_forecasts

        mock_sites = [
            {
                "site_id": 1,
                "name": "Test Site",
                "latitude": 45.5,
                "longitude": 6.5,
                "romma_beacon_id": 21,
                "romma_beacon_id_backup": None,
                "ffvl_beacon_id": 67,
                "ffvl_beacon_id_backup": None,
            }
        ]

        with patch("scheduler.jobs.get_site_configs_async", new_callable=AsyncMock, return_value=mock_sites):
            with patch("scheduler.jobs.MeteoParapenteCollector") as mock_mp:
                with patch("scheduler.jobs.AROMECollector") as mock_arome:
                    with patch("scheduler.jobs.save_forecasts", new_callable=AsyncMock, return_value=(0, 0)):
                        with patch("scheduler.jobs.save_execution_log", new_callable=AsyncMock) as mock_log:
                            mock_mp.return_value.collect_forecast = AsyncMock(return_value=[])
                            mock_arome.return_value.collect_forecast = AsyncMock(return_value=[])

                            await collect_all_forecasts()

        # Verify execution log was saved
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs["job_id"] == "collect_forecasts"
        assert call_kwargs["status"] == "success"
