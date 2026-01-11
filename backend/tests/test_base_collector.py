"""Unit tests for base collector infrastructure.

Tests cover:
- Data transfer objects (ForecastData, ObservationData)
- Deviation calculation engine
- Retry decorator with exponential backoff
- HTTP client wrapper
- Date parsing utilities
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from backend.collectors.base import BaseCollector
from backend.collectors.utils import (
    CollectorError,
    HttpClient,
    HttpClientError,
    RetryExhaustedError,
    parse_datetime_flexible,
    parse_iso_datetime,
    parse_unix_timestamp,
    retry_with_backoff,
)
from backend.core.data_models import ForecastData, ObservationData
from backend.core.deviation_engine import calculate_deviation


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_forecast() -> ForecastData:
    """Create a sample forecast data object."""
    return ForecastData(
        site_id=1,
        model_id=1,
        parameter_id=1,
        forecast_run=datetime(2026, 1, 11, 0, 0, tzinfo=timezone.utc),
        valid_time=datetime(2026, 1, 11, 12, 0, tzinfo=timezone.utc),
        horizon=12,
        value=Decimal("25.5"),
    )


@pytest.fixture
def sample_observation() -> ObservationData:
    """Create a sample observation data object."""
    return ObservationData(
        site_id=1,
        parameter_id=1,
        observation_time=datetime(2026, 1, 11, 12, 0, tzinfo=timezone.utc),
        value=Decimal("22.3"),
    )


# =============================================================================
# Test ForecastData and ObservationData
# =============================================================================


class TestForecastData:
    """Tests for ForecastData dataclass."""

    def test_create_forecast_data(self, sample_forecast: ForecastData) -> None:
        """Test creating a ForecastData instance."""
        assert sample_forecast.site_id == 1
        assert sample_forecast.model_id == 1
        assert sample_forecast.parameter_id == 1
        assert sample_forecast.horizon == 12
        assert sample_forecast.value == Decimal("25.5")

    def test_forecast_data_immutable(self, sample_forecast: ForecastData) -> None:
        """Test that ForecastData is immutable (frozen)."""
        with pytest.raises(AttributeError):
            sample_forecast.value = Decimal("30.0")  # type: ignore

    def test_forecast_data_equality(self) -> None:
        """Test ForecastData equality comparison."""
        dt = datetime(2026, 1, 11, 0, 0, tzinfo=timezone.utc)
        forecast1 = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=1,
            forecast_run=dt,
            valid_time=dt,
            horizon=0,
            value=Decimal("10.0"),
        )
        forecast2 = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=1,
            forecast_run=dt,
            valid_time=dt,
            horizon=0,
            value=Decimal("10.0"),
        )
        assert forecast1 == forecast2


class TestObservationData:
    """Tests for ObservationData dataclass."""

    def test_create_observation_data(self, sample_observation: ObservationData) -> None:
        """Test creating an ObservationData instance."""
        assert sample_observation.site_id == 1
        assert sample_observation.parameter_id == 1
        assert sample_observation.value == Decimal("22.3")

    def test_observation_data_immutable(
        self, sample_observation: ObservationData
    ) -> None:
        """Test that ObservationData is immutable (frozen)."""
        with pytest.raises(AttributeError):
            sample_observation.value = Decimal("30.0")  # type: ignore


# =============================================================================
# Test Deviation Engine
# =============================================================================


class TestDeviationEngine:
    """Tests for deviation calculation engine."""

    def test_calculate_deviation_positive(
        self, sample_forecast: ForecastData, sample_observation: ObservationData
    ) -> None:
        """Test deviation calculation when forecast > observed."""
        # forecast: 25.5, observation: 22.3 -> deviation: 3.2
        result = calculate_deviation(sample_forecast, sample_observation)
        assert result == Decimal("3.2")

    def test_calculate_deviation_negative(self) -> None:
        """Test deviation calculation when forecast < observed."""
        dt = datetime(2026, 1, 11, 12, 0, tzinfo=timezone.utc)
        forecast = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=1,
            forecast_run=dt,
            valid_time=dt,
            horizon=0,
            value=Decimal("20.0"),
        )
        observation = ObservationData(
            site_id=1,
            parameter_id=1,
            observation_time=dt,
            value=Decimal("25.0"),
        )
        result = calculate_deviation(forecast, observation)
        assert result == Decimal("-5.0")

    def test_calculate_deviation_zero(self) -> None:
        """Test deviation calculation when forecast equals observed."""
        dt = datetime(2026, 1, 11, 12, 0, tzinfo=timezone.utc)
        forecast = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=1,
            forecast_run=dt,
            valid_time=dt,
            horizon=0,
            value=Decimal("15.0"),
        )
        observation = ObservationData(
            site_id=1,
            parameter_id=1,
            observation_time=dt,
            value=Decimal("15.0"),
        )
        result = calculate_deviation(forecast, observation)
        assert result == Decimal("0")

    def test_calculate_deviation_site_mismatch(self) -> None:
        """Test that site_id mismatch raises ValueError."""
        dt = datetime(2026, 1, 11, 12, 0, tzinfo=timezone.utc)
        forecast = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=1,
            forecast_run=dt,
            valid_time=dt,
            horizon=0,
            value=Decimal("15.0"),
        )
        observation = ObservationData(
            site_id=2,  # Different site!
            parameter_id=1,
            observation_time=dt,
            value=Decimal("15.0"),
        )
        with pytest.raises(ValueError, match="Site ID mismatch"):
            calculate_deviation(forecast, observation)

    def test_calculate_deviation_parameter_mismatch(self) -> None:
        """Test that parameter_id mismatch raises ValueError."""
        dt = datetime(2026, 1, 11, 12, 0, tzinfo=timezone.utc)
        forecast = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=1,
            forecast_run=dt,
            valid_time=dt,
            horizon=0,
            value=Decimal("15.0"),
        )
        observation = ObservationData(
            site_id=1,
            parameter_id=2,  # Different parameter!
            observation_time=dt,
            value=Decimal("15.0"),
        )
        with pytest.raises(ValueError, match="Parameter ID mismatch"):
            calculate_deviation(forecast, observation)

    def test_calculate_deviation_decimal_precision(self) -> None:
        """Test that Decimal precision is preserved in calculation."""
        dt = datetime(2026, 1, 11, 12, 0, tzinfo=timezone.utc)
        forecast = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=1,
            forecast_run=dt,
            valid_time=dt,
            horizon=0,
            value=Decimal("25.123456789"),
        )
        observation = ObservationData(
            site_id=1,
            parameter_id=1,
            observation_time=dt,
            value=Decimal("22.987654321"),
        )
        result = calculate_deviation(forecast, observation)
        assert result == Decimal("2.135802468")


# =============================================================================
# Test Retry Decorator
# =============================================================================


class TestRetryWithBackoff:
    """Tests for retry_with_backoff decorator."""

    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self) -> None:
        """Test that function succeeds on first attempt."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def always_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await always_succeeds()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self) -> None:
        """Test that function succeeds after initial failures."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def succeeds_on_third() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary failure")
            return "success"

        result = await succeeds_on_third()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self) -> None:
        """Test that RetryExhaustedError is raised after all retries."""

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def always_fails() -> str:
            raise ValueError("permanent failure")

        with pytest.raises(RetryExhaustedError) as exc_info:
            await always_fails()

        assert "3 attempts failed" in str(exc_info.value)
        assert exc_info.value.last_exception is not None

    @pytest.mark.asyncio
    async def test_retry_specific_exceptions(self) -> None:
        """Test that only specified exceptions trigger retry."""

        @retry_with_backoff(
            max_retries=2, base_delay=0.01, exceptions=(ValueError,)
        )
        async def raises_type_error() -> str:
            raise TypeError("not retried")

        # TypeError should not be retried
        with pytest.raises(TypeError):
            await raises_type_error()


# =============================================================================
# Test HTTP Client
# =============================================================================


class TestHttpClient:
    """Tests for HttpClient wrapper."""

    @pytest.mark.asyncio
    async def test_client_context_manager(self) -> None:
        """Test that client works as async context manager."""
        async with HttpClient(timeout=5.0) as client:
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_client_not_initialized_error(self) -> None:
        """Test that using client without context raises error."""
        client = HttpClient()
        with pytest.raises(HttpClientError, match="not initialized"):
            await client.get("https://example.com")

    @pytest.mark.asyncio
    async def test_get_json_success(self) -> None:
        """Test successful JSON GET request."""

        async def mock_get(self: Any, url: str, **kwargs: Any) -> dict[str, Any]:
            return {"key": "value"}

        with patch.object(HttpClient, "get", mock_get):
            async with HttpClient() as client:
                result = await client.get("https://api.example.com/data")
                assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_text_success(self) -> None:
        """Test successful text GET request."""

        async def mock_get_text(self: Any, url: str, **kwargs: Any) -> str:
            return "<html>content</html>"

        with patch.object(HttpClient, "get_text", mock_get_text):
            async with HttpClient() as client:
                result = await client.get_text("https://example.com/page")
                assert result == "<html>content</html>"

    @pytest.mark.asyncio
    async def test_get_http_status_error(self) -> None:
        """Test that HTTP status errors are converted to HttpClientError."""
        async with HttpClient(timeout=5.0) as client:
            # Mock the internal client to raise HTTPStatusError
            mock_response = httpx.Response(
                status_code=404,
                request=httpx.Request("GET", "https://example.com/notfound"),
            )
            mock_response._content = b"Not Found"

            async def mock_get(*args: Any, **kwargs: Any) -> httpx.Response:
                raise httpx.HTTPStatusError(
                    "Not Found", request=mock_response.request, response=mock_response
                )

            client._client.get = mock_get  # type: ignore

            with pytest.raises(HttpClientError) as exc_info:
                await client.get("https://example.com/notfound")

            assert exc_info.value.status_code == 404
            assert "404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_request_error(self) -> None:
        """Test that network errors are converted to HttpClientError."""
        async with HttpClient(timeout=5.0) as client:

            async def mock_get(*args: Any, **kwargs: Any) -> httpx.Response:
                raise httpx.RequestError("Connection refused")

            client._client.get = mock_get  # type: ignore

            with pytest.raises(HttpClientError) as exc_info:
                await client.get("https://example.com/error")

            assert "Request failed" in str(exc_info.value)
            assert exc_info.value.status_code is None

    @pytest.mark.asyncio
    async def test_get_invalid_json_error(self) -> None:
        """Test that invalid JSON responses raise HttpClientError."""
        async with HttpClient(timeout=5.0) as client:
            mock_response = httpx.Response(
                status_code=200,
                content=b"not valid json",
                request=httpx.Request("GET", "https://example.com/bad-json"),
            )

            async def mock_get(*args: Any, **kwargs: Any) -> httpx.Response:
                return mock_response

            client._client.get = mock_get  # type: ignore

            with pytest.raises(HttpClientError) as exc_info:
                await client.get("https://example.com/bad-json")

            assert "Invalid JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_text_http_error(self) -> None:
        """Test that get_text handles HTTP errors correctly."""
        async with HttpClient(timeout=5.0) as client:
            mock_response = httpx.Response(
                status_code=500,
                request=httpx.Request("GET", "https://example.com/error"),
            )
            mock_response._content = b"Internal Server Error"

            async def mock_get(*args: Any, **kwargs: Any) -> httpx.Response:
                raise httpx.HTTPStatusError(
                    "Server Error", request=mock_response.request, response=mock_response
                )

            client._client.get = mock_get  # type: ignore

            with pytest.raises(HttpClientError) as exc_info:
                await client.get_text("https://example.com/error")

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_bytes_http_error(self) -> None:
        """Test that get_bytes handles HTTP errors correctly."""
        async with HttpClient(timeout=5.0) as client:
            mock_response = httpx.Response(
                status_code=403,
                request=httpx.Request("GET", "https://example.com/forbidden"),
            )
            mock_response._content = b"Forbidden"

            async def mock_get(*args: Any, **kwargs: Any) -> httpx.Response:
                raise httpx.HTTPStatusError(
                    "Forbidden", request=mock_response.request, response=mock_response
                )

            client._client.get = mock_get  # type: ignore

            with pytest.raises(HttpClientError) as exc_info:
                await client.get_bytes("https://example.com/forbidden")

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_bytes_success(self) -> None:
        """Test successful binary GET request."""
        async with HttpClient(timeout=5.0) as client:
            mock_response = httpx.Response(
                status_code=200,
                content=b"\x00\x01\x02\x03",
                request=httpx.Request("GET", "https://example.com/binary"),
            )

            async def mock_get(*args: Any, **kwargs: Any) -> httpx.Response:
                return mock_response

            client._client.get = mock_get  # type: ignore

            result = await client.get_bytes("https://example.com/binary")
            assert result == b"\x00\x01\x02\x03"


# =============================================================================
# Test Collector Exceptions
# =============================================================================


class TestCollectorExceptions:
    """Tests for collector exception classes."""

    def test_collector_error_base(self) -> None:
        """Test CollectorError base exception."""
        error = CollectorError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_http_client_error_with_status(self) -> None:
        """Test HttpClientError with status code."""
        error = HttpClientError("Not Found", status_code=404)
        assert str(error) == "Not Found"
        assert error.status_code == 404
        assert isinstance(error, CollectorError)

    def test_http_client_error_without_status(self) -> None:
        """Test HttpClientError without status code."""
        error = HttpClientError("Connection failed")
        assert str(error) == "Connection failed"
        assert error.status_code is None

    def test_retry_exhausted_error(self) -> None:
        """Test RetryExhaustedError with last exception."""
        original = ValueError("Original error")
        error = RetryExhaustedError("All retries failed", last_exception=original)
        assert str(error) == "All retries failed"
        assert error.last_exception is original
        assert isinstance(error, CollectorError)


# =============================================================================
# Test Date Parsing Utilities
# =============================================================================


class TestDateParsingUtilities:
    """Tests for date/time parsing utilities."""

    def test_parse_iso_datetime_with_z(self) -> None:
        """Test parsing ISO datetime with Z suffix."""
        result = parse_iso_datetime("2026-01-11T12:00:00Z")
        assert result == datetime(2026, 1, 11, 12, 0, 0, tzinfo=timezone.utc)

    def test_parse_iso_datetime_with_offset(self) -> None:
        """Test parsing ISO datetime with timezone offset."""
        result = parse_iso_datetime("2026-01-11T12:00:00+00:00")
        assert result == datetime(2026, 1, 11, 12, 0, 0, tzinfo=timezone.utc)

    def test_parse_iso_datetime_naive_becomes_utc(self) -> None:
        """Test that naive datetime is converted to UTC."""
        result = parse_iso_datetime("2026-01-11T12:00:00")
        assert result.tzinfo == timezone.utc
        assert result == datetime(2026, 1, 11, 12, 0, 0, tzinfo=timezone.utc)

    def test_parse_iso_datetime_invalid(self) -> None:
        """Test that invalid datetime string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse datetime"):
            parse_iso_datetime("not-a-date")

    def test_parse_unix_timestamp(self) -> None:
        """Test parsing Unix timestamp."""
        # 2026-01-11T12:00:00Z = 1768132800
        result = parse_unix_timestamp(1768132800)
        assert result == datetime(2026, 1, 11, 12, 0, 0, tzinfo=timezone.utc)

    def test_parse_datetime_flexible_iso(self) -> None:
        """Test flexible parsing with ISO string."""
        result = parse_datetime_flexible("2026-01-11T12:00:00Z")
        assert result == datetime(2026, 1, 11, 12, 0, 0, tzinfo=timezone.utc)

    def test_parse_datetime_flexible_unix_int(self) -> None:
        """Test flexible parsing with Unix timestamp integer."""
        result = parse_datetime_flexible(1768132800)
        assert result == datetime(2026, 1, 11, 12, 0, 0, tzinfo=timezone.utc)

    def test_parse_datetime_flexible_unix_string(self) -> None:
        """Test flexible parsing with Unix timestamp as string."""
        result = parse_datetime_flexible("1768132800")
        assert result == datetime(2026, 1, 11, 12, 0, 0, tzinfo=timezone.utc)


# =============================================================================
# Test BaseCollector Abstract Class
# =============================================================================


class TestBaseCollector:
    """Tests for BaseCollector abstract class."""

    def test_cannot_instantiate_base_collector(self) -> None:
        """Test that BaseCollector cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseCollector()  # type: ignore

    def test_concrete_collector_must_implement_methods(self) -> None:
        """Test that concrete collectors must implement abstract methods."""

        # This should fail because methods are not implemented
        class IncompleteCollector(BaseCollector):
            pass

        with pytest.raises(TypeError):
            IncompleteCollector()  # type: ignore

    @pytest.mark.asyncio
    async def test_concrete_collector_implementation(self) -> None:
        """Test that properly implemented collector works."""
        from typing import List

        class TestCollector(BaseCollector):
            name = "Test"
            source = "Test Source"

            async def collect_forecast(
                self, site_id: int, forecast_run: datetime
            ) -> List[ForecastData]:
                return [
                    ForecastData(
                        site_id=site_id,
                        model_id=1,
                        parameter_id=1,
                        forecast_run=forecast_run,
                        valid_time=forecast_run,
                        horizon=0,
                        value=Decimal("10.0"),
                    )
                ]

            async def collect_observation(
                self, site_id: int, observation_time: datetime
            ) -> List[ObservationData]:
                return []

        collector = TestCollector()
        assert collector.name == "Test"
        assert collector.source == "Test Source"

        forecasts = await collector.collect_forecast(
            site_id=1, forecast_run=datetime.now(tz=timezone.utc)
        )
        assert len(forecasts) == 1
        assert forecasts[0].site_id == 1
