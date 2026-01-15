"""Tests for forecast-observation matching service.

TDD tests written FIRST before implementation.

Tests verify:
- AC1: Temporal matching (±30 min tolerance)
- AC2: Spatial matching (exact site_id)
- AC3: Parameter matching (exact parameter_id)
- AC4: Horizon calculation (valid_time - forecast_run in hours)
- AC5: Staging table (matched pairs stored correctly)
- AC6: Time tolerance boundaries (±29 min = match, ±31 min = no match)
- AC7: Multiple observations (select closest to valid_time)
- AC8: Idempotency (re-running doesn't duplicate)
- AC9: Test coverage >80%
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    Forecast,
    ForecastObservationPair,
    Model,
    Observation,
    Parameter,
    Site,
)
from services.matching_service import (
    MatchingService,
    calculate_horizon,
    calculate_time_diff_minutes,
    is_within_tolerance,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def matching_service() -> MatchingService:
    """Provide a MatchingService instance."""
    return MatchingService()


@pytest_asyncio.fixture
async def setup_reference_data(test_db: AsyncSession) -> dict:
    """Create reference data (site, model, parameter) for tests."""
    # Create site
    site = Site(
        name="Test Site",
        latitude=Decimal("45.916700"),
        longitude=Decimal("6.700000"),
        altitude=1360,
    )
    test_db.add(site)

    # Create model
    model = Model(
        name="AROME",
        source="Météo-France AROME model",
    )
    test_db.add(model)

    # Create parameter
    parameter = Parameter(
        name="Wind Speed",
        unit="km/h",
    )
    test_db.add(parameter)

    await test_db.commit()
    await test_db.refresh(site)
    await test_db.refresh(model)
    await test_db.refresh(parameter)

    return {
        "site": site,
        "model": model,
        "parameter": parameter,
    }


@pytest_asyncio.fixture
async def sample_forecast(
    test_db: AsyncSession,
    setup_reference_data: dict,
) -> Forecast:
    """Create a sample forecast for testing."""
    ref_data = setup_reference_data
    forecast = Forecast(
        site_id=ref_data["site"].id,
        model_id=ref_data["model"].id,
        parameter_id=ref_data["parameter"].id,
        forecast_run=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        valid_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        value=Decimal("25.50"),
    )
    test_db.add(forecast)
    await test_db.commit()
    await test_db.refresh(forecast)
    return forecast


@pytest_asyncio.fixture
async def sample_observation(
    test_db: AsyncSession,
    setup_reference_data: dict,
) -> Observation:
    """Create a sample observation at exactly the forecast valid_time."""
    ref_data = setup_reference_data
    observation = Observation(
        site_id=ref_data["site"].id,
        parameter_id=ref_data["parameter"].id,
        observation_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        value=Decimal("22.30"),
        source="ROMMA",
    )
    test_db.add(observation)
    await test_db.commit()
    await test_db.refresh(observation)
    return observation


# =============================================================================
# Test: Helper Functions
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_is_within_tolerance_exact_match(self):
        """Test observation at exactly valid_time is within tolerance."""
        valid_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        obs_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

        assert is_within_tolerance(valid_time, obs_time, 30) is True

    def test_is_within_tolerance_at_boundary_29min(self):
        """Test ±29 min = match (AC6)."""
        valid_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

        # 29 minutes before
        obs_before = datetime(2026, 1, 15, 11, 31, tzinfo=timezone.utc)
        assert is_within_tolerance(valid_time, obs_before, 30) is True

        # 29 minutes after
        obs_after = datetime(2026, 1, 15, 12, 29, tzinfo=timezone.utc)
        assert is_within_tolerance(valid_time, obs_after, 30) is True

    def test_is_within_tolerance_at_boundary_30min(self):
        """Test exactly 30 min is still within tolerance."""
        valid_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

        # Exactly 30 minutes before
        obs_before = datetime(2026, 1, 15, 11, 30, tzinfo=timezone.utc)
        assert is_within_tolerance(valid_time, obs_before, 30) is True

        # Exactly 30 minutes after
        obs_after = datetime(2026, 1, 15, 12, 30, tzinfo=timezone.utc)
        assert is_within_tolerance(valid_time, obs_after, 30) is True

    def test_is_within_tolerance_outside_31min(self):
        """Test ±31 min = no match (AC6)."""
        valid_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

        # 31 minutes before
        obs_before = datetime(2026, 1, 15, 11, 29, tzinfo=timezone.utc)
        assert is_within_tolerance(valid_time, obs_before, 30) is False

        # 31 minutes after
        obs_after = datetime(2026, 1, 15, 12, 31, tzinfo=timezone.utc)
        assert is_within_tolerance(valid_time, obs_after, 30) is False

    def test_calculate_horizon_6h(self):
        """Test horizon calculation for 6h forecast (AC4)."""
        forecast_run = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
        valid_time = datetime(2026, 1, 15, 6, 0, tzinfo=timezone.utc)

        assert calculate_horizon(forecast_run, valid_time) == 6

    def test_calculate_horizon_12h(self):
        """Test horizon calculation for 12h forecast (AC4)."""
        forecast_run = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
        valid_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

        assert calculate_horizon(forecast_run, valid_time) == 12

    def test_calculate_horizon_24h(self):
        """Test horizon calculation for 24h forecast (AC4)."""
        forecast_run = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
        valid_time = datetime(2026, 1, 16, 0, 0, tzinfo=timezone.utc)

        assert calculate_horizon(forecast_run, valid_time) == 24

    def test_calculate_horizon_48h(self):
        """Test horizon calculation for 48h forecast (AC4)."""
        forecast_run = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
        valid_time = datetime(2026, 1, 17, 0, 0, tzinfo=timezone.utc)

        assert calculate_horizon(forecast_run, valid_time) == 48

    def test_calculate_time_diff_minutes_exact(self):
        """Test time difference calculation for exact match."""
        valid_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        obs_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

        assert calculate_time_diff_minutes(valid_time, obs_time) == 0

    def test_calculate_time_diff_minutes_15min(self):
        """Test time difference calculation for 15 minute offset."""
        valid_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        obs_time = datetime(2026, 1, 15, 12, 15, tzinfo=timezone.utc)

        assert calculate_time_diff_minutes(valid_time, obs_time) == 15


# =============================================================================
# Test: Exact Time Match (AC1, AC2, AC3)
# =============================================================================


@pytest.mark.asyncio
async def test_exact_time_match(
    test_db: AsyncSession,
    matching_service: MatchingService,
    sample_forecast: Forecast,
    sample_observation: Observation,
    setup_reference_data: dict,
):
    """Test matching when observation is at exactly forecast.valid_time (3.2)."""
    ref_data = setup_reference_data

    pairs = await matching_service.match_forecasts_to_observations(
        db=test_db,
        site_id=ref_data["site"].id,
        start_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 15, 23, 59, tzinfo=timezone.utc),
    )

    assert len(pairs) == 1
    pair = pairs[0]

    # Verify matching
    assert pair.forecast_id == sample_forecast.id
    assert pair.observation_id == sample_observation.id
    assert pair.site_id == ref_data["site"].id
    assert pair.model_id == ref_data["model"].id
    assert pair.parameter_id == ref_data["parameter"].id

    # Verify values
    assert pair.forecast_value == Decimal("25.50")
    assert pair.observed_value == Decimal("22.30")
    assert pair.time_diff_minutes == 0

    # Verify horizon calculation (12h)
    assert pair.horizon == 12


# =============================================================================
# Test: Time Tolerance Boundaries (AC6)
# =============================================================================


@pytest.mark.asyncio
async def test_time_tolerance_29min_matches(
    test_db: AsyncSession,
    matching_service: MatchingService,
    sample_forecast: Forecast,
    setup_reference_data: dict,
):
    """Test ±29 min = match (3.3)."""
    ref_data = setup_reference_data

    # Create observation 29 minutes before valid_time
    observation = Observation(
        site_id=ref_data["site"].id,
        parameter_id=ref_data["parameter"].id,
        observation_time=datetime(2026, 1, 15, 11, 31, tzinfo=timezone.utc),
        value=Decimal("21.00"),
        source="ROMMA",
    )
    test_db.add(observation)
    await test_db.commit()

    pairs = await matching_service.match_forecasts_to_observations(
        db=test_db,
        site_id=ref_data["site"].id,
        start_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 15, 23, 59, tzinfo=timezone.utc),
    )

    assert len(pairs) == 1
    assert pairs[0].time_diff_minutes == 29


@pytest.mark.asyncio
async def test_time_tolerance_31min_no_match(
    test_db: AsyncSession,
    matching_service: MatchingService,
    sample_forecast: Forecast,
    setup_reference_data: dict,
):
    """Test ±31 min = no match (3.3)."""
    ref_data = setup_reference_data

    # Create observation 31 minutes after valid_time (outside tolerance)
    observation = Observation(
        site_id=ref_data["site"].id,
        parameter_id=ref_data["parameter"].id,
        observation_time=datetime(2026, 1, 15, 12, 31, tzinfo=timezone.utc),
        value=Decimal("21.00"),
        source="ROMMA",
    )
    test_db.add(observation)
    await test_db.commit()

    pairs = await matching_service.match_forecasts_to_observations(
        db=test_db,
        site_id=ref_data["site"].id,
        start_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 15, 23, 59, tzinfo=timezone.utc),
    )

    assert len(pairs) == 0


# =============================================================================
# Test: Multiple Observations (AC7)
# =============================================================================


@pytest.mark.asyncio
async def test_multiple_observations_select_closest(
    test_db: AsyncSession,
    matching_service: MatchingService,
    sample_forecast: Forecast,
    setup_reference_data: dict,
):
    """Test multiple observations within tolerance - select closest (3.4)."""
    ref_data = setup_reference_data

    # Create observation 10 minutes before valid_time
    obs_10min = Observation(
        site_id=ref_data["site"].id,
        parameter_id=ref_data["parameter"].id,
        observation_time=datetime(2026, 1, 15, 11, 50, tzinfo=timezone.utc),
        value=Decimal("21.00"),
        source="ROMMA",
    )
    test_db.add(obs_10min)

    # Create observation 5 minutes before valid_time (CLOSEST)
    obs_5min = Observation(
        site_id=ref_data["site"].id,
        parameter_id=ref_data["parameter"].id,
        observation_time=datetime(2026, 1, 15, 11, 55, tzinfo=timezone.utc),
        value=Decimal("22.00"),
        source="FFVL",
    )
    test_db.add(obs_5min)

    # Create observation 15 minutes after valid_time
    obs_15min = Observation(
        site_id=ref_data["site"].id,
        parameter_id=ref_data["parameter"].id,
        observation_time=datetime(2026, 1, 15, 12, 15, tzinfo=timezone.utc),
        value=Decimal("23.00"),
        source="ROMMA",
    )
    test_db.add(obs_15min)

    await test_db.commit()
    await test_db.refresh(obs_5min)

    pairs = await matching_service.match_forecasts_to_observations(
        db=test_db,
        site_id=ref_data["site"].id,
        start_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 15, 23, 59, tzinfo=timezone.utc),
    )

    # Should match with closest observation (5 min before)
    assert len(pairs) == 1
    assert pairs[0].observation_id == obs_5min.id
    assert pairs[0].observed_value == Decimal("22.00")
    assert pairs[0].time_diff_minutes == 5


# =============================================================================
# Test: Missing Observation (3.5)
# =============================================================================


@pytest.mark.asyncio
async def test_missing_observation_no_pair(
    test_db: AsyncSession,
    matching_service: MatchingService,
    sample_forecast: Forecast,
    setup_reference_data: dict,
):
    """Test no pair created when observation is missing (3.5)."""
    ref_data = setup_reference_data

    # Don't create any observation - forecast should remain unmatched
    pairs = await matching_service.match_forecasts_to_observations(
        db=test_db,
        site_id=ref_data["site"].id,
        start_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 15, 23, 59, tzinfo=timezone.utc),
    )

    assert len(pairs) == 0


# =============================================================================
# Test: Multiple Forecasts (3.6)
# =============================================================================


@pytest.mark.asyncio
async def test_multiple_forecasts_all_matched(
    test_db: AsyncSession,
    matching_service: MatchingService,
    setup_reference_data: dict,
):
    """Test multiple forecasts for same valid_time - all matched (3.6)."""
    ref_data = setup_reference_data

    # Create second model
    model2 = Model(
        name="Meteo-Parapente",
        source="Meteo-Parapente forecast model",
    )
    test_db.add(model2)
    await test_db.commit()
    await test_db.refresh(model2)

    valid_time = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

    # Create forecast from AROME
    forecast1 = Forecast(
        site_id=ref_data["site"].id,
        model_id=ref_data["model"].id,
        parameter_id=ref_data["parameter"].id,
        forecast_run=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        valid_time=valid_time,
        value=Decimal("25.00"),
    )
    test_db.add(forecast1)

    # Create forecast from Meteo-Parapente
    forecast2 = Forecast(
        site_id=ref_data["site"].id,
        model_id=model2.id,
        parameter_id=ref_data["parameter"].id,
        forecast_run=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        valid_time=valid_time,
        value=Decimal("27.00"),
    )
    test_db.add(forecast2)

    # Create single observation
    observation = Observation(
        site_id=ref_data["site"].id,
        parameter_id=ref_data["parameter"].id,
        observation_time=valid_time,
        value=Decimal("24.00"),
        source="ROMMA",
    )
    test_db.add(observation)

    await test_db.commit()

    pairs = await matching_service.match_forecasts_to_observations(
        db=test_db,
        site_id=ref_data["site"].id,
        start_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 15, 23, 59, tzinfo=timezone.utc),
    )

    # Both forecasts should be matched
    assert len(pairs) == 2

    # Verify both models are represented
    model_ids = {pair.model_id for pair in pairs}
    assert ref_data["model"].id in model_ids
    assert model2.id in model_ids

    # Verify values
    for pair in pairs:
        assert pair.observed_value == Decimal("24.00")


# =============================================================================
# Test: Horizon Calculation (3.7)
# =============================================================================


@pytest.mark.asyncio
async def test_horizon_calculation_various(
    test_db: AsyncSession,
    matching_service: MatchingService,
    setup_reference_data: dict,
):
    """Test horizon calculation for 6h, 12h, 24h, 48h forecasts (3.7)."""
    ref_data = setup_reference_data
    base_run = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)

    # Create forecasts with different horizons
    horizons_to_test = [6, 12, 24, 48]

    for hours in horizons_to_test:
        valid_time = base_run + timedelta(hours=hours)

        forecast = Forecast(
            site_id=ref_data["site"].id,
            model_id=ref_data["model"].id,
            parameter_id=ref_data["parameter"].id,
            forecast_run=base_run,
            valid_time=valid_time,
            value=Decimal("25.00"),
        )
        test_db.add(forecast)

        observation = Observation(
            site_id=ref_data["site"].id,
            parameter_id=ref_data["parameter"].id,
            observation_time=valid_time,
            value=Decimal("24.00"),
            source=f"TEST_{hours}h",
        )
        test_db.add(observation)

    await test_db.commit()

    pairs = await matching_service.match_forecasts_to_observations(
        db=test_db,
        site_id=ref_data["site"].id,
        start_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 17, 23, 59, tzinfo=timezone.utc),
    )

    assert len(pairs) == 4

    # Verify each horizon is correct
    pair_horizons = {pair.horizon for pair in pairs}
    assert pair_horizons == {6, 12, 24, 48}


# =============================================================================
# Test: Idempotency (AC8, 3.8)
# =============================================================================


@pytest.mark.asyncio
async def test_idempotency_no_duplicates(
    test_db: AsyncSession,
    matching_service: MatchingService,
    sample_forecast: Forecast,
    sample_observation: Observation,
    setup_reference_data: dict,
):
    """Test re-running matching doesn't create duplicates (3.8)."""
    ref_data = setup_reference_data
    date_range = (
        datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 15, 23, 59, tzinfo=timezone.utc),
    )

    # First run
    pairs1 = await matching_service.match_forecasts_to_observations(
        db=test_db,
        site_id=ref_data["site"].id,
        start_date=date_range[0],
        end_date=date_range[1],
    )
    assert len(pairs1) == 1

    # Second run (should not create duplicates)
    pairs2 = await matching_service.match_forecasts_to_observations(
        db=test_db,
        site_id=ref_data["site"].id,
        start_date=date_range[0],
        end_date=date_range[1],
    )

    # Should return 0 new pairs (already exists)
    assert len(pairs2) == 0

    # Verify only one pair exists in database
    result = await test_db.execute(select(ForecastObservationPair))
    all_pairs = result.scalars().all()
    assert len(all_pairs) == 1


# =============================================================================
# Test: Parameter Matching (AC3)
# =============================================================================


@pytest.mark.asyncio
async def test_parameter_mismatch_no_match(
    test_db: AsyncSession,
    matching_service: MatchingService,
    setup_reference_data: dict,
):
    """Test that different parameters don't match."""
    ref_data = setup_reference_data

    # Create another parameter
    param2 = Parameter(
        name="Temperature",
        unit="°C",
    )
    test_db.add(param2)
    await test_db.commit()
    await test_db.refresh(param2)

    # Create forecast for Wind Speed
    forecast = Forecast(
        site_id=ref_data["site"].id,
        model_id=ref_data["model"].id,
        parameter_id=ref_data["parameter"].id,  # Wind Speed
        forecast_run=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        valid_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        value=Decimal("25.00"),
    )
    test_db.add(forecast)

    # Create observation for Temperature (different parameter)
    observation = Observation(
        site_id=ref_data["site"].id,
        parameter_id=param2.id,  # Temperature
        observation_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        value=Decimal("15.00"),
        source="ROMMA",
    )
    test_db.add(observation)

    await test_db.commit()

    pairs = await matching_service.match_forecasts_to_observations(
        db=test_db,
        site_id=ref_data["site"].id,
        start_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 15, 23, 59, tzinfo=timezone.utc),
    )

    # No match because parameter_id differs
    assert len(pairs) == 0


# =============================================================================
# Test: Site Matching (AC2)
# =============================================================================


@pytest.mark.asyncio
async def test_site_mismatch_no_match(
    test_db: AsyncSession,
    matching_service: MatchingService,
    setup_reference_data: dict,
):
    """Test that different sites don't match."""
    ref_data = setup_reference_data

    # Create another site
    site2 = Site(
        name="Other Site",
        latitude=Decimal("46.000000"),
        longitude=Decimal("7.000000"),
        altitude=1500,
    )
    test_db.add(site2)
    await test_db.commit()
    await test_db.refresh(site2)

    # Create forecast for site 1
    forecast = Forecast(
        site_id=ref_data["site"].id,
        model_id=ref_data["model"].id,
        parameter_id=ref_data["parameter"].id,
        forecast_run=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        valid_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        value=Decimal("25.00"),
    )
    test_db.add(forecast)

    # Create observation for site 2 (different site)
    observation = Observation(
        site_id=site2.id,
        parameter_id=ref_data["parameter"].id,
        observation_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        value=Decimal("22.00"),
        source="ROMMA",
    )
    test_db.add(observation)

    await test_db.commit()

    pairs = await matching_service.match_forecasts_to_observations(
        db=test_db,
        site_id=ref_data["site"].id,
        start_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 15, 23, 59, tzinfo=timezone.utc),
    )

    # No match because site_id differs
    assert len(pairs) == 0


# =============================================================================
# Test: Batch Processing
# =============================================================================


@pytest.mark.asyncio
async def test_batch_processing_many_forecasts(
    test_db: AsyncSession,
    matching_service: MatchingService,
    setup_reference_data: dict,
):
    """Test batch processing with many forecasts."""
    ref_data = setup_reference_data
    base_run = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)

    # Create 50 forecasts with matching observations
    for i in range(50):
        valid_time = base_run + timedelta(hours=i)

        forecast = Forecast(
            site_id=ref_data["site"].id,
            model_id=ref_data["model"].id,
            parameter_id=ref_data["parameter"].id,
            forecast_run=base_run,
            valid_time=valid_time,
            value=Decimal("25.00") + Decimal(i),
        )
        test_db.add(forecast)

        observation = Observation(
            site_id=ref_data["site"].id,
            parameter_id=ref_data["parameter"].id,
            observation_time=valid_time,
            value=Decimal("24.00") + Decimal(i),
            source=f"BATCH_{i}",
        )
        test_db.add(observation)

    await test_db.commit()

    pairs = await matching_service.match_forecasts_to_observations(
        db=test_db,
        site_id=ref_data["site"].id,
        start_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 17, 23, 59, tzinfo=timezone.utc),
    )

    assert len(pairs) == 50


# =============================================================================
# Test: Input Validation (Code Review Fixes)
# =============================================================================


@pytest.mark.asyncio
async def test_invalid_site_id_raises_error(
    test_db: AsyncSession,
    matching_service: MatchingService,
):
    """Test that invalid site_id raises ValueError."""
    with pytest.raises(ValueError, match="site_id must be positive"):
        await matching_service.match_forecasts_to_observations(
            db=test_db,
            site_id=0,
            start_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 15, 23, 59, tzinfo=timezone.utc),
        )

    with pytest.raises(ValueError, match="site_id must be positive"):
        await matching_service.match_forecasts_to_observations(
            db=test_db,
            site_id=-1,
            start_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 15, 23, 59, tzinfo=timezone.utc),
        )


@pytest.mark.asyncio
async def test_invalid_date_range_raises_error(
    test_db: AsyncSession,
    matching_service: MatchingService,
):
    """Test that start_date >= end_date raises ValueError."""
    # start_date == end_date
    with pytest.raises(ValueError, match="start_date must be before end_date"):
        await matching_service.match_forecasts_to_observations(
            db=test_db,
            site_id=1,
            start_date=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        )

    # start_date > end_date
    with pytest.raises(ValueError, match="start_date must be before end_date"):
        await matching_service.match_forecasts_to_observations(
            db=test_db,
            site_id=1,
            start_date=datetime(2026, 1, 16, 0, 0, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        )
