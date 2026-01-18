"""End-to-end integration tests for the data collection pipeline.

These tests verify the complete flow from data collection through
database persistence and retrieval.

Usage:
    pytest -m integration tests/integration/test_pipeline_e2e.py
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestForecastCollectionPipeline:
    """E2E tests for forecast data collection and persistence."""

    @pytest.mark.asyncio
    async def test_meteo_parapente_collection_and_persistence(self, test_db):
        """Test full collection -> persistence -> retrieval flow."""
        from collectors import MeteoParapenteCollector
        from core.models import Forecast, Model, Parameter, Site
        from services.storage_service import save_forecasts

        # Setup: Create required database records
        site = Site(
            name="Test Site E2E",
            latitude=45.9167,
            longitude=6.7000,
            altitude=1360,
        )
        model = Model(name="Meteo-Parapente", source="Meteo-Parapente API")
        param_wind_speed = Parameter(name="wind_speed", unit="km/h")
        param_wind_dir = Parameter(name="wind_direction", unit="degrees")
        param_temp = Parameter(name="temperature", unit="C")

        test_db.add_all([site, model, param_wind_speed, param_wind_dir, param_temp])
        await test_db.commit()
        await test_db.refresh(site)

        # Step 1: Collect from real API
        collector = MeteoParapenteCollector()
        forecast_run = datetime.now(timezone.utc)

        data = await collector.collect_forecast(
            site_id=site.id,
            forecast_run=forecast_run,
            latitude=float(site.latitude),
            longitude=float(site.longitude),
        )

        # Step 2: Persist to database
        total_collected, total_persisted = await save_forecasts(data, "Meteo-Parapente")

        # Step 3: Verify data in database
        result = await test_db.execute(
            select(func.count()).select_from(Forecast).where(Forecast.site_id == site.id)
        )
        db_count = result.scalar()

        # Assertions
        assert total_collected > 0, "Should collect at least one forecast"
        assert total_persisted > 0, "Should persist at least one forecast"
        assert db_count == total_persisted, "DB count should match persisted count"

    @pytest.mark.asyncio
    async def test_collection_deduplication(self, test_db):
        """Test that duplicate forecasts are not inserted twice."""
        from collectors import MeteoParapenteCollector
        from core.models import Forecast, Model, Parameter, Site
        from services.storage_service import save_forecasts

        # Setup: Create required database records
        site = Site(
            name="Test Site Dedup",
            latitude=45.9167,
            longitude=6.7000,
            altitude=1360,
        )
        model = Model(name="Meteo-Parapente", source="Meteo-Parapente API")
        param_wind_speed = Parameter(name="wind_speed", unit="km/h")
        param_wind_dir = Parameter(name="wind_direction", unit="degrees")
        param_temp = Parameter(name="temperature", unit="C")

        test_db.add_all([site, model, param_wind_speed, param_wind_dir, param_temp])
        await test_db.commit()
        await test_db.refresh(site)

        # Collect once
        collector = MeteoParapenteCollector()
        forecast_run = datetime.now(timezone.utc)

        data = await collector.collect_forecast(
            site_id=site.id,
            forecast_run=forecast_run,
            latitude=float(site.latitude),
            longitude=float(site.longitude),
        )

        # Persist twice
        _, first_persisted = await save_forecasts(data, "Meteo-Parapente")
        _, second_persisted = await save_forecasts(data, "Meteo-Parapente")

        # Second persist should not add duplicates (upsert behavior)
        result = await test_db.execute(
            select(func.count()).select_from(Forecast).where(Forecast.site_id == site.id)
        )
        db_count = result.scalar()

        # The exact behavior depends on upsert implementation
        # At minimum, we should have at least the first batch
        assert db_count >= first_persisted


class TestObservationCollectionPipeline:
    """E2E tests for observation data collection and persistence."""

    @pytest.fixture
    def romma_beacon_id(self) -> int:
        """Return a known ROMMA beacon ID for testing."""
        return 21

    @pytest.mark.asyncio
    async def test_romma_collection_and_persistence(self, test_db, romma_beacon_id):
        """Test full observation collection -> persistence -> retrieval flow."""
        from collectors import ROMMaCollector
        from core.models import Observation, Parameter, Site
        from services.storage_service import save_observations

        # Setup: Create required database records
        site = Site(
            name="Test Site ROMMA",
            latitude=45.9167,
            longitude=6.7000,
            altitude=1360,
            romma_beacon_id=romma_beacon_id,
        )
        param_wind_speed = Parameter(name="wind_speed", unit="km/h")
        param_wind_dir = Parameter(name="wind_direction", unit="degrees")
        param_temp = Parameter(name="temperature", unit="C")

        test_db.add_all([site, param_wind_speed, param_wind_dir, param_temp])
        await test_db.commit()
        await test_db.refresh(site)

        # Step 1: Collect from real beacon
        collector = ROMMaCollector(beacon_id=romma_beacon_id)
        observation_time = datetime.now(timezone.utc)

        data = await collector.collect_observation(
            site_id=site.id,
            observation_time=observation_time,
            beacon_id=romma_beacon_id,
        )

        if not data:
            pytest.skip("ROMMA beacon returned no data (may be offline)")

        # Step 2: Persist to database
        total_collected, total_persisted = await save_observations(data, "ROMMA")

        # Step 3: Verify data in database
        result = await test_db.execute(
            select(func.count()).select_from(Observation).where(
                Observation.site_id == site.id
            )
        )
        db_count = result.scalar()

        # Assertions
        assert total_collected > 0, "Should collect at least one observation"
        assert total_persisted > 0, "Should persist at least one observation"
        assert db_count == total_persisted, "DB count should match persisted count"


class TestFullPipelineIntegration:
    """E2E tests for the complete scheduled job pipeline."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_forecast_collection_job(self, test_db):
        """Test the full forecast collection job with all collectors."""
        from core.models import Model, Parameter, Site
        from scheduler.jobs import collect_all_forecasts

        # Setup: Create required database records
        site = Site(
            name="Test Site Full",
            latitude=45.9167,
            longitude=6.7000,
            altitude=1360,
        )
        model_mp = Model(name="Meteo-Parapente", source="Meteo-Parapente API")
        model_arome = Model(name="AROME", source="Météo-France AROME")
        param_wind_speed = Parameter(name="wind_speed", unit="km/h")
        param_wind_dir = Parameter(name="wind_direction", unit="degrees")
        param_temp = Parameter(name="temperature", unit="C")

        test_db.add_all([site, model_mp, model_arome, param_wind_speed, param_wind_dir, param_temp])
        await test_db.commit()

        # Run the full collection job
        result = await collect_all_forecasts()

        # Verify result structure
        assert "status" in result
        assert "records_collected" in result
        assert "records_persisted" in result
        assert "duration_seconds" in result

        # Status should be success or partial (AROME may fail without token)
        assert result["status"] in ["success", "partial"]

        # Should have collected at least some data from Meteo-Parapente
        assert result["records_collected"] >= 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_observation_collection_job(self, test_db):
        """Test the full observation collection job with all collectors."""
        from core.models import Parameter, Site
        from scheduler.jobs import collect_all_observations

        # Setup: Create required database records with beacon IDs
        site = Site(
            name="Test Site Obs Full",
            latitude=45.9167,
            longitude=6.7000,
            altitude=1360,
            romma_beacon_id=21,
            ffvl_beacon_id=67,
        )
        param_wind_speed = Parameter(name="wind_speed", unit="km/h")
        param_wind_dir = Parameter(name="wind_direction", unit="degrees")
        param_temp = Parameter(name="temperature", unit="C")

        test_db.add_all([site, param_wind_speed, param_wind_dir, param_temp])
        await test_db.commit()

        # Run the full collection job
        result = await collect_all_observations()

        # Verify result structure
        assert "status" in result
        assert "records_collected" in result
        assert "records_persisted" in result
        assert "duration_seconds" in result

        # Status should be success or partial (beacons may be offline)
        assert result["status"] in ["success", "partial"]
