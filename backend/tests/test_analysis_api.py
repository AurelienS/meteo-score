"""Tests for Analysis API endpoints.

Tests cover:
- Site accuracy endpoint with model comparison
- Model bias endpoint across horizons
- Time series accuracy endpoint with granularity
- Error handling (404, 400)
- camelCase field aliases in JSON responses
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def sample_site():
    """Sample site data for testing."""
    site = MagicMock()
    site.id = 1
    site.name = "Passy Plaine Joux"
    return site


@pytest.fixture
def sample_model():
    """Sample model data for testing."""
    model = MagicMock()
    model.id = 1
    model.name = "AROME"
    return model


@pytest.fixture
def sample_parameter():
    """Sample parameter data for testing."""
    param = MagicMock()
    param.id = 1
    param.name = "Wind Speed"
    param.unit = "km/h"
    return param


# =============================================================================
# Test Site Accuracy Endpoint
# =============================================================================


class TestSiteAccuracyEndpoint:
    """Tests for GET /api/analysis/sites/{site_id}/accuracy endpoint."""

    @pytest.mark.asyncio
    async def test_get_site_accuracy_returns_model_metrics(self):
        """Test endpoint returns accuracy metrics for all models at a site."""
        with patch("api.routes.analysis.get_db") as mock_get_db, \
             patch("api.routes.analysis.AnalysisService") as mock_service_class:
            # Setup mock
            mock_session = MagicMock()
            mock_get_db.return_value = AsyncMock(return_value=mock_session)()

            mock_service = MagicMock()
            mock_service.get_site_accuracy = AsyncMock(return_value={
                "site_id": 1,
                "site_name": "Passy Plaine Joux",
                "parameter_id": 1,
                "parameter_name": "Wind Speed",
                "horizon": 6,
                "models": [
                    {
                        "model_id": 1,
                        "model_name": "AROME",
                        "mae": 4.2,
                        "bias": -1.5,
                        "std_dev": 3.8,
                        "sample_size": 120,
                        "confidence_level": "validated",
                        "confidence_message": "Validated with 120 days of data.",
                    }
                ],
            })
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/analysis/sites/1/accuracy",
                    params={"parameterId": 1, "horizon": 6}
                )

            assert response.status_code == 200
            data = response.json()
            assert "siteId" in data
            assert "models" in data

    @pytest.mark.asyncio
    async def test_get_site_accuracy_404_when_not_found(self):
        """Test endpoint returns 404 when site has no metrics."""
        with patch("api.routes.analysis.get_db") as mock_get_db, \
             patch("api.routes.analysis.AnalysisService") as mock_service_class:
            mock_session = MagicMock()
            mock_get_db.return_value = AsyncMock(return_value=mock_session)()

            mock_service = MagicMock()
            mock_service.get_site_accuracy = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/analysis/sites/999/accuracy",
                    params={"parameterId": 1}
                )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_site_accuracy_with_custom_horizon(self):
        """Test endpoint accepts custom horizon values (12h, 24h, 48h)."""
        with patch("api.routes.analysis.get_db") as mock_get_db, \
             patch("api.routes.analysis.AnalysisService") as mock_service_class:
            mock_session = MagicMock()
            mock_get_db.return_value = AsyncMock(return_value=mock_session)()

            mock_service = MagicMock()
            mock_service.get_site_accuracy = AsyncMock(return_value={
                "site_id": 1,
                "site_name": "Passy",
                "parameter_id": 1,
                "parameter_name": "Wind Speed",
                "horizon": 24,
                "models": [],
            })
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/analysis/sites/1/accuracy",
                    params={"parameterId": 1, "horizon": 24}
                )

            assert response.status_code == 200
            data = response.json()
            assert data["horizon"] == 24

    @pytest.mark.asyncio
    async def test_get_site_accuracy_404_when_parameter_not_found(self):
        """Test endpoint returns 404 when parameter doesn't exist."""
        with patch("api.routes.analysis.get_db") as mock_get_db, \
             patch("api.routes.analysis.AnalysisService") as mock_service_class:
            mock_session = MagicMock()
            mock_get_db.return_value = AsyncMock(return_value=mock_session)()

            mock_service = MagicMock()
            # Service returns None when parameter not found
            mock_service.get_site_accuracy = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/analysis/sites/1/accuracy",
                    params={"parameterId": 999}  # Non-existent parameter
                )

            assert response.status_code == 404
            data = response.json()
            assert "parameter" in data["detail"].lower()


# =============================================================================
# Test Model Bias Endpoint
# =============================================================================


class TestModelBiasEndpoint:
    """Tests for GET /api/analysis/models/{model_id}/bias endpoint."""

    @pytest.mark.asyncio
    async def test_get_model_bias_returns_horizon_data(self):
        """Test endpoint returns bias data across forecast horizons."""
        with patch("api.routes.analysis.get_db") as mock_get_db, \
             patch("api.routes.analysis.AnalysisService") as mock_service_class:
            mock_session = MagicMock()
            mock_get_db.return_value = AsyncMock(return_value=mock_session)()

            mock_service = MagicMock()
            mock_service.get_model_bias = AsyncMock(return_value={
                "model_id": 1,
                "model_name": "AROME",
                "site_id": 1,
                "site_name": "Passy",
                "parameter_id": 1,
                "parameter_name": "Wind Speed",
                "horizons": [
                    {"horizon": 6, "bias": -1.5, "mae": 4.2, "sample_size": 100, "confidence_level": "validated"},
                    {"horizon": 12, "bias": -2.0, "mae": 5.0, "sample_size": 95, "confidence_level": "validated"},
                ],
            })
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/analysis/models/1/bias",
                    params={"siteId": 1, "parameterId": 1}
                )

            assert response.status_code == 200
            data = response.json()
            assert "horizons" in data
            assert len(data["horizons"]) == 2

    @pytest.mark.asyncio
    async def test_get_model_bias_404_when_not_found(self):
        """Test endpoint returns 404 when model has no bias data."""
        with patch("api.routes.analysis.get_db") as mock_get_db, \
             patch("api.routes.analysis.AnalysisService") as mock_service_class:
            mock_session = MagicMock()
            mock_get_db.return_value = AsyncMock(return_value=mock_session)()

            mock_service = MagicMock()
            mock_service.get_model_bias = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/analysis/models/999/bias",
                    params={"siteId": 1, "parameterId": 1}
                )

            assert response.status_code == 404


# =============================================================================
# Test Time Series Endpoint
# =============================================================================


class TestTimeSeriesEndpoint:
    """Tests for GET /api/analysis/sites/{site_id}/accuracy/timeseries endpoint."""

    @pytest.mark.asyncio
    async def test_get_timeseries_daily_returns_data(self):
        """Test endpoint returns daily time series data."""
        with patch("api.routes.analysis.get_db") as mock_get_db, \
             patch("api.routes.analysis.AnalysisService") as mock_service_class:
            mock_session = MagicMock()
            mock_get_db.return_value = AsyncMock(return_value=mock_session)()

            mock_service = MagicMock()
            mock_service.get_accuracy_timeseries = AsyncMock(return_value={
                "site_id": 1,
                "site_name": "Passy",
                "model_id": 1,
                "model_name": "AROME",
                "parameter_id": 1,
                "parameter_name": "Wind Speed",
                "granularity": "daily",
                "data_points": [
                    {"bucket": "2026-01-14T00:00:00Z", "mae": 4.0, "bias": -1.0, "sample_size": 24},
                    {"bucket": "2026-01-15T00:00:00Z", "mae": 4.5, "bias": -1.2, "sample_size": 24},
                ],
            })
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/analysis/sites/1/accuracy/timeseries",
                    params={"modelId": 1, "parameterId": 1, "granularity": "daily"}
                )

            assert response.status_code == 200
            data = response.json()
            assert data["granularity"] == "daily"
            assert "dataPoints" in data

    @pytest.mark.asyncio
    async def test_get_timeseries_400_invalid_granularity(self):
        """Test endpoint returns 400 for invalid granularity."""
        with patch("api.routes.analysis.get_db") as mock_get_db, \
             patch("api.routes.analysis.AnalysisService") as mock_service_class:
            mock_session = MagicMock()
            mock_get_db.return_value = AsyncMock(return_value=mock_session)()

            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/analysis/sites/1/accuracy/timeseries",
                    params={"modelId": 1, "parameterId": 1, "granularity": "invalid"}
                )

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_timeseries_weekly_granularity(self):
        """Test endpoint accepts weekly granularity."""
        with patch("api.routes.analysis.get_db") as mock_get_db, \
             patch("api.routes.analysis.AnalysisService") as mock_service_class:
            mock_session = MagicMock()
            mock_get_db.return_value = AsyncMock(return_value=mock_session)()

            mock_service = MagicMock()
            mock_service.get_accuracy_timeseries = AsyncMock(return_value={
                "site_id": 1,
                "site_name": "Passy",
                "model_id": 1,
                "model_name": "AROME",
                "parameter_id": 1,
                "parameter_name": "Wind Speed",
                "granularity": "weekly",
                "data_points": [],
            })
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/analysis/sites/1/accuracy/timeseries",
                    params={"modelId": 1, "parameterId": 1, "granularity": "weekly"}
                )

            assert response.status_code == 200


# =============================================================================
# Test camelCase Aliases
# =============================================================================


class TestCamelCaseAliases:
    """Tests for verifying camelCase field aliases in JSON responses."""

    @pytest.mark.asyncio
    async def test_site_accuracy_uses_camel_case(self):
        """Test site accuracy response uses camelCase field names."""
        with patch("api.routes.analysis.get_db") as mock_get_db, \
             patch("api.routes.analysis.AnalysisService") as mock_service_class:
            mock_session = MagicMock()
            mock_get_db.return_value = AsyncMock(return_value=mock_session)()

            mock_service = MagicMock()
            mock_service.get_site_accuracy = AsyncMock(return_value={
                "site_id": 1,
                "site_name": "Passy",
                "parameter_id": 1,
                "parameter_name": "Wind Speed",
                "horizon": 6,
                "models": [
                    {
                        "model_id": 1,
                        "model_name": "AROME",
                        "mae": 4.2,
                        "bias": -1.5,
                        "std_dev": 3.8,
                        "sample_size": 120,
                        "confidence_level": "validated",
                        "confidence_message": "Validated.",
                    }
                ],
            })
            mock_service_class.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/analysis/sites/1/accuracy",
                    params={"parameterId": 1}
                )

            data = response.json()
            # Check camelCase keys
            assert "siteId" in data
            assert "siteName" in data
            assert "parameterId" in data
            assert "parameterName" in data
            # Check nested model uses camelCase
            if data.get("models"):
                model = data["models"][0]
                assert "modelId" in model
                assert "modelName" in model
                assert "stdDev" in model
                assert "sampleSize" in model
                assert "confidenceLevel" in model
                assert "confidenceMessage" in model


# =============================================================================
# Test Schema Validation
# =============================================================================


class TestSchemaValidation:
    """Tests for Pydantic schema validation."""

    def test_model_accuracy_metrics_schema(self):
        """Test ModelAccuracyMetrics schema creation and serialization."""
        from api.schemas.analysis import ModelAccuracyMetrics

        metrics = ModelAccuracyMetrics(
            model_id=1,
            model_name="AROME",
            mae=4.2,
            bias=-1.5,
            std_dev=3.8,
            sample_size=120,
            confidence_level="validated",
            confidence_message="Validated with 120 days."
        )

        # Test internal values
        assert metrics.model_id == 1
        assert metrics.mae == 4.2

        # Test JSON serialization uses camelCase
        json_data = metrics.model_dump(by_alias=True)
        assert "modelId" in json_data
        assert "stdDev" in json_data
        assert "sampleSize" in json_data

    def test_site_accuracy_response_schema(self):
        """Test SiteAccuracyResponse schema with nested models."""
        from api.schemas.analysis import ModelAccuracyMetrics, SiteAccuracyResponse

        response = SiteAccuracyResponse(
            site_id=1,
            site_name="Passy",
            parameter_id=1,
            parameter_name="Wind Speed",
            horizon=6,
            models=[
                ModelAccuracyMetrics(
                    model_id=1,
                    model_name="AROME",
                    mae=4.2,
                    bias=-1.5,
                    std_dev=3.8,
                    sample_size=120,
                    confidence_level="validated",
                    confidence_message="Validated."
                )
            ]
        )

        json_data = response.model_dump(by_alias=True)
        assert json_data["siteId"] == 1
        assert len(json_data["models"]) == 1
        assert json_data["models"][0]["modelId"] == 1

    def test_time_series_response_schema(self):
        """Test TimeSeriesAccuracyResponse schema."""
        from api.schemas.analysis import TimeSeriesAccuracyResponse, TimeSeriesDataPoint

        response = TimeSeriesAccuracyResponse(
            site_id=1,
            site_name="Passy",
            model_id=1,
            model_name="AROME",
            parameter_id=1,
            parameter_name="Wind Speed",
            granularity="daily",
            data_points=[
                TimeSeriesDataPoint(
                    bucket=datetime(2026, 1, 15, tzinfo=timezone.utc),
                    mae=4.0,
                    bias=-1.0,
                    sample_size=24
                )
            ]
        )

        json_data = response.model_dump(by_alias=True)
        assert json_data["granularity"] == "daily"
        assert "dataPoints" in json_data
        assert len(json_data["dataPoints"]) == 1
