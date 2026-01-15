"""TDD tests for MetricsService.

Tests written FIRST following Red-Green-Refactor cycle.
These tests define the expected behavior for accuracy metrics calculation.

Test Coverage:
- AC1: MAE Calculation - mean(abs(deviation))
- AC2: Bias Calculation - mean(deviation), positive = underestimate
- AC3: Confidence Intervals - 95% CI using scipy t-distribution
- AC4: Standard Deviation - stddev(deviation)
- AC5: Sample Size Tracking
- AC6: Confidence Levels - insufficient (<30), preliminary (30-90), validated (>=90)
- AC7: Min/Max Deviations
- AC8: Persistence with UNIQUE constraint (upsert)
- AC9: >80% test coverage
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch

from core.models import (
    AccuracyMetric,
    Deviation,
    Model,
    Parameter,
    Site,
)
from services import normalize_datetime_for_db


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def metrics_service():
    """Create MetricsService instance for testing."""
    from services.metrics_service import MetricsService
    return MetricsService()


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
async def sample_deviations(
    test_db: AsyncSession,
    sample_site: Site,
    sample_model: Model,
    wind_speed_param: Parameter,
) -> List[Deviation]:
    """Create sample deviations for metrics testing.

    Creates 5 deviations: [2.0, -1.0, 3.0, -2.0, 1.0]
    Expected MAE = mean(|2|, |-1|, |3|, |-2|, |1|) = mean(2, 1, 3, 2, 1) = 9/5 = 1.8
    Expected bias = mean(2, -1, 3, -2, 1) = 3/5 = 0.6
    """
    base_time = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
    deviation_values = [
        Decimal("2.0"),
        Decimal("-1.0"),
        Decimal("3.0"),
        Decimal("-2.0"),
        Decimal("1.0"),
    ]

    deviations = []
    for i, dev_value in enumerate(deviation_values):
        ts = normalize_datetime_for_db(base_time + timedelta(hours=i))
        deviation = Deviation(
            timestamp=ts,
            site_id=sample_site.id,
            model_id=sample_model.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
            forecast_value=Decimal("20.0"),
            observed_value=Decimal("20.0") + dev_value,
            deviation=dev_value,
        )
        test_db.add(deviation)
        deviations.append(deviation)

    await test_db.commit()
    return deviations


@pytest_asyncio.fixture
async def large_sample_deviations(
    test_db: AsyncSession,
    sample_site: Site,
    sample_model: Model,
    wind_speed_param: Parameter,
) -> List[Deviation]:
    """Create 100 deviations for validated confidence level testing."""
    base_time = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    deviations = []

    for i in range(100):
        # Alternate between positive and negative deviations
        dev_value = Decimal(str((i % 10) - 5))  # Values from -5 to 4
        ts = normalize_datetime_for_db(base_time + timedelta(hours=i))
        deviation = Deviation(
            timestamp=ts,
            site_id=sample_site.id,
            model_id=sample_model.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
            forecast_value=Decimal("20.0"),
            observed_value=Decimal("20.0") + dev_value,
            deviation=dev_value,
        )
        test_db.add(deviation)
        deviations.append(deviation)

    await test_db.commit()
    return deviations


# =============================================================================
# Task 2.2: Test MAE calculation accuracy (AC1)
# =============================================================================


class TestMAECalculation:
    """Tests for Mean Absolute Error calculation: MAE = mean(abs(deviation))."""

    @pytest.mark.asyncio
    async def test_mae_calculation_correct(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_deviations: List[Deviation],
        metrics_service,
    ):
        """Test MAE calculation with sample deviations (AC1).

        Deviations: [2.0, -1.0, 3.0, -2.0, 1.0]
        MAE = mean(|2|, |-1|, |3|, |-2|, |1|) = mean(2, 1, 3, 2, 1) = 9/5 = 1.8
        """
        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        assert metrics.mae == Decimal("1.8")

    @pytest.mark.asyncio
    async def test_mae_always_positive(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        metrics_service,
    ):
        """Test MAE is always positive (absolute values) (AC1)."""
        # Create all negative deviations
        base_time = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
        for i in range(5):
            ts = normalize_datetime_for_db(base_time + timedelta(hours=i))
            deviation = Deviation(
                timestamp=ts,
                site_id=sample_site.id,
                model_id=sample_model.id,
                parameter_id=wind_speed_param.id,
                horizon=12,
                forecast_value=Decimal("25.0"),
                observed_value=Decimal("20.0"),
                deviation=Decimal("-5.0"),  # All negative
            )
            test_db.add(deviation)
        await test_db.commit()

        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        assert metrics.mae > 0, "MAE should always be positive"
        assert metrics.mae == Decimal("5.0")  # mean(|-5|, |-5|, |-5|, |-5|, |-5|) = 5


# =============================================================================
# Task 2.3: Test bias calculation (AC2)
# =============================================================================


class TestBiasCalculation:
    """Tests for bias calculation: bias = mean(deviation)."""

    @pytest.mark.asyncio
    async def test_bias_calculation_correct(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_deviations: List[Deviation],
        metrics_service,
    ):
        """Test bias calculation with sample deviations (AC2).

        Deviations: [2.0, -1.0, 3.0, -2.0, 1.0]
        Bias = mean(2, -1, 3, -2, 1) = 3/5 = 0.6
        """
        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        assert metrics.bias == Decimal("0.6")

    @pytest.mark.asyncio
    async def test_positive_bias_indicates_underestimate(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        metrics_service,
    ):
        """Test positive bias = model underestimates (AC2).

        When observed > forecast, deviation is positive.
        Positive mean deviation = systematic underestimate.
        """
        base_time = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
        # All positive deviations (observed > forecast)
        for i in range(5):
            ts = normalize_datetime_for_db(base_time + timedelta(hours=i))
            deviation = Deviation(
                timestamp=ts,
                site_id=sample_site.id,
                model_id=sample_model.id,
                parameter_id=wind_speed_param.id,
                horizon=12,
                forecast_value=Decimal("20.0"),
                observed_value=Decimal("25.0"),
                deviation=Decimal("5.0"),  # observed - forecast = positive
            )
            test_db.add(deviation)
        await test_db.commit()

        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        assert metrics.bias > 0, "Positive bias indicates underestimate"

    @pytest.mark.asyncio
    async def test_negative_bias_indicates_overestimate(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        metrics_service,
    ):
        """Test negative bias = model overestimates (AC2).

        When observed < forecast, deviation is negative.
        Negative mean deviation = systematic overestimate.
        """
        base_time = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
        # All negative deviations (observed < forecast)
        for i in range(5):
            ts = normalize_datetime_for_db(base_time + timedelta(hours=i))
            deviation = Deviation(
                timestamp=ts,
                site_id=sample_site.id,
                model_id=sample_model.id,
                parameter_id=wind_speed_param.id,
                horizon=12,
                forecast_value=Decimal("30.0"),
                observed_value=Decimal("25.0"),
                deviation=Decimal("-5.0"),  # observed - forecast = negative
            )
            test_db.add(deviation)
        await test_db.commit()

        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        assert metrics.bias < 0, "Negative bias indicates overestimate"


# =============================================================================
# Task 2.4: Test confidence interval calculation (AC3)
# =============================================================================


class TestConfidenceIntervalCalculation:
    """Tests for 95% confidence interval using scipy t-distribution."""

    def test_confidence_interval_basic(self, metrics_service):
        """Test CI calculation with known values (AC3)."""
        # With bias=0, std_dev=1, sample_size=10
        # SE = 1 / sqrt(10) ≈ 0.316
        # t_stat for 95% CI with df=9 ≈ 2.262
        # margin ≈ 2.262 * 0.316 ≈ 0.715
        ci_lower, ci_upper = metrics_service.calculate_confidence_interval(
            bias=0.0,
            std_dev=1.0,
            sample_size=10,
            confidence=0.95,
        )

        assert ci_lower < 0, "CI lower should be negative when bias=0"
        assert ci_upper > 0, "CI upper should be positive when bias=0"
        assert abs(ci_lower) == pytest.approx(abs(ci_upper), rel=0.01), "CI should be symmetric around bias=0"

    def test_confidence_interval_single_sample(self, metrics_service):
        """Test CI with single sample returns (bias, bias) (AC3 edge case)."""
        ci_lower, ci_upper = metrics_service.calculate_confidence_interval(
            bias=5.0,
            std_dev=0.0,
            sample_size=1,
        )

        assert ci_lower == 5.0
        assert ci_upper == 5.0

    def test_confidence_interval_zero_std_dev(self, metrics_service):
        """Test CI with zero std_dev returns (bias, bias) (AC3 edge case)."""
        ci_lower, ci_upper = metrics_service.calculate_confidence_interval(
            bias=3.5,
            std_dev=0.0,
            sample_size=50,
        )

        assert ci_lower == 3.5
        assert ci_upper == 3.5

    def test_confidence_interval_wider_with_smaller_sample(self, metrics_service):
        """Test CI gets wider with smaller sample size (AC3)."""
        # Same bias and std_dev, different sample sizes
        ci_small_lower, ci_small_upper = metrics_service.calculate_confidence_interval(
            bias=1.0,
            std_dev=2.0,
            sample_size=10,
        )
        ci_large_lower, ci_large_upper = metrics_service.calculate_confidence_interval(
            bias=1.0,
            std_dev=2.0,
            sample_size=100,
        )

        small_width = ci_small_upper - ci_small_lower
        large_width = ci_large_upper - ci_large_lower

        assert small_width > large_width, "CI should be wider with smaller sample"


# =============================================================================
# Task 2.5: Test confidence level thresholds (AC6)
# =============================================================================


class TestConfidenceLevelThresholds:
    """Tests for confidence level determination based on sample size."""

    def test_insufficient_below_30(self, metrics_service):
        """Test sample_size < 30 = 'insufficient' (AC6)."""
        assert metrics_service.determine_confidence_level(29) == "insufficient"
        assert metrics_service.determine_confidence_level(1) == "insufficient"
        assert metrics_service.determine_confidence_level(15) == "insufficient"

    def test_preliminary_30_to_89(self, metrics_service):
        """Test sample_size 30-89 = 'preliminary' (AC6)."""
        assert metrics_service.determine_confidence_level(30) == "preliminary"
        assert metrics_service.determine_confidence_level(31) == "preliminary"
        assert metrics_service.determine_confidence_level(60) == "preliminary"
        assert metrics_service.determine_confidence_level(89) == "preliminary"

    def test_validated_90_or_more(self, metrics_service):
        """Test sample_size >= 90 = 'validated' (AC6)."""
        assert metrics_service.determine_confidence_level(90) == "validated"
        assert metrics_service.determine_confidence_level(91) == "validated"
        assert metrics_service.determine_confidence_level(100) == "validated"
        assert metrics_service.determine_confidence_level(1000) == "validated"

    @pytest.mark.asyncio
    async def test_metrics_with_insufficient_data(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_deviations: List[Deviation],  # 5 samples
        metrics_service,
    ):
        """Test metrics calculation returns 'insufficient' for <30 samples (AC6)."""
        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        assert metrics.sample_size == 5
        assert metrics.confidence_level == "insufficient"

    @pytest.mark.asyncio
    async def test_metrics_with_validated_data(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        large_sample_deviations: List[Deviation],  # 100 samples
        metrics_service,
    ):
        """Test metrics calculation returns 'validated' for >=90 samples (AC6)."""
        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        assert metrics.sample_size == 100
        assert metrics.confidence_level == "validated"


# =============================================================================
# Task 2.6: Test edge case - single sample (AC4)
# =============================================================================


class TestSingleSampleEdgeCase:
    """Tests for edge case with single deviation sample."""

    @pytest.mark.asyncio
    async def test_single_sample_std_dev_zero(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        metrics_service,
    ):
        """Test std_dev = 0 with single sample (AC4 edge case)."""
        # Create single deviation
        ts = normalize_datetime_for_db(datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc))
        deviation = Deviation(
            timestamp=ts,
            site_id=sample_site.id,
            model_id=sample_model.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
            forecast_value=Decimal("20.0"),
            observed_value=Decimal("25.0"),
            deviation=Decimal("5.0"),
        )
        test_db.add(deviation)
        await test_db.commit()

        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        assert metrics.sample_size == 1
        assert metrics.std_dev == Decimal("0")
        assert metrics.ci_lower == metrics.ci_upper == metrics.bias


# =============================================================================
# Task 2.7: Test edge case - all deviations identical (AC4)
# =============================================================================


class TestIdenticalDeviationsEdgeCase:
    """Tests for edge case with all identical deviations."""

    @pytest.mark.asyncio
    async def test_identical_deviations_std_dev_zero(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        metrics_service,
    ):
        """Test std_dev = 0 when all deviations are identical (AC4 edge case)."""
        base_time = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
        # Create 10 identical deviations
        for i in range(10):
            ts = normalize_datetime_for_db(base_time + timedelta(hours=i))
            deviation = Deviation(
                timestamp=ts,
                site_id=sample_site.id,
                model_id=sample_model.id,
                parameter_id=wind_speed_param.id,
                horizon=12,
                forecast_value=Decimal("20.0"),
                observed_value=Decimal("23.0"),
                deviation=Decimal("3.0"),  # All identical
            )
            test_db.add(deviation)
        await test_db.commit()

        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        assert metrics.sample_size == 10
        assert metrics.mae == Decimal("3.0")
        assert metrics.bias == Decimal("3.0")
        assert metrics.std_dev == Decimal("0")
        assert metrics.ci_lower == metrics.ci_upper == metrics.bias


# =============================================================================
# Task 2.8: Test idempotency - re-running updates, doesn't duplicate (AC8)
# =============================================================================


class TestIdempotency:
    """Tests for idempotent metrics persistence (upsert behavior)."""

    @pytest.mark.asyncio
    async def test_save_metrics_creates_new_record(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_deviations: List[Deviation],
        metrics_service,
    ):
        """Test save_metrics creates new record when none exists (AC8)."""
        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        await metrics_service.save_metrics(db=test_db, metrics=metrics)

        # Verify record was created
        result = await test_db.execute(select(AccuracyMetric))
        records = result.scalars().all()
        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_save_metrics_updates_existing_record(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_deviations: List[Deviation],
        metrics_service,
    ):
        """Test save_metrics updates existing record (upsert) (AC8)."""
        # First calculation and save
        metrics1 = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )
        await metrics_service.save_metrics(db=test_db, metrics=metrics1)

        # Add more deviations
        base_time = datetime(2026, 1, 16, 0, 0, tzinfo=timezone.utc)
        for i in range(5):
            ts = normalize_datetime_for_db(base_time + timedelta(hours=i))
            deviation = Deviation(
                timestamp=ts,
                site_id=sample_site.id,
                model_id=sample_model.id,
                parameter_id=wind_speed_param.id,
                horizon=12,
                forecast_value=Decimal("20.0"),
                observed_value=Decimal("30.0"),
                deviation=Decimal("10.0"),
            )
            test_db.add(deviation)
        await test_db.commit()

        # Second calculation and save (should update, not create duplicate)
        metrics2 = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )
        await metrics_service.save_metrics(db=test_db, metrics=metrics2)

        # Verify only one record exists
        result = await test_db.execute(select(AccuracyMetric))
        records = result.scalars().all()
        assert len(records) == 1

        # Verify values were updated
        assert records[0].sample_size == 10  # 5 + 5
        assert records[0].mae != metrics1.mae  # Should have changed

    @pytest.mark.asyncio
    async def test_save_metrics_postgresql_path(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_deviations: List[Deviation],
        metrics_service,
    ):
        """Test save_metrics PostgreSQL upsert path (mocked dialect)."""
        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        # Mock the database bind to simulate PostgreSQL dialect
        mock_dialect = MagicMock()
        mock_dialect.name = "postgresql"
        mock_bind = MagicMock()
        mock_bind.dialect = mock_dialect

        # Create a mock session that tracks execute calls
        original_bind = test_db.bind
        test_db.bind = mock_bind

        # Mock execute to capture the statement
        execute_calls = []
        original_execute = test_db.execute

        async def mock_execute(stmt, *args, **kwargs):
            execute_calls.append(stmt)
            # For PostgreSQL INSERT, we need to actually execute on SQLite
            # Just verify the statement structure
            return MagicMock()

        test_db.execute = mock_execute
        test_db.commit = AsyncMock()

        try:
            await metrics_service.save_metrics(db=test_db, metrics=metrics)

            # Verify PostgreSQL INSERT was attempted
            assert len(execute_calls) == 1
            # The statement should be a PostgreSQL insert
            stmt = execute_calls[0]
            assert "accuracy_metrics" in str(stmt)
        finally:
            # Restore original bind and execute
            test_db.bind = original_bind
            test_db.execute = original_execute


# =============================================================================
# Task 2.9: Test input validation
# =============================================================================


class TestInputValidation:
    """Tests for input validation in MetricsService."""

    @pytest.mark.asyncio
    async def test_no_deviations_raises_value_error(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        metrics_service,
    ):
        """Test ValueError raised when no deviations found."""
        with pytest.raises(ValueError, match="No deviations found"):
            await metrics_service.calculate_accuracy_metrics(
                db=test_db,
                model_id=sample_model.id,
                site_id=sample_site.id,
                parameter_id=wind_speed_param.id,
                horizon=12,
            )

    @pytest.mark.asyncio
    async def test_invalid_model_id_raises_value_error(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        wind_speed_param: Parameter,
        metrics_service,
    ):
        """Test ValueError raised for invalid model_id."""
        with pytest.raises(ValueError, match="model_id must be positive"):
            await metrics_service.calculate_accuracy_metrics(
                db=test_db,
                model_id=-1,
                site_id=sample_site.id,
                parameter_id=wind_speed_param.id,
                horizon=12,
            )

    @pytest.mark.asyncio
    async def test_invalid_site_id_raises_value_error(
        self,
        test_db: AsyncSession,
        sample_model: Model,
        wind_speed_param: Parameter,
        metrics_service,
    ):
        """Test ValueError raised for invalid site_id."""
        with pytest.raises(ValueError, match="site_id must be positive"):
            await metrics_service.calculate_accuracy_metrics(
                db=test_db,
                model_id=sample_model.id,
                site_id=0,
                parameter_id=wind_speed_param.id,
                horizon=12,
            )

    @pytest.mark.asyncio
    async def test_invalid_parameter_id_raises_value_error(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        metrics_service,
    ):
        """Test ValueError raised for invalid parameter_id."""
        with pytest.raises(ValueError, match="parameter_id must be positive"):
            await metrics_service.calculate_accuracy_metrics(
                db=test_db,
                model_id=sample_model.id,
                site_id=sample_site.id,
                parameter_id=-1,
                horizon=12,
            )

    @pytest.mark.asyncio
    async def test_invalid_horizon_raises_value_error(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        metrics_service,
    ):
        """Test ValueError raised for negative horizon."""
        with pytest.raises(ValueError, match="horizon must be non-negative"):
            await metrics_service.calculate_accuracy_metrics(
                db=test_db,
                model_id=sample_model.id,
                site_id=sample_site.id,
                parameter_id=wind_speed_param.id,
                horizon=-1,
            )


# =============================================================================
# Test Min/Max Deviations (AC7)
# =============================================================================


class TestMinMaxDeviations:
    """Tests for min/max deviation tracking."""

    @pytest.mark.asyncio
    async def test_min_max_deviations_correct(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_deviations: List[Deviation],
        metrics_service,
    ):
        """Test min/max deviation values are tracked correctly (AC7).

        Deviations: [2.0, -1.0, 3.0, -2.0, 1.0]
        Min = -2.0, Max = 3.0
        """
        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        assert metrics.min_deviation == Decimal("-2.0")
        assert metrics.max_deviation == Decimal("3.0")


# =============================================================================
# Test Standard Deviation (AC4)
# =============================================================================


class TestStandardDeviation:
    """Tests for standard deviation calculation."""

    @pytest.mark.asyncio
    async def test_std_dev_calculation(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_deviations: List[Deviation],
        metrics_service,
    ):
        """Test standard deviation calculation (AC4).

        Deviations: [2.0, -1.0, 3.0, -2.0, 1.0]
        Mean = 0.6
        Variance = ((2-0.6)^2 + (-1-0.6)^2 + (3-0.6)^2 + (-2-0.6)^2 + (1-0.6)^2) / (5-1)
                 = (1.96 + 2.56 + 5.76 + 6.76 + 0.16) / 4
                 = 17.2 / 4 = 4.3
        Std Dev = sqrt(4.3) ≈ 2.074
        """
        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        # SQLite and PostgreSQL may have slightly different precision
        assert float(metrics.std_dev) == pytest.approx(2.074, rel=0.01)


# =============================================================================
# Test Sample Size Tracking (AC5)
# =============================================================================


class TestSampleSizeTracking:
    """Tests for sample size tracking."""

    @pytest.mark.asyncio
    async def test_sample_size_correct(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_deviations: List[Deviation],
        metrics_service,
    ):
        """Test sample size is tracked correctly (AC5)."""
        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        assert metrics.sample_size == 5  # 5 deviations in sample_deviations fixture


# =============================================================================
# Integration Test: Full workflow
# =============================================================================


class TestMetricsServiceIntegration:
    """Integration tests for complete metrics calculation workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow_calculate_and_save(
        self,
        test_db: AsyncSession,
        sample_site: Site,
        sample_model: Model,
        wind_speed_param: Parameter,
        sample_deviations: List[Deviation],
        metrics_service,
    ):
        """Test complete workflow: calculate metrics → save to database."""
        # Calculate metrics
        metrics = await metrics_service.calculate_accuracy_metrics(
            db=test_db,
            model_id=sample_model.id,
            site_id=sample_site.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
        )

        # Verify calculated values
        assert metrics.model_id == sample_model.id
        assert metrics.site_id == sample_site.id
        assert metrics.parameter_id == wind_speed_param.id
        assert metrics.horizon == 12
        assert metrics.mae == Decimal("1.8")
        assert metrics.bias == Decimal("0.6")
        assert metrics.sample_size == 5
        assert metrics.confidence_level == "insufficient"
        assert metrics.min_deviation == Decimal("-2.0")
        assert metrics.max_deviation == Decimal("3.0")

        # Save metrics
        await metrics_service.save_metrics(db=test_db, metrics=metrics)

        # Verify saved to database
        result = await test_db.execute(
            select(AccuracyMetric).where(
                AccuracyMetric.model_id == sample_model.id,
                AccuracyMetric.site_id == sample_site.id,
                AccuracyMetric.parameter_id == wind_speed_param.id,
                AccuracyMetric.horizon == 12,
            )
        )
        saved = result.scalar_one()

        assert saved.mae == Decimal("1.8")
        assert saved.bias == Decimal("0.6")
        assert saved.sample_size == 5
        assert saved.confidence_level == "insufficient"
