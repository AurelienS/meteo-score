"""Tests for AggregateService and TimescaleDB continuous aggregates.

These tests verify the AggregateService functionality. Since continuous
aggregates are TimescaleDB-specific, most tests use mocking to verify
logic without requiring a PostgreSQL database.

Integration tests with actual TimescaleDB should be run separately
with a PostgreSQL database.
"""

import os
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from services.aggregate_service import AggregateMetrics, AggregateService


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def aggregate_service():
    """Create AggregateService instance for testing."""
    return AggregateService()


@pytest.fixture
def mock_postgresql_session():
    """Create a mock session that simulates PostgreSQL with TimescaleDB."""
    session = MagicMock(spec=AsyncSession)
    session.bind = MagicMock()
    session.bind.dialect.name = "postgresql"

    # Mock execute to return TimescaleDB exists
    async def mock_execute(query, params=None):
        query_str = str(query)
        if "pg_extension" in query_str:
            result = MagicMock()
            result.scalar.return_value = True
            return result
        return MagicMock()

    session.execute = mock_execute
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_sqlite_session():
    """Create a mock session that simulates SQLite (no TimescaleDB)."""
    session = MagicMock(spec=AsyncSession)
    session.bind = MagicMock()
    session.bind.dialect.name = "sqlite"
    return session


# =============================================================================
# Test TimescaleDB Detection
# =============================================================================


class TestTimescaleDBDetection:
    """Tests for TimescaleDB availability detection."""

    @pytest.mark.asyncio
    async def test_check_timescaledb_returns_false_for_sqlite(
        self,
        mock_sqlite_session,
        aggregate_service,
    ):
        """Test _check_timescaledb returns False for SQLite."""
        result = await aggregate_service._check_timescaledb(mock_sqlite_session)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_timescaledb_returns_true_for_postgresql(
        self,
        mock_postgresql_session,
        aggregate_service,
    ):
        """Test _check_timescaledb returns True for PostgreSQL with TimescaleDB."""
        result = await aggregate_service._check_timescaledb(mock_postgresql_session)
        assert result is True

    @pytest.mark.asyncio
    async def test_ensure_timescaledb_raises_for_sqlite(
        self,
        mock_sqlite_session,
        aggregate_service,
    ):
        """Test _ensure_timescaledb raises RuntimeError for SQLite."""
        with pytest.raises(RuntimeError, match="TimescaleDB extension required"):
            await aggregate_service._ensure_timescaledb(mock_sqlite_session)


# =============================================================================
# Test Query Methods with Mock
# =============================================================================


class TestQueryMethods:
    """Tests for query methods using mocks."""

    @pytest.mark.asyncio
    async def test_query_daily_metrics_raises_without_timescaledb(
        self,
        mock_sqlite_session,
        aggregate_service,
    ):
        """Test query_daily_metrics raises RuntimeError without TimescaleDB."""
        with pytest.raises(RuntimeError, match="TimescaleDB extension required"):
            await aggregate_service.query_daily_metrics(
                db=mock_sqlite_session,
                site_id=1,
            )

    @pytest.mark.asyncio
    async def test_query_weekly_metrics_raises_without_timescaledb(
        self,
        mock_sqlite_session,
        aggregate_service,
    ):
        """Test query_weekly_metrics raises RuntimeError without TimescaleDB."""
        with pytest.raises(RuntimeError, match="TimescaleDB extension required"):
            await aggregate_service.query_weekly_metrics(
                db=mock_sqlite_session,
                site_id=1,
            )

    @pytest.mark.asyncio
    async def test_query_monthly_metrics_raises_without_timescaledb(
        self,
        mock_sqlite_session,
        aggregate_service,
    ):
        """Test query_monthly_metrics raises RuntimeError without TimescaleDB."""
        with pytest.raises(RuntimeError, match="TimescaleDB extension required"):
            await aggregate_service.query_monthly_metrics(
                db=mock_sqlite_session,
                site_id=1,
            )

    @pytest.mark.asyncio
    async def test_query_daily_metrics_builds_correct_query(
        self,
        aggregate_service,
    ):
        """Test query_daily_metrics builds correct SQL query."""
        # Create a mock that captures the executed query
        session = MagicMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.dialect.name = "postgresql"

        executed_queries = []

        async def mock_execute(query, params=None):
            query_str = str(query)
            if "pg_extension" in query_str:
                result = MagicMock()
                result.scalar.return_value = True
                return result
            executed_queries.append((query_str, params))
            result = MagicMock()
            result.fetchall.return_value = []
            return result

        session.execute = mock_execute

        await aggregate_service.query_daily_metrics(
            db=session,
            site_id=1,
            model_id=2,
            parameter_id=3,
            horizon=12,
            limit=50,
        )

        assert len(executed_queries) == 1
        query, params = executed_queries[0]
        assert "daily_accuracy_metrics" in query
        assert params["site_id"] == 1
        assert params["model_id"] == 2
        assert params["parameter_id"] == 3
        assert params["horizon"] == 12
        assert params["limit"] == 50

    @pytest.mark.asyncio
    async def test_query_weekly_metrics_builds_correct_query(
        self,
        aggregate_service,
    ):
        """Test query_weekly_metrics builds correct SQL query with all filters."""
        session = MagicMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.dialect.name = "postgresql"

        executed_queries = []

        async def mock_execute(query, params=None):
            query_str = str(query)
            if "pg_extension" in query_str:
                result = MagicMock()
                result.scalar.return_value = True
                return result
            executed_queries.append((query_str, params))
            result = MagicMock()
            result.fetchall.return_value = []
            return result

        session.execute = mock_execute

        await aggregate_service.query_weekly_metrics(
            db=session,
            site_id=5,
            model_id=10,
        )

        assert len(executed_queries) == 1
        query, params = executed_queries[0]
        assert "weekly_accuracy_metrics" in query
        assert "SELECT" in query
        assert "bucket" in query
        assert params["site_id"] == 5
        assert params["model_id"] == 10

    @pytest.mark.asyncio
    async def test_query_monthly_metrics_builds_correct_query(
        self,
        aggregate_service,
    ):
        """Test query_monthly_metrics builds correct SQL query."""
        session = MagicMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.dialect.name = "postgresql"

        executed_queries = []

        async def mock_execute(query, params=None):
            query_str = str(query)
            if "pg_extension" in query_str:
                result = MagicMock()
                result.scalar.return_value = True
                return result
            executed_queries.append((query_str, params))
            result = MagicMock()
            result.fetchall.return_value = []
            return result

        session.execute = mock_execute

        await aggregate_service.query_monthly_metrics(
            db=session,
            site_id=7,
        )

        assert len(executed_queries) == 1
        query, params = executed_queries[0]
        assert "monthly_accuracy_metrics" in query
        assert params["site_id"] == 7

    @pytest.mark.asyncio
    async def test_query_validates_sql_structure(
        self,
        aggregate_service,
    ):
        """Test query methods build valid SQL with all required columns."""
        session = MagicMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.dialect.name = "postgresql"

        executed_queries = []

        async def mock_execute(query, params=None):
            query_str = str(query)
            if "pg_extension" in query_str:
                result = MagicMock()
                result.scalar.return_value = True
                return result
            executed_queries.append(query_str)
            result = MagicMock()
            result.fetchall.return_value = []
            return result

        session.execute = mock_execute

        await aggregate_service.query_daily_metrics(db=session, site_id=1)

        assert len(executed_queries) == 1
        query = executed_queries[0]
        # Verify all expected columns are in SELECT
        required_columns = ["bucket", "site_id", "model_id", "parameter_id",
                           "horizon", "mae", "bias", "std_dev", "sample_size",
                           "min_deviation", "max_deviation"]
        for col in required_columns:
            assert col in query, f"Missing column {col} in query"
        # Verify proper WHERE and ORDER BY
        assert "WHERE site_id = :site_id" in query
        assert "ORDER BY bucket DESC" in query
        assert "LIMIT :limit" in query


# =============================================================================
# Test Refresh Methods
# =============================================================================


class TestRefreshMethods:
    """Tests for aggregate refresh methods."""

    @pytest.mark.asyncio
    async def test_refresh_aggregate_raises_for_invalid_name(
        self,
        mock_postgresql_session,
        aggregate_service,
    ):
        """Test refresh_aggregate raises ValueError for invalid aggregate name."""
        with pytest.raises(ValueError, match="Invalid aggregate name"):
            await aggregate_service.refresh_aggregate(
                db=mock_postgresql_session,
                aggregate_name="invalid_aggregate",
            )

    @pytest.mark.asyncio
    async def test_refresh_aggregate_accepts_valid_names(
        self,
        aggregate_service,
    ):
        """Test refresh_aggregate accepts valid aggregate names."""
        session = MagicMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.dialect.name = "postgresql"

        executed_queries = []

        async def mock_execute(query, params=None):
            query_str = str(query)
            if "pg_extension" in query_str:
                result = MagicMock()
                result.scalar.return_value = True
                return result
            executed_queries.append(query_str)
            return MagicMock()

        session.execute = mock_execute
        session.commit = AsyncMock()

        # Test each valid aggregate name
        for name in ["daily_accuracy_metrics", "weekly_accuracy_metrics", "monthly_accuracy_metrics"]:
            executed_queries.clear()
            await aggregate_service.refresh_aggregate(db=session, aggregate_name=name)
            assert any("refresh_continuous_aggregate" in q for q in executed_queries)

    @pytest.mark.asyncio
    async def test_refresh_daily_aggregate_calls_refresh(
        self,
        aggregate_service,
    ):
        """Test refresh_daily_aggregate calls the correct refresh."""
        session = MagicMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.dialect.name = "postgresql"

        executed_queries = []

        async def mock_execute(query, params=None):
            query_str = str(query)
            if "pg_extension" in query_str:
                result = MagicMock()
                result.scalar.return_value = True
                return result
            executed_queries.append(query_str)
            return MagicMock()

        session.execute = mock_execute
        session.commit = AsyncMock()

        await aggregate_service.refresh_daily_aggregate(db=session)

        assert any("daily_accuracy_metrics" in q for q in executed_queries)

    @pytest.mark.asyncio
    async def test_refresh_all_aggregates_refreshes_all(
        self,
        aggregate_service,
    ):
        """Test refresh_all_aggregates refreshes all three aggregates."""
        session = MagicMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.dialect.name = "postgresql"

        executed_queries = []

        async def mock_execute(query, params=None):
            query_str = str(query)
            if "pg_extension" in query_str:
                result = MagicMock()
                result.scalar.return_value = True
                return result
            executed_queries.append(query_str)
            return MagicMock()

        session.execute = mock_execute
        session.commit = AsyncMock()

        await aggregate_service.refresh_all_aggregates(db=session)

        # Check all three aggregates were refreshed
        assert any("daily_accuracy_metrics" in q for q in executed_queries)
        assert any("weekly_accuracy_metrics" in q for q in executed_queries)
        assert any("monthly_accuracy_metrics" in q for q in executed_queries)


# =============================================================================
# Test AggregateMetrics Dataclass
# =============================================================================


class TestAggregateMetricsDataclass:
    """Tests for AggregateMetrics dataclass."""

    def test_aggregate_metrics_creation(self):
        """Test AggregateMetrics can be created with all fields."""
        metrics = AggregateMetrics(
            bucket=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
            site_id=1,
            model_id=2,
            parameter_id=3,
            horizon=12,
            mae=Decimal("1.5"),
            bias=Decimal("0.3"),
            std_dev=Decimal("2.1"),
            sample_size=100,
            min_deviation=Decimal("-5.0"),
            max_deviation=Decimal("8.0"),
        )

        assert metrics.site_id == 1
        assert metrics.model_id == 2
        assert metrics.mae == Decimal("1.5")
        assert metrics.sample_size == 100

    def test_aggregate_metrics_with_none_values(self):
        """Test AggregateMetrics handles None for optional fields."""
        metrics = AggregateMetrics(
            bucket=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
            site_id=1,
            model_id=2,
            parameter_id=3,
            horizon=12,
            mae=Decimal("1.5"),
            bias=Decimal("0.3"),
            std_dev=None,  # Can be None for single sample
            sample_size=1,
            min_deviation=None,
            max_deviation=None,
        )

        assert metrics.std_dev is None
        assert metrics.min_deviation is None


# =============================================================================
# Test Get Aggregate Info
# =============================================================================


class TestGetAggregateInfo:
    """Tests for get_aggregate_info method."""

    @pytest.mark.asyncio
    async def test_get_aggregate_info_returns_counts(
        self,
        aggregate_service,
    ):
        """Test get_aggregate_info returns row counts for all aggregates."""
        session = MagicMock(spec=AsyncSession)
        session.bind = MagicMock()
        session.bind.dialect.name = "postgresql"

        count_values = {"daily": 100, "weekly": 20, "monthly": 5}
        call_count = [0]

        async def mock_execute(query, params=None):
            query_str = str(query)
            if "pg_extension" in query_str:
                result = MagicMock()
                result.scalar.return_value = True
                return result
            if "COUNT" in query_str:
                result = MagicMock()
                if "daily" in query_str:
                    result.scalar.return_value = count_values["daily"]
                elif "weekly" in query_str:
                    result.scalar.return_value = count_values["weekly"]
                else:
                    result.scalar.return_value = count_values["monthly"]
                return result
            return MagicMock()

        session.execute = mock_execute

        info = await aggregate_service.get_aggregate_info(db=session)

        assert "daily_accuracy_metrics" in info
        assert "weekly_accuracy_metrics" in info
        assert "monthly_accuracy_metrics" in info


# =============================================================================
# Test Constants
# =============================================================================


class TestServiceConstants:
    """Tests for service constants."""

    def test_view_names_are_correct(self, aggregate_service):
        """Test view name constants are correct."""
        assert aggregate_service.DAILY_VIEW == "daily_accuracy_metrics"
        assert aggregate_service.WEEKLY_VIEW == "weekly_accuracy_metrics"
        assert aggregate_service.MONTHLY_VIEW == "monthly_accuracy_metrics"
