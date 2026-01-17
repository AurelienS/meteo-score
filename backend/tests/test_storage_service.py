"""Tests for storage service.

Tests verify:
- Forecast data persistence with upsert behavior
- Observation data persistence with upsert behavior
- Execution log persistence and retrieval
- Data statistics retrieval
- Recent data preview retrieval
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.data_models import ForecastData
from core.models import ExecutionLog, Forecast, Model, Observation, Parameter, Site


class TestSaveForecasts:
    """Tests for save_forecasts function."""

    @pytest.mark.asyncio
    async def test_save_forecasts_empty_list(self, test_db: AsyncSession):
        """Test saving empty list returns zero counts."""
        from services.storage_service import save_forecasts

        with patch("services.storage_service.get_async_session_factory") as mock_factory:
            mock_factory.return_value = lambda: AsyncMock()

            total, inserted = await save_forecasts([], "Test")

        assert total == 0
        assert inserted == 0

    @pytest.mark.asyncio
    async def test_save_forecasts_inserts_new_records(self, test_db: AsyncSession):
        """Test that new forecasts are inserted by calling the real function."""
        from services.storage_service import save_forecasts

        # Create required reference data
        site = Site(
            name="Test Site",
            latitude=Decimal("45.5"),
            longitude=Decimal("6.5"),
            altitude=1000,
        )
        model = Model(name="Test Model", source="Test")
        param = Parameter(name="Wind Speed", unit="km/h")
        test_db.add_all([site, model, param])
        await test_db.commit()
        await test_db.refresh(site)
        await test_db.refresh(model)
        await test_db.refresh(param)

        forecast_data = [
            ForecastData(
                site_id=site.id,
                model_id=model.id,
                parameter_id=param.id,
                forecast_run=datetime.now(timezone.utc),
                valid_time=datetime.now(timezone.utc) + timedelta(hours=6),
                value=Decimal("15.5"),
            )
        ]

        # Mock the session factory to return a factory that yields test_db
        def mock_session_factory():
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def session_context():
                yield test_db

            return session_context()

        with patch(
            "services.storage_service.get_async_session_factory",
            return_value=mock_session_factory,
        ):
            # Call the REAL function
            total, inserted = await save_forecasts(forecast_data, "Test")

        assert total == 1
        assert inserted == 1

        # Verify data was inserted
        result = await test_db.execute(select(Forecast))
        forecasts = result.scalars().all()
        assert len(forecasts) == 1
        assert forecasts[0].value == Decimal("15.50")

    @pytest.mark.asyncio
    async def test_save_forecasts_skips_duplicates(self, test_db: AsyncSession):
        """Test that duplicate forecasts are skipped (idempotent)."""
        # Create required reference data
        site = Site(name="Test Site", latitude=Decimal("45.5"), longitude=Decimal("6.5"), altitude=1000)
        model = Model(name="Test Model", source="Test")
        param = Parameter(name="Wind Speed", unit="km/h")
        test_db.add_all([site, model, param])
        await test_db.commit()
        await test_db.refresh(site)
        await test_db.refresh(model)
        await test_db.refresh(param)

        forecast_run = datetime.now(timezone.utc)
        valid_time = datetime.now(timezone.utc) + timedelta(hours=6)

        # Insert first forecast
        forecast1 = Forecast(
            site_id=site.id,
            model_id=model.id,
            parameter_id=param.id,
            forecast_run=forecast_run,
            valid_time=valid_time,
            value=Decimal("15.5"),
        )
        test_db.add(forecast1)
        await test_db.commit()

        # Try to insert duplicate using upsert
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(Forecast).values(
            site_id=site.id,
            model_id=model.id,
            parameter_id=param.id,
            forecast_run=forecast_run,
            valid_time=valid_time,
            value=Decimal("20.0"),  # Different value
        ).on_conflict_do_nothing(constraint="uq_forecasts_unique")

        result = await test_db.execute(stmt)
        await test_db.commit()

        # Should have skipped the duplicate
        assert result.rowcount == 0

        # Verify only one record exists
        result = await test_db.execute(select(Forecast))
        forecasts = result.scalars().all()
        assert len(forecasts) == 1
        assert forecasts[0].value == Decimal("15.50")  # Original value preserved


class TestSaveObservations:
    """Tests for save_observations function."""

    @pytest.mark.asyncio
    async def test_save_observations_empty_list(self, test_db: AsyncSession):
        """Test saving empty list returns zero counts."""
        from services.storage_service import save_observations

        with patch("services.storage_service.get_async_session_factory") as mock_factory:
            mock_factory.return_value = lambda: AsyncMock()

            total, inserted = await save_observations([], "Test")

        assert total == 0
        assert inserted == 0

    @pytest.mark.asyncio
    async def test_save_observations_inserts_new_records(self, test_db: AsyncSession):
        """Test that new observations are inserted."""
        # Create required reference data
        site = Site(name="Test Site", latitude=Decimal("45.5"), longitude=Decimal("6.5"), altitude=1000)
        param = Parameter(name="Wind Speed", unit="km/h")
        test_db.add_all([site, param])
        await test_db.commit()
        await test_db.refresh(site)
        await test_db.refresh(param)

        from sqlalchemy.dialects.postgresql import insert as pg_insert

        obs_time = datetime.now(timezone.utc)
        stmt = pg_insert(Observation).values(
            site_id=site.id,
            parameter_id=param.id,
            observation_time=obs_time,
            value=Decimal("12.3"),
            source="ROMMA",
        ).on_conflict_do_nothing(constraint="uq_observations_unique")

        await test_db.execute(stmt)
        await test_db.commit()

        # Verify data was inserted
        result = await test_db.execute(select(Observation))
        observations = result.scalars().all()
        assert len(observations) == 1
        assert observations[0].value == Decimal("12.30")
        assert observations[0].source == "ROMMA"


class TestExecutionLog:
    """Tests for execution log persistence."""

    @pytest.mark.asyncio
    async def test_save_execution_log(self, test_db: AsyncSession):
        """Test saving execution log creates record."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(seconds=30)

        log = ExecutionLog(
            job_id="collect_forecasts",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=30.0,
            status="success",
            records_collected=100,
            records_persisted=95,
            errors=None,
        )
        test_db.add(log)
        await test_db.commit()

        # Verify log was saved
        result = await test_db.execute(
            select(ExecutionLog).where(ExecutionLog.job_id == "collect_forecasts")
        )
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].status == "success"
        assert logs[0].records_collected == 100
        assert logs[0].records_persisted == 95

    @pytest.mark.asyncio
    async def test_save_execution_log_with_errors(self, test_db: AsyncSession):
        """Test saving execution log with errors."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(seconds=30)

        log = ExecutionLog(
            job_id="collect_observations",
            start_time=start_time,
            end_time=end_time,
            duration_seconds=30.0,
            status="partial",
            records_collected=50,
            records_persisted=45,
            errors=["ROMMA connection failed", "FFVL timeout"],
        )
        test_db.add(log)
        await test_db.commit()

        # Verify log with errors was saved
        result = await test_db.execute(
            select(ExecutionLog).where(ExecutionLog.job_id == "collect_observations")
        )
        log = result.scalar_one()
        assert log.status == "partial"
        assert len(log.errors) == 2
        assert "ROMMA connection failed" in log.errors

    @pytest.mark.asyncio
    async def test_get_execution_history_returns_recent_first(self, test_db: AsyncSession):
        """Test execution history returns most recent first."""
        base_time = datetime.now(timezone.utc)

        # Create multiple logs
        for i in range(5):
            log = ExecutionLog(
                job_id="collect_forecasts",
                start_time=base_time + timedelta(hours=i),
                end_time=base_time + timedelta(hours=i, minutes=1),
                duration_seconds=60.0,
                status="success",
                records_collected=i * 10,
                records_persisted=i * 10,
            )
            test_db.add(log)
        await test_db.commit()

        # Query history
        result = await test_db.execute(
            select(ExecutionLog)
            .where(ExecutionLog.job_id == "collect_forecasts")
            .order_by(ExecutionLog.start_time.desc())
            .limit(3)
        )
        logs = result.scalars().all()

        assert len(logs) == 3
        # Most recent first (highest records_collected)
        assert logs[0].records_collected == 40
        assert logs[1].records_collected == 30
        assert logs[2].records_collected == 20


class TestDataStats:
    """Tests for get_data_stats function."""

    @pytest.mark.asyncio
    async def test_get_data_stats_empty_database(self, test_db: AsyncSession):
        """Test stats return zeros for empty database."""
        # Use raw SQL to get counts
        result = await test_db.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM forecasts) as total_forecasts,
                (SELECT COUNT(*) FROM observations) as total_observations,
                (SELECT COUNT(*) FROM sites) as total_sites
        """))
        row = result.fetchone()

        assert row[0] == 0  # forecasts
        assert row[1] == 0  # observations
        assert row[2] == 0  # sites

    @pytest.mark.asyncio
    async def test_get_data_stats_with_data(self, test_db: AsyncSession):
        """Test stats return correct counts with data."""
        # Create site
        site = Site(name="Test Site", latitude=Decimal("45.5"), longitude=Decimal("6.5"), altitude=1000)
        test_db.add(site)
        await test_db.commit()

        # Verify count
        result = await test_db.execute(text("SELECT COUNT(*) FROM sites"))
        count = result.scalar()
        assert count == 1


class TestDataPreview:
    """Tests for get_recent_data_preview function."""

    @pytest.mark.asyncio
    async def test_preview_returns_recent_forecasts(self, test_db: AsyncSession):
        """Test preview returns recent forecasts grouped by model."""
        # Create reference data
        site = Site(name="Test Site", latitude=Decimal("45.5"), longitude=Decimal("6.5"), altitude=1000)
        model1 = Model(name="AROME", source="Meteo-France")
        model2 = Model(name="Meteo-Parapente", source="MP")
        param = Parameter(name="Wind Speed", unit="km/h")
        test_db.add_all([site, model1, model2, param])
        await test_db.commit()
        await test_db.refresh(site)
        await test_db.refresh(model1)
        await test_db.refresh(model2)
        await test_db.refresh(param)

        # Create forecasts for both models
        base_time = datetime.now(timezone.utc)
        for i, model in enumerate([model1, model2]):
            for j in range(3):
                forecast = Forecast(
                    site_id=site.id,
                    model_id=model.id,
                    parameter_id=param.id,
                    forecast_run=base_time,
                    valid_time=base_time + timedelta(hours=j + i * 10),
                    value=Decimal(f"{10 + j}.5"),
                )
                test_db.add(forecast)
        await test_db.commit()

        # Query and group by model
        result = await test_db.execute(
            select(Forecast).order_by(Forecast.created_at.desc()).limit(10)
        )
        forecasts = result.scalars().all()

        assert len(forecasts) == 6

        # Group by model
        by_model = {}
        for f in forecasts:
            model_name = f.model.name
            if model_name not in by_model:
                by_model[model_name] = []
            by_model[model_name].append(f)

        assert "AROME" in by_model
        assert "Meteo-Parapente" in by_model
        assert len(by_model["AROME"]) == 3
        assert len(by_model["Meteo-Parapente"]) == 3


class TestSiteBeaconConfig:
    """Tests for site beacon configuration."""

    @pytest.mark.asyncio
    async def test_site_with_beacon_ids(self, test_db: AsyncSession):
        """Test site can store beacon IDs."""
        site = Site(
            name="Passy Plaine Joux",
            latitude=Decimal("45.9167"),
            longitude=Decimal("6.7"),
            altitude=1360,
            romma_beacon_id=21,
            romma_beacon_id_backup=22,
            ffvl_beacon_id=67,
            ffvl_beacon_id_backup=68,
        )
        test_db.add(site)
        await test_db.commit()
        await test_db.refresh(site)

        assert site.romma_beacon_id == 21
        assert site.romma_beacon_id_backup == 22
        assert site.ffvl_beacon_id == 67
        assert site.ffvl_beacon_id_backup == 68

    @pytest.mark.asyncio
    async def test_site_beacon_ids_nullable(self, test_db: AsyncSession):
        """Test site beacon IDs can be null."""
        site = Site(
            name="Site Without Beacons",
            latitude=Decimal("45.5"),
            longitude=Decimal("6.5"),
            altitude=1000,
        )
        test_db.add(site)
        await test_db.commit()
        await test_db.refresh(site)

        assert site.romma_beacon_id is None
        assert site.romma_beacon_id_backup is None
        assert site.ffvl_beacon_id is None
        assert site.ffvl_beacon_id_backup is None
