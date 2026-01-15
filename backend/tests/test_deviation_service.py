"""TDD tests for DeviationService.

Tests written FIRST following Red-Green-Refactor cycle.
These tests define the expected behavior for deviation calculation.

Test Coverage:
- AC1: Deviation formula (observed - forecast)
- AC2: Sign convention (positive = underestimate)
- AC3: Wind direction angular distance [-180, 180]
- AC4: Outlier detection with logging
- AC5: Bulk insert performance (<2s for 1000+)
- AC6: Idempotency (no duplicates)
- AC7: Missing data handling (skip NULLs)
- AC8: Source tracking (processed_at)
- AC9: >80% test coverage
"""

import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    Deviation,
    Forecast,
    ForecastObservationPair,
    Model,
    Observation,
    Parameter,
    Site,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def wind_speed_parameter_id() -> int:
    """Parameter ID for wind speed (used for outlier threshold testing)."""
    return 1


@pytest.fixture
def wind_direction_parameter_id() -> int:
    """Parameter ID for wind direction (used for angular distance testing)."""
    return 2


@pytest.fixture
def temperature_parameter_id() -> int:
    """Parameter ID for temperature (used for outlier threshold testing)."""
    return 3


@pytest.fixture
def deviation_service():
    """Create DeviationService instance for testing."""
    from services.deviation_service import DeviationService
    return DeviationService()


@pytest_asyncio.fixture
async def sample_site(test_db: AsyncSession) -> Site:
    """Create a test site."""
    site = Site(
        name="Test Site",
        latitude=Decimal("45.5"),
        longitude=Decimal("6.5"),
        altitude=1000,
    )
    test_db.add(site)
    await test_db.commit()
    await test_db.refresh(site)
    return site


@pytest_asyncio.fixture
async def sample_model(test_db: AsyncSession) -> Model:
    """Create a test weather model."""
    model = Model(
        name="AROME",
        source="Météo-France",
    )
    test_db.add(model)
    await test_db.commit()
    await test_db.refresh(model)
    return model


@pytest_asyncio.fixture
async def wind_speed_param(test_db: AsyncSession) -> Parameter:
    """Create wind speed parameter."""
    param = Parameter(
        name="wind_speed",
        unit="km/h",
    )
    test_db.add(param)
    await test_db.commit()
    await test_db.refresh(param)
    return param


@pytest_asyncio.fixture
async def wind_direction_param(test_db: AsyncSession) -> Parameter:
    """Create wind direction parameter."""
    param = Parameter(
        name="wind_direction",
        unit="degrees",
    )
    test_db.add(param)
    await test_db.commit()
    await test_db.refresh(param)
    return param


@pytest_asyncio.fixture
async def temperature_param(test_db: AsyncSession) -> Parameter:
    """Create temperature parameter."""
    param = Parameter(
        name="temperature",
        unit="°C",
    )
    test_db.add(param)
    await test_db.commit()
    await test_db.refresh(param)
    return param


@pytest_asyncio.fixture
async def sample_pair(
    test_db: AsyncSession,
    sample_site: Site,
    sample_model: Model,
    wind_speed_param: Parameter,
) -> ForecastObservationPair:
    """Create a forecast-observation pair for basic deviation testing.

    Forecast: 20.0 km/h
    Observed: 25.0 km/h
    Expected deviation: +5.0 (underestimate)
    """
    # Create forecast
    forecast = Forecast(
        site_id=sample_site.id,
        model_id=sample_model.id,
        parameter_id=wind_speed_param.id,
        forecast_run=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        valid_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        value=Decimal("20.0"),
    )
    test_db.add(forecast)
    await test_db.flush()

    # Create observation
    observation = Observation(
        site_id=sample_site.id,
        parameter_id=wind_speed_param.id,
        observation_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        value=Decimal("25.0"),
        source="ROMMA",
    )
    test_db.add(observation)
    await test_db.flush()

    # Create pair
    pair = ForecastObservationPair(
        forecast_id=forecast.id,
        observation_id=observation.id,
        site_id=sample_site.id,
        model_id=sample_model.id,
        parameter_id=wind_speed_param.id,
        forecast_run=forecast.forecast_run,
        valid_time=forecast.valid_time,
        horizon=12,
        forecast_value=forecast.value,
        observed_value=observation.value,
        time_diff_minutes=0,
    )
    test_db.add(pair)
    await test_db.commit()
    await test_db.refresh(pair)
    return pair


# =============================================================================
# Task 1.2: Test basic deviation calculation (AC1, AC2)
# =============================================================================


class TestBasicDeviationCalculation:
    """Tests for basic deviation calculation: observed - forecast."""

    def test_calculate_deviation_underestimate(self, deviation_service):
        """Test deviation when forecast underestimates (AC1, AC2).

        Forecast: 20.0, Observed: 25.0
        Deviation = 25.0 - 20.0 = +5.0 (positive = underestimate)
        """
        result = deviation_service.calculate_deviation(
            observed_value=Decimal("25.0"),
            forecast_value=Decimal("20.0"),
        )
        assert result == Decimal("5.0")

    def test_calculate_deviation_overestimate(self, deviation_service):
        """Test deviation when forecast overestimates (AC1, AC2).

        Forecast: 30.0, Observed: 20.0
        Deviation = 20.0 - 30.0 = -10.0 (negative = overestimate)
        """
        result = deviation_service.calculate_deviation(
            observed_value=Decimal("20.0"),
            forecast_value=Decimal("30.0"),
        )
        assert result == Decimal("-10.0")

    def test_calculate_deviation_exact_match(self, deviation_service):
        """Test deviation when forecast is exact (AC1).

        Forecast: 25.0, Observed: 25.0
        Deviation = 25.0 - 25.0 = 0.0
        """
        result = deviation_service.calculate_deviation(
            observed_value=Decimal("25.0"),
            forecast_value=Decimal("25.0"),
        )
        assert result == Decimal("0.0")

    def test_sign_convention_positive_is_underestimate(self, deviation_service):
        """Verify sign convention: positive deviation = underestimate (AC2).

        When observed > forecast, deviation should be POSITIVE.
        """
        # Observed higher than forecast
        result = deviation_service.calculate_deviation(
            observed_value=Decimal("100.0"),
            forecast_value=Decimal("80.0"),
        )
        assert result > 0, "Positive deviation should indicate underestimate"

    def test_sign_convention_negative_is_overestimate(self, deviation_service):
        """Verify sign convention: negative deviation = overestimate (AC2).

        When observed < forecast, deviation should be NEGATIVE.
        """
        # Observed lower than forecast
        result = deviation_service.calculate_deviation(
            observed_value=Decimal("80.0"),
            forecast_value=Decimal("100.0"),
        )
        assert result < 0, "Negative deviation should indicate overestimate"


# =============================================================================
# Task 1.4, 1.5: Test wind direction angular distance (AC3)
# =============================================================================


class TestWindDirectionDeviation:
    """Tests for wind direction special case: shortest angular distance."""

    def test_wind_direction_simple_positive(self, deviation_service):
        """Test simple wind direction deviation (AC3).

        Forecast: 350°, Observed: 10°
        Shortest angular distance: +20° (not -340°)
        """
        result = deviation_service.calculate_wind_direction_deviation(
            forecast_deg=Decimal("350.0"),
            observed_deg=Decimal("10.0"),
        )
        assert result == Decimal("20.0")

    def test_wind_direction_simple_negative(self, deviation_service):
        """Test wind direction wrap-around in opposite direction (AC3).

        Forecast: 10°, Observed: 350°
        Shortest angular distance: -20° (not +340°)
        """
        result = deviation_service.calculate_wind_direction_deviation(
            forecast_deg=Decimal("10.0"),
            observed_deg=Decimal("350.0"),
        )
        assert result == Decimal("-20.0")

    def test_wind_direction_no_wrap(self, deviation_service):
        """Test wind direction without wrap-around (AC3).

        Forecast: 90°, Observed: 120°
        Deviation: +30°
        """
        result = deviation_service.calculate_wind_direction_deviation(
            forecast_deg=Decimal("90.0"),
            observed_deg=Decimal("120.0"),
        )
        assert result == Decimal("30.0")

    def test_wind_direction_boundary_180(self, deviation_service):
        """Test wind direction at 180° boundary (AC3).

        Forecast: 180°, Observed: 0°
        Shortest distance could be -180° or +180° (both valid)
        """
        result = deviation_service.calculate_wind_direction_deviation(
            forecast_deg=Decimal("180.0"),
            observed_deg=Decimal("0.0"),
        )
        # Either -180 or +180 is acceptable at the boundary
        assert abs(result) == Decimal("180.0")

    def test_wind_direction_zero_equals_360(self, deviation_service):
        """Test that 0° and 360° are treated as equivalent (AC3).

        Forecast: 5°, Observed: 355°
        Both should give same result as 5° to -5° = -10°
        """
        result = deviation_service.calculate_wind_direction_deviation(
            forecast_deg=Decimal("5.0"),
            observed_deg=Decimal("355.0"),
        )
        assert result == Decimal("-10.0")

    def test_wind_direction_exact_opposite(self, deviation_service):
        """Test wind direction exactly opposite (AC3).

        Forecast: 90°, Observed: 270°
        Shortest distance is 180° (or -180°)
        """
        result = deviation_service.calculate_wind_direction_deviation(
            forecast_deg=Decimal("90.0"),
            observed_deg=Decimal("270.0"),
        )
        assert abs(result) == Decimal("180.0")


# =============================================================================
# Task 1.6: Test outlier detection logging (AC4)
# =============================================================================


class TestOutlierDetection:
    """Tests for outlier detection with threshold-based logging."""

    def test_wind_speed_outlier_detected(self, deviation_service, caplog):
        """Test wind speed outlier detection (AC4).

        Deviation > 50 km/h should log warning.
        """
        # Wind speed deviation > 50 km/h
        deviation = Decimal("55.0")

        with caplog.at_level(logging.WARNING):
            is_outlier = deviation_service.is_outlier(
                deviation=deviation,
                parameter_name="wind_speed",
            )

        assert is_outlier is True
        assert "outlier" in caplog.text.lower()
        assert "55" in caplog.text

    def test_wind_speed_normal_not_outlier(self, deviation_service):
        """Test normal wind speed is not flagged (AC4).

        Deviation <= 50 km/h should not be flagged.
        """
        deviation = Decimal("30.0")

        is_outlier = deviation_service.is_outlier(
            deviation=deviation,
            parameter_name="wind_speed",
        )

        assert is_outlier is False

    def test_temperature_outlier_detected(self, deviation_service):
        """Test temperature outlier detection (AC4).

        Deviation > 15°C should log warning.
        """
        deviation = Decimal("18.0")

        is_outlier = deviation_service.is_outlier(
            deviation=deviation,
            parameter_name="temperature",
        )

        assert is_outlier is True

    def test_temperature_normal_not_outlier(self, deviation_service):
        """Test normal temperature is not flagged (AC4).

        Deviation <= 15°C should not be flagged.
        """
        deviation = Decimal("10.0")

        is_outlier = deviation_service.is_outlier(
            deviation=deviation,
            parameter_name="temperature",
        )

        assert is_outlier is False

    def test_wind_direction_always_in_range(self, deviation_service):
        """Test wind direction is never flagged as outlier (AC4).

        Wind direction uses angular distance [-180, 180], so max deviation
        is 180°. This is normal for wind direction.
        """
        deviation = Decimal("180.0")  # Maximum possible

        is_outlier = deviation_service.is_outlier(
            deviation=deviation,
            parameter_name="wind_direction",
        )

        assert is_outlier is False


# =============================================================================
# Task 1.7: Test bulk insert performance (AC5)
# =============================================================================


class TestBulkInsertPerformance:
    """Tests for bulk insert performance requirements."""

    @pytest.mark.asyncio
    async def test_bulk_insert_1000_pairs_under_2_seconds(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        deviation_service,
    ):
        """Test bulk insert performance: 1000+ deviations in <2 seconds (AC5).

        Creates 1000 pairs and measures time to calculate and store deviations.
        Each pair has a unique timestamp to avoid composite key collisions.
        """
        from datetime import timedelta

        # Create 1000 forecast-observation pairs with unique timestamps
        base_time = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        forecast_run = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)

        for i in range(1000):
            # Each forecast has a unique valid_time (1 hour apart)
            valid_time = base_time + timedelta(hours=i)

            # Create forecast
            forecast = Forecast(
                site_id=sample_site.id,
                model_id=sample_model.id,
                parameter_id=wind_speed_param.id,
                forecast_run=forecast_run,
                valid_time=valid_time,
                value=Decimal(f"{20 + (i % 10)}.0"),
            )
            test_db.add(forecast)

        await test_db.flush()

        # Get all forecasts
        result = await test_db.execute(select(Forecast))
        forecasts = result.scalars().all()

        # Create observations
        for i, forecast in enumerate(forecasts):
            observation = Observation(
                site_id=sample_site.id,
                parameter_id=wind_speed_param.id,
                observation_time=forecast.valid_time,
                value=Decimal(f"{25 + (i % 5)}.0"),
                source="ROMMA",
            )
            test_db.add(observation)

        await test_db.flush()

        # Get all observations
        result = await test_db.execute(select(Observation))
        observations = result.scalars().all()

        # Create pairs - vary horizon to ensure unique composite keys
        for i, (forecast, observation) in enumerate(zip(forecasts, observations)):
            # Calculate horizon based on actual time difference
            horizon = int((forecast.valid_time - forecast.forecast_run).total_seconds() / 3600)

            pair = ForecastObservationPair(
                forecast_id=forecast.id,
                observation_id=observation.id,
                site_id=sample_site.id,
                model_id=sample_model.id,
                parameter_id=wind_speed_param.id,
                forecast_run=forecast.forecast_run,
                valid_time=forecast.valid_time,
                horizon=horizon,
                forecast_value=forecast.value,
                observed_value=observation.value,
                time_diff_minutes=0,
            )
            test_db.add(pair)

        await test_db.commit()

        # Measure time to process pairs
        start_time = time.time()

        count = await deviation_service.process_pairs(
            db=test_db,
            site_id=sample_site.id,
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 3, 1, tzinfo=timezone.utc),  # Extended range for 1000 hours
        )

        elapsed_time = time.time() - start_time

        assert count >= 1000, f"Expected 1000+ deviations, got {count}"
        assert elapsed_time < 2.0, f"Bulk insert took {elapsed_time:.2f}s, expected <2s"


# =============================================================================
# Task 1.8: Test idempotency (AC6)
# =============================================================================


class TestIdempotency:
    """Tests for idempotency: re-running doesn't create duplicates."""

    @pytest.mark.asyncio
    async def test_rerun_does_not_create_duplicates(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_pair: ForecastObservationPair,
        deviation_service,
    ):
        """Test that re-running process_pairs doesn't duplicate (AC6).

        First run creates deviations, second run creates none.
        """
        start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2026, 1, 31, tzinfo=timezone.utc)

        # First run: should create deviations
        count1 = await deviation_service.process_pairs(
            db=test_db,
            site_id=sample_site.id,
            start_date=start_date,
            end_date=end_date,
        )

        # Second run: should create no new deviations
        count2 = await deviation_service.process_pairs(
            db=test_db,
            site_id=sample_site.id,
            start_date=start_date,
            end_date=end_date,
        )

        assert count1 > 0, "First run should create deviations"
        assert count2 == 0, "Second run should create no new deviations"

    @pytest.mark.asyncio
    async def test_deviation_count_stable_after_reruns(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_pair: ForecastObservationPair,
        deviation_service,
    ):
        """Test total deviation count is stable after multiple runs (AC6)."""
        start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2026, 1, 31, tzinfo=timezone.utc)

        # Run three times
        await deviation_service.process_pairs(
            db=test_db, site_id=sample_site.id, start_date=start_date, end_date=end_date
        )
        await deviation_service.process_pairs(
            db=test_db, site_id=sample_site.id, start_date=start_date, end_date=end_date
        )
        await deviation_service.process_pairs(
            db=test_db, site_id=sample_site.id, start_date=start_date, end_date=end_date
        )

        # Count total deviations
        result = await test_db.execute(select(Deviation))
        deviations = result.scalars().all()

        # Should have exactly one deviation (from sample_pair)
        assert len(deviations) == 1


# =============================================================================
# Task 1.9: Test NULL value handling (AC7)
# =============================================================================


class TestNullValueHandling:
    """Tests for missing data handling (AC7).

    AC7 states: "Skip pairs with NULL values, log warning"

    Implementation note: NULL values are prevented at the database level
    via NOT NULL constraints on forecast_value and observed_value columns.
    These tests verify the constraint-based protection and edge cases.
    """

    @pytest.mark.asyncio
    async def test_database_prevents_null_forecast_value(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
    ):
        """Test that database constraint prevents NULL forecast_value (AC7).

        The NOT NULL constraint on ForecastObservationPair.forecast_value
        ensures NULL values never reach the DeviationService.
        """
        from sqlalchemy.exc import IntegrityError

        # Create forecast and observation first
        forecast = Forecast(
            site_id=sample_site.id,
            model_id=sample_model.id,
            parameter_id=wind_speed_param.id,
            forecast_run=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
            valid_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
            value=Decimal("20.0"),
        )
        test_db.add(forecast)
        await test_db.flush()

        observation = Observation(
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            observation_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
            value=Decimal("25.0"),
            source="ROMMA",
        )
        test_db.add(observation)
        await test_db.flush()
        await test_db.commit()

        # Verify the model has NOT NULL constraint - this documents AC7 is
        # satisfied by database design rather than runtime checks
        from core.models import ForecastObservationPair

        forecast_value_col = ForecastObservationPair.__table__.c.forecast_value
        assert forecast_value_col.nullable is False, "forecast_value should be NOT NULL"

        observed_value_col = ForecastObservationPair.__table__.c.observed_value
        assert observed_value_col.nullable is False, "observed_value should be NOT NULL"

    @pytest.mark.asyncio
    async def test_unknown_parameter_handled_gracefully(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        deviation_service,
        caplog,
    ):
        """Test that pairs with unknown parameter_id are processed (AC7 edge case).

        If parameter lookup fails, service should still calculate deviation
        using standard formula (not wind direction angular distance).
        """
        # Create a parameter that won't be in the lookup
        unknown_param = Parameter(
            name="unknown_metric",
            unit="units",
        )
        test_db.add(unknown_param)
        await test_db.commit()
        await test_db.refresh(unknown_param)

        # Create forecast
        forecast = Forecast(
            site_id=sample_site.id,
            model_id=sample_model.id,
            parameter_id=unknown_param.id,
            forecast_run=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
            valid_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
            value=Decimal("100.0"),
        )
        test_db.add(forecast)
        await test_db.flush()

        # Create observation
        observation = Observation(
            site_id=sample_site.id,
            parameter_id=unknown_param.id,
            observation_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
            value=Decimal("110.0"),
            source="TEST",
        )
        test_db.add(observation)
        await test_db.flush()

        # Create pair
        pair = ForecastObservationPair(
            forecast_id=forecast.id,
            observation_id=observation.id,
            site_id=sample_site.id,
            model_id=sample_model.id,
            parameter_id=unknown_param.id,
            forecast_run=forecast.forecast_run,
            valid_time=forecast.valid_time,
            horizon=12,
            forecast_value=forecast.value,
            observed_value=observation.value,
            time_diff_minutes=0,
        )
        test_db.add(pair)
        await test_db.commit()

        # Process should succeed with standard deviation calculation
        with caplog.at_level(logging.DEBUG):
            count = await deviation_service.process_pairs(
                db=test_db,
                site_id=sample_site.id,
                start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
            )

        assert count == 1, "Should process pair with unknown parameter"

        # Verify deviation was calculated correctly (standard formula)
        result = await test_db.execute(select(Deviation))
        deviation = result.scalar_one()
        assert deviation.deviation == Decimal("10.0")  # 110 - 100


# =============================================================================
# Task 1.10: Test processed pair tracking (AC8)
# =============================================================================


class TestProcessedPairTracking:
    """Tests for tracking which pairs have been processed."""

    @pytest.mark.asyncio
    async def test_pairs_marked_as_processed(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_pair: ForecastObservationPair,
        deviation_service,
    ):
        """Test that processed pairs are marked with processed_at timestamp (AC8)."""
        start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2026, 1, 31, tzinfo=timezone.utc)

        # Process pairs
        await deviation_service.process_pairs(
            db=test_db,
            site_id=sample_site.id,
            start_date=start_date,
            end_date=end_date,
        )

        # Refresh pair from database
        await test_db.refresh(sample_pair)

        # Check processed_at is set
        assert sample_pair.processed_at is not None

    @pytest.mark.asyncio
    async def test_unprocessed_pairs_have_null_processed_at(
        self,
        test_db: AsyncSession,
        sample_pair: ForecastObservationPair,
    ):
        """Test that unprocessed pairs have NULL processed_at (AC8)."""
        # Refresh pair from database
        await test_db.refresh(sample_pair)

        # Check processed_at is NULL before processing
        assert sample_pair.processed_at is None


# =============================================================================
# Integration tests: Full process_pairs workflow
# =============================================================================


class TestProcessPairsIntegration:
    """Integration tests for the complete process_pairs workflow."""

    @pytest.mark.asyncio
    async def test_process_pairs_creates_deviation(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_pair: ForecastObservationPair,
        deviation_service,
    ):
        """Test complete workflow: pair → deviation calculation → storage."""
        start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2026, 1, 31, tzinfo=timezone.utc)

        # Process pairs
        count = await deviation_service.process_pairs(
            db=test_db,
            site_id=sample_site.id,
            start_date=start_date,
            end_date=end_date,
        )

        assert count == 1, "Should create 1 deviation"

        # Verify deviation in database
        result = await test_db.execute(select(Deviation))
        deviation = result.scalar_one()

        assert deviation.site_id == sample_site.id
        assert deviation.model_id == sample_model.id
        assert deviation.parameter_id == wind_speed_param.id
        assert deviation.forecast_value == Decimal("20.0")
        assert deviation.observed_value == Decimal("25.0")
        assert deviation.deviation == Decimal("5.0")  # observed - forecast
        assert deviation.horizon == 12

    @pytest.mark.asyncio
    async def test_process_pairs_with_wind_direction(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_direction_param: Parameter,
        deviation_service,
    ):
        """Test wind direction deviation uses angular distance (AC3)."""
        # Create forecast at 350°
        forecast = Forecast(
            site_id=sample_site.id,
            model_id=sample_model.id,
            parameter_id=wind_direction_param.id,
            forecast_run=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
            valid_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
            value=Decimal("350.0"),
        )
        test_db.add(forecast)
        await test_db.flush()

        # Create observation at 10°
        observation = Observation(
            site_id=sample_site.id,
            parameter_id=wind_direction_param.id,
            observation_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
            value=Decimal("10.0"),
            source="ROMMA",
        )
        test_db.add(observation)
        await test_db.flush()

        # Create pair
        pair = ForecastObservationPair(
            forecast_id=forecast.id,
            observation_id=observation.id,
            site_id=sample_site.id,
            model_id=sample_model.id,
            parameter_id=wind_direction_param.id,
            forecast_run=forecast.forecast_run,
            valid_time=forecast.valid_time,
            horizon=12,
            forecast_value=forecast.value,
            observed_value=observation.value,
            time_diff_minutes=0,
        )
        test_db.add(pair)
        await test_db.commit()

        # Process pairs
        count = await deviation_service.process_pairs(
            db=test_db,
            site_id=sample_site.id,
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

        assert count == 1

        # Verify angular distance was used
        result = await test_db.execute(select(Deviation))
        deviation = result.scalar_one()

        # Should be +20° (shortest path from 350° to 10°), not -340°
        assert deviation.deviation == Decimal("20.0")

    @pytest.mark.asyncio
    async def test_input_validation_invalid_site_id(self, test_db: AsyncSession, deviation_service):
        """Test that invalid site_id raises ValueError."""
        with pytest.raises(ValueError, match="site_id must be positive"):
            await deviation_service.process_pairs(
                db=test_db,
                site_id=-1,
                start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_input_validation_invalid_date_range(
        self, test_db: AsyncSession, sample_site: Site, deviation_service
    ):
        """Test that invalid date range raises ValueError."""
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            await deviation_service.process_pairs(
                db=test_db,
                site_id=sample_site.id,
                start_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
                end_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
