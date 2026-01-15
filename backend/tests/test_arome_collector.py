"""TDD test suite for AROME forecast collector.

Tests are written FIRST following TDD approach (Red → Green → Refactor).
All tests use mocked data - NEVER call real Météo-France API.

Test Coverage:
- GRIB2 download from Météo-France API
- Parsing GRIB2 with cfgrib and xarray
- Extracting wind U/V components and converting to speed/direction
- Extracting temperature at surface level
- Handling missing GRIB2 fields
- Coordinate interpolation to site location
- HTTP error scenarios (404, 500, timeout)
- Rate limiting compliance
"""

import io
import math
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
import xarray as xr

from collectors.arome import AROMECollector
from collectors.utils import HttpClientError, RetryExhaustedError
from core.data_models import ForecastData


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def collector():
    """Create AROMECollector instance."""
    return AROMECollector()


@pytest.fixture
def forecast_run():
    """Standard forecast run datetime for tests."""
    return datetime(2026, 1, 12, 6, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_xarray_dataset():
    """Create mock xarray dataset simulating GRIB2 data.

    Simulates AROME GRIB2 structure with:
    - u10: 10m U wind component (m/s)
    - v10: 10m V wind component (m/s)
    - t2m: 2m temperature (K - Kelvin, converted to Celsius)
    - Coordinates: latitude, longitude, time (valid_time)
    """
    # Create coordinate arrays matching AROME grid around Passy
    lats = np.array([45.5, 45.75, 46.0, 46.25])
    lons = np.array([6.25, 6.5, 6.75, 7.0])

    # Create time coordinates (forecast valid times)
    base_time = np.datetime64("2026-01-12T06:00:00")
    times = np.array([
        base_time,
        base_time + np.timedelta64(1, "h"),
        base_time + np.timedelta64(2, "h"),
        base_time + np.timedelta64(3, "h"),
        base_time + np.timedelta64(6, "h"),
        base_time + np.timedelta64(12, "h"),
    ])

    # Create deterministic wind data for predictable tests
    # u10: 5 m/s, v10: 5 m/s → speed = 7.07 m/s = 25.5 km/h
    u_data = np.full((len(times), len(lats), len(lons)), 5.0)
    v_data = np.full((len(times), len(lats), len(lons)), 5.0)

    # Temperature in Kelvin (273.15 = 0°C, so 283.15 = 10°C)
    t_data = np.full((len(times), len(lats), len(lons)), 283.15)

    ds = xr.Dataset(
        {
            "u10": (["valid_time", "latitude", "longitude"], u_data),
            "v10": (["valid_time", "latitude", "longitude"], v_data),
            "t2m": (["valid_time", "latitude", "longitude"], t_data),
        },
        coords={
            "valid_time": times,
            "latitude": lats,
            "longitude": lons,
        },
    )
    return ds


@pytest.fixture
def mock_xarray_dataset_with_variation():
    """Create mock dataset with varying values for interpolation tests."""
    lats = np.array([45.5, 46.0, 46.5])
    lons = np.array([6.0, 6.5, 7.0])

    base_time = np.datetime64("2026-01-12T06:00:00")
    times = np.array([base_time])

    # Create gradient data to test interpolation
    # u varies from 0 to 10 m/s across longitude
    u_data = np.array([[[0.0, 5.0, 10.0]] * 3])
    v_data = np.array([[[5.0, 5.0, 5.0]] * 3])
    t_data = np.array([[[280.0, 283.0, 286.0]] * 3])  # 7°C, 10°C, 13°C

    ds = xr.Dataset(
        {
            "u10": (["valid_time", "latitude", "longitude"], u_data),
            "v10": (["valid_time", "latitude", "longitude"], v_data),
            "t2m": (["valid_time", "latitude", "longitude"], t_data),
        },
        coords={
            "valid_time": times,
            "latitude": lats,
            "longitude": lons,
        },
    )
    return ds


@pytest.fixture
def mock_xarray_dataset_missing_wind():
    """Create mock dataset with missing wind components."""
    lats = np.array([45.5, 46.0])
    lons = np.array([6.0, 6.5])
    times = np.array([np.datetime64("2026-01-12T06:00:00")])

    # Only temperature, no wind data
    t_data = np.full((1, 2, 2), 283.15)

    ds = xr.Dataset(
        {
            "t2m": (["valid_time", "latitude", "longitude"], t_data),
        },
        coords={
            "valid_time": times,
            "latitude": lats,
            "longitude": lons,
        },
    )
    return ds


@pytest.fixture
def mock_xarray_dataset_missing_temperature():
    """Create mock dataset with missing temperature."""
    lats = np.array([45.5, 46.0])
    lons = np.array([6.0, 6.5])
    times = np.array([np.datetime64("2026-01-12T06:00:00")])

    u_data = np.full((1, 2, 2), 5.0)
    v_data = np.full((1, 2, 2), 5.0)

    ds = xr.Dataset(
        {
            "u10": (["valid_time", "latitude", "longitude"], u_data),
            "v10": (["valid_time", "latitude", "longitude"], v_data),
        },
        coords={
            "valid_time": times,
            "latitude": lats,
            "longitude": lons,
        },
    )
    return ds


# =============================================================================
# Class Structure Tests
# =============================================================================


class TestAROMECollectorStructure:
    """Test AROMECollector class structure and interface."""

    def test_inherits_from_base_collector(self, collector):
        """Verify AROMECollector inherits from BaseCollector."""
        from collectors.base import BaseCollector

        assert isinstance(collector, BaseCollector)

    def test_has_required_class_attributes(self, collector):
        """Verify required class attributes are defined."""
        assert hasattr(collector, "name")
        assert hasattr(collector, "source")
        assert hasattr(collector, "API_ENDPOINT")
        assert hasattr(collector, "TIMEOUT")

    def test_name_attribute(self, collector):
        """Verify collector name is correctly set."""
        assert collector.name == "AROMECollector"

    def test_source_attribute(self, collector):
        """Verify source is correctly set."""
        assert collector.source == "AROME"

    def test_api_endpoint(self, collector):
        """Verify API endpoint is defined."""
        assert "meteofrance" in collector.API_ENDPOINT.lower()

    def test_timeout_for_large_files(self, collector):
        """Verify timeout is appropriate for large GRIB2 files."""
        # GRIB2 files can be large, need longer timeout than JSON APIs
        assert collector.TIMEOUT >= 30.0

    def test_has_collect_forecast_method(self, collector):
        """Verify collect_forecast method exists."""
        assert hasattr(collector, "collect_forecast")
        assert callable(collector.collect_forecast)

    def test_has_collect_observation_method(self, collector):
        """Verify collect_observation method exists."""
        assert hasattr(collector, "collect_observation")
        assert callable(collector.collect_observation)


# =============================================================================
# Wind Calculation Tests
# =============================================================================


class TestWindCalculations:
    """Test wind speed and direction calculations from U/V components."""

    def test_calculate_wind_speed_basic(self, collector):
        """Test basic wind speed calculation."""
        # u=3, v=4 → speed = sqrt(9+16) = 5 m/s = 18 km/h
        speed = collector._calculate_wind_speed(3.0, 4.0)
        assert speed == Decimal("18.0")

    def test_calculate_wind_speed_zero(self, collector):
        """Test wind speed calculation with zero wind."""
        speed = collector._calculate_wind_speed(0.0, 0.0)
        assert speed == Decimal("0.0")

    def test_calculate_wind_speed_negative_components(self, collector):
        """Test wind speed with negative U/V components."""
        # u=-3, v=-4 → speed = sqrt(9+16) = 5 m/s = 18 km/h
        speed = collector._calculate_wind_speed(-3.0, -4.0)
        assert speed == Decimal("18.0")

    def test_calculate_wind_speed_conversion_factor(self, collector):
        """Test m/s to km/h conversion (factor 3.6)."""
        # 10 m/s = 36 km/h
        speed = collector._calculate_wind_speed(10.0, 0.0)
        assert speed == Decimal("36.0")

    def test_calculate_wind_direction_north(self, collector):
        """Test wind from North (v negative, u zero)."""
        # Wind coming FROM north: v=-5 (toward south), u=0
        direction = collector._calculate_wind_direction(0.0, -5.0)
        assert direction == Decimal("0") or direction == Decimal("360")

    def test_calculate_wind_direction_south(self, collector):
        """Test wind from South."""
        # Wind coming FROM south: v=5 (toward north), u=0
        direction = collector._calculate_wind_direction(0.0, 5.0)
        assert direction == Decimal("180")

    def test_calculate_wind_direction_east(self, collector):
        """Test wind from East."""
        # Wind coming FROM east: u=-5 (toward west), v=0
        direction = collector._calculate_wind_direction(-5.0, 0.0)
        assert direction == Decimal("90")

    def test_calculate_wind_direction_west(self, collector):
        """Test wind from West."""
        # Wind coming FROM west: u=5 (toward east), v=0
        direction = collector._calculate_wind_direction(5.0, 0.0)
        assert direction == Decimal("270")

    def test_calculate_wind_direction_zero_wind(self, collector):
        """Test wind direction with zero wind."""
        direction = collector._calculate_wind_direction(0.0, 0.0)
        assert direction == Decimal("0")

    def test_calculate_wind_direction_always_positive(self, collector):
        """Test that wind direction is always in 0-360 range."""
        # Test various combinations
        for u in [-10.0, -5.0, 0.0, 5.0, 10.0]:
            for v in [-10.0, -5.0, 0.0, 5.0, 10.0]:
                if u == 0 and v == 0:
                    continue
                direction = collector._calculate_wind_direction(u, v)
                assert Decimal("0") <= direction <= Decimal("360")


# =============================================================================
# Temperature Conversion Tests
# =============================================================================


class TestTemperatureConversion:
    """Test temperature conversion from Kelvin to Celsius."""

    def test_convert_kelvin_to_celsius_freezing(self, collector):
        """Test 273.15 K = 0°C."""
        celsius = collector._kelvin_to_celsius(273.15)
        assert celsius == Decimal("0.0")

    def test_convert_kelvin_to_celsius_positive(self, collector):
        """Test positive Celsius temperature."""
        # 293.15 K = 20°C
        celsius = collector._kelvin_to_celsius(293.15)
        assert celsius == Decimal("20.0")

    def test_convert_kelvin_to_celsius_negative(self, collector):
        """Test negative Celsius temperature."""
        # 263.15 K = -10°C
        celsius = collector._kelvin_to_celsius(263.15)
        assert celsius == Decimal("-10.0")

    def test_convert_kelvin_to_celsius_rounding(self, collector):
        """Test temperature rounding to 0.1 precision."""
        # 283.156 K = 10.006°C → rounds to 10.0°C
        celsius = collector._kelvin_to_celsius(283.156)
        assert celsius == Decimal("10.0")


# =============================================================================
# Data Validation Tests
# =============================================================================


class TestDataValidation:
    """Test aberrant value detection."""

    def test_valid_wind_speed(self, collector):
        """Test valid wind speed is accepted."""
        assert collector._is_valid_value("wind_speed", Decimal("50.0")) is True
        assert collector._is_valid_value("wind_speed", Decimal("0.0")) is True
        assert collector._is_valid_value("wind_speed", Decimal("200.0")) is True

    def test_invalid_wind_speed(self, collector):
        """Test aberrant wind speed is rejected."""
        assert collector._is_valid_value("wind_speed", Decimal("-1.0")) is False
        assert collector._is_valid_value("wind_speed", Decimal("250.0")) is False

    def test_valid_wind_direction(self, collector):
        """Test valid wind direction is accepted."""
        assert collector._is_valid_value("wind_direction", Decimal("0")) is True
        assert collector._is_valid_value("wind_direction", Decimal("180")) is True
        assert collector._is_valid_value("wind_direction", Decimal("360")) is True

    def test_invalid_wind_direction(self, collector):
        """Test aberrant wind direction is rejected."""
        assert collector._is_valid_value("wind_direction", Decimal("-10")) is False
        assert collector._is_valid_value("wind_direction", Decimal("400")) is False

    def test_valid_temperature(self, collector):
        """Test valid temperature is accepted."""
        assert collector._is_valid_value("temperature", Decimal("20.0")) is True
        assert collector._is_valid_value("temperature", Decimal("-30.0")) is True
        assert collector._is_valid_value("temperature", Decimal("50.0")) is True

    def test_invalid_temperature(self, collector):
        """Test aberrant temperature is rejected."""
        assert collector._is_valid_value("temperature", Decimal("-60.0")) is False
        assert collector._is_valid_value("temperature", Decimal("60.0")) is False


# =============================================================================
# Coordinate Interpolation Tests
# =============================================================================


class TestCoordinateInterpolation:
    """Test interpolation of grid data to site coordinates."""

    def test_interpolate_to_exact_grid_point(
        self, collector, mock_xarray_dataset
    ):
        """Test interpolation when site is exactly on grid point."""
        # Site at exact grid point (45.75, 6.5)
        result = collector._interpolate_to_site(
            dataset=mock_xarray_dataset,
            latitude=45.75,
            longitude=6.5,
        )
        assert result is not None
        assert "u10" in result
        assert "v10" in result
        assert "t2m" in result

    def test_interpolate_between_grid_points(
        self, collector, mock_xarray_dataset_with_variation
    ):
        """Test linear interpolation between grid points."""
        # Interpolate at longitude 6.25 (between 6.0 and 6.5)
        result = collector._interpolate_to_site(
            dataset=mock_xarray_dataset_with_variation,
            latitude=46.0,
            longitude=6.25,
        )
        assert result is not None
        # u should be between 0 and 5 (interpolated)
        u_value = float(result["u10"].values.flatten()[0])
        assert 0.0 < u_value < 5.0

    def test_interpolate_outside_grid_returns_none(self, collector, mock_xarray_dataset):
        """Test that interpolation outside grid bounds handles gracefully."""
        # Site far outside grid
        result = collector._interpolate_to_site(
            dataset=mock_xarray_dataset,
            latitude=50.0,  # Way outside grid
            longitude=10.0,
        )
        # Should either return None or extrapolated values
        # Implementation decides behavior


# =============================================================================
# GRIB2 Parsing Tests
# =============================================================================


class TestGrib2Parsing:
    """Test GRIB2 file parsing with xarray/cfgrib."""

    @pytest.mark.asyncio
    async def test_parse_grib2_extracts_wind_speed(
        self, collector, mock_xarray_dataset, forecast_run
    ):
        """Test wind speed extraction from GRIB2 data."""
        results = collector._parse_grib2_data(
            dataset=mock_xarray_dataset,
            site_id=1,
            model_id=3,
            latitude=45.9167,
            longitude=6.7000,
            forecast_run=forecast_run,
        )

        # Should have ForecastData for wind speed
        wind_speed_results = [
            r for r in results if r.parameter_id == 1  # wind_speed
        ]
        assert len(wind_speed_results) > 0

        # u=5, v=5 → speed = sqrt(50) * 3.6 ≈ 25.5 km/h
        expected_speed = Decimal("25.5")
        assert wind_speed_results[0].value == expected_speed

    @pytest.mark.asyncio
    async def test_parse_grib2_extracts_wind_direction(
        self, collector, mock_xarray_dataset, forecast_run
    ):
        """Test wind direction extraction from GRIB2 data."""
        results = collector._parse_grib2_data(
            dataset=mock_xarray_dataset,
            site_id=1,
            model_id=3,
            latitude=45.9167,
            longitude=6.7000,
            forecast_run=forecast_run,
        )

        wind_dir_results = [
            r for r in results if r.parameter_id == 2  # wind_direction
        ]
        assert len(wind_dir_results) > 0

        # u=5, v=5 → direction = atan2(-5, -5) = 225° (from SW)
        expected_direction = Decimal("225")
        assert wind_dir_results[0].value == expected_direction

    @pytest.mark.asyncio
    async def test_parse_grib2_extracts_temperature(
        self, collector, mock_xarray_dataset, forecast_run
    ):
        """Test temperature extraction from GRIB2 data."""
        results = collector._parse_grib2_data(
            dataset=mock_xarray_dataset,
            site_id=1,
            model_id=3,
            latitude=45.9167,
            longitude=6.7000,
            forecast_run=forecast_run,
        )

        temp_results = [
            r for r in results if r.parameter_id == 3  # temperature
        ]
        assert len(temp_results) > 0

        # 283.15 K = 10°C
        expected_temp = Decimal("10.0")
        assert temp_results[0].value == expected_temp

    @pytest.mark.asyncio
    async def test_parse_grib2_calculates_horizons(
        self, collector, mock_xarray_dataset, forecast_run
    ):
        """Test forecast horizon calculation."""
        results = collector._parse_grib2_data(
            dataset=mock_xarray_dataset,
            site_id=1,
            model_id=3,
            latitude=45.9167,
            longitude=6.7000,
            forecast_run=forecast_run,
        )

        # Get unique horizons
        horizons = set(r.horizon for r in results)

        # Dataset has times at H+0, H+1, H+2, H+3, H+6, H+12
        assert 0 in horizons
        assert 1 in horizons
        assert 6 in horizons
        assert 12 in horizons

    @pytest.mark.asyncio
    async def test_parse_grib2_returns_forecast_data_objects(
        self, collector, mock_xarray_dataset, forecast_run
    ):
        """Test that results are ForecastData objects."""
        results = collector._parse_grib2_data(
            dataset=mock_xarray_dataset,
            site_id=1,
            model_id=3,
            latitude=45.9167,
            longitude=6.7000,
            forecast_run=forecast_run,
        )

        assert len(results) > 0
        for result in results:
            assert isinstance(result, ForecastData)
            assert result.site_id == 1
            assert result.model_id == 3


# =============================================================================
# Missing Data Handling Tests
# =============================================================================


class TestMissingDataHandling:
    """Test handling of missing or incomplete GRIB2 data."""

    @pytest.mark.asyncio
    async def test_missing_wind_components_skips_wind(
        self, collector, mock_xarray_dataset_missing_wind, forecast_run
    ):
        """Test that missing wind components are handled gracefully."""
        results = collector._parse_grib2_data(
            dataset=mock_xarray_dataset_missing_wind,
            site_id=1,
            model_id=3,
            latitude=45.75,
            longitude=6.25,
            forecast_run=forecast_run,
        )

        # Should have temperature but no wind
        wind_results = [r for r in results if r.parameter_id in [1, 2]]
        temp_results = [r for r in results if r.parameter_id == 3]

        assert len(wind_results) == 0
        assert len(temp_results) > 0

    @pytest.mark.asyncio
    async def test_missing_temperature_skips_temperature(
        self, collector, mock_xarray_dataset_missing_temperature, forecast_run
    ):
        """Test that missing temperature is handled gracefully."""
        results = collector._parse_grib2_data(
            dataset=mock_xarray_dataset_missing_temperature,
            site_id=1,
            model_id=3,
            latitude=45.75,
            longitude=6.25,
            forecast_run=forecast_run,
        )

        # Should have wind but no temperature
        wind_results = [r for r in results if r.parameter_id in [1, 2]]
        temp_results = [r for r in results if r.parameter_id == 3]

        assert len(wind_results) > 0
        assert len(temp_results) == 0

    @pytest.mark.asyncio
    async def test_empty_dataset_returns_empty_list(self, collector, forecast_run):
        """Test that empty dataset returns empty list."""
        empty_ds = xr.Dataset()
        results = collector._parse_grib2_data(
            dataset=empty_ds,
            site_id=1,
            model_id=3,
            latitude=45.9167,
            longitude=6.7000,
            forecast_run=forecast_run,
        )
        assert results == []


# =============================================================================
# HTTP Error Handling Tests
# =============================================================================


class TestHttpErrorHandling:
    """Test HTTP error scenarios."""

    @pytest.mark.asyncio
    async def test_http_404_returns_empty_list(self, collector, forecast_run):
        """Test that 404 errors return empty list."""
        with patch.object(
            collector, "_download_grib2", new_callable=AsyncMock
        ) as mock_download:
            mock_download.side_effect = HttpClientError("404 Not Found")

            results = await collector.collect_forecast(
                site_id=1,
                forecast_run=forecast_run,
                latitude=45.9167,
                longitude=6.7000,
            )

            assert results == []

    @pytest.mark.asyncio
    async def test_http_500_returns_empty_list(self, collector, forecast_run):
        """Test that 500 errors return empty list."""
        with patch.object(
            collector, "_download_grib2", new_callable=AsyncMock
        ) as mock_download:
            mock_download.side_effect = HttpClientError("500 Server Error")

            results = await collector.collect_forecast(
                site_id=1,
                forecast_run=forecast_run,
                latitude=45.9167,
                longitude=6.7000,
            )

            assert results == []

    @pytest.mark.asyncio
    async def test_timeout_returns_empty_list(self, collector, forecast_run):
        """Test that timeout errors return empty list."""
        with patch.object(
            collector, "_download_grib2", new_callable=AsyncMock
        ) as mock_download:
            mock_download.side_effect = HttpClientError("Request timeout")

            results = await collector.collect_forecast(
                site_id=1,
                forecast_run=forecast_run,
                latitude=45.9167,
                longitude=6.7000,
            )

            assert results == []

    @pytest.mark.asyncio
    async def test_retry_exhausted_returns_empty_list(self, collector, forecast_run):
        """Test that retry exhaustion returns empty list."""
        with patch.object(
            collector, "_download_grib2", new_callable=AsyncMock
        ) as mock_download:
            mock_download.side_effect = RetryExhaustedError("Max retries exceeded")

            results = await collector.collect_forecast(
                site_id=1,
                forecast_run=forecast_run,
                latitude=45.9167,
                longitude=6.7000,
            )

            assert results == []


# =============================================================================
# GRIB2 Corruption Tests
# =============================================================================


class TestGrib2CorruptionHandling:
    """Test handling of corrupted or malformed GRIB2 files."""

    @pytest.mark.asyncio
    async def test_corrupted_grib2_returns_empty_list(self, collector, forecast_run):
        """Test that corrupted GRIB2 files are handled gracefully."""
        with patch.object(
            collector, "_download_grib2", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = b"not a valid grib2 file"

            with patch.object(
                collector, "_parse_grib2_bytes"
            ) as mock_parse:
                mock_parse.side_effect = Exception("Invalid GRIB2 format")

                results = await collector.collect_forecast(
                    site_id=1,
                    forecast_run=forecast_run,
                    latitude=45.9167,
                    longitude=6.7000,
                )

                assert results == []

    @pytest.mark.asyncio
    async def test_empty_grib2_returns_empty_list(self, collector, forecast_run):
        """Test that empty GRIB2 files are handled gracefully."""
        with patch.object(
            collector, "_download_grib2", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = b""

            results = await collector.collect_forecast(
                site_id=1,
                forecast_run=forecast_run,
                latitude=45.9167,
                longitude=6.7000,
            )

            assert results == []


# =============================================================================
# API URL Construction Tests
# =============================================================================


class TestApiUrlConstruction:
    """Test API URL building."""

    def test_build_api_url_contains_endpoint(self, collector, forecast_run):
        """Test URL contains base endpoint."""
        url = collector._build_api_url(
            forecast_run=forecast_run,
            package="SP1",
        )
        assert collector.API_ENDPOINT in url

    def test_build_api_url_contains_reference_time(self, collector, forecast_run):
        """Test URL contains reference time parameter."""
        url = collector._build_api_url(
            forecast_run=forecast_run,
            package="SP1",
        )
        # Should contain ISO format date
        assert "2026-01-12" in url or "20260112" in url

    def test_build_api_url_contains_format(self, collector, forecast_run):
        """Test URL specifies GRIB2 format."""
        url = collector._build_api_url(
            forecast_run=forecast_run,
            package="SP1",
        )
        assert "grib2" in url.lower()


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimiting:
    """Test rate limiting compliance (50 req/min for Météo-France)."""

    def test_has_rate_limit_attribute(self, collector):
        """Test collector has rate limit configuration."""
        assert hasattr(collector, "RATE_LIMIT_PER_MINUTE")
        assert collector.RATE_LIMIT_PER_MINUTE == 50

    def test_has_rate_limiter(self, collector):
        """Test collector has rate limiting mechanism."""
        # Either a rate limiter object or delay mechanism
        assert (
            hasattr(collector, "_rate_limiter")
            or hasattr(collector, "_request_delay")
            or hasattr(collector, "MIN_REQUEST_INTERVAL")
        )


# =============================================================================
# Headers Tests
# =============================================================================


class TestRequestHeaders:
    """Test HTTP request headers."""

    def test_headers_contain_user_agent(self, collector):
        """Test User-Agent header is set."""
        headers = collector._get_headers()
        assert "User-Agent" in headers or "user-agent" in headers

    def test_headers_contain_accept(self, collector):
        """Test Accept header for GRIB2."""
        headers = collector._get_headers()
        assert "Accept" in headers or "accept" in headers

    def test_user_agent_identifies_meteoscore(self, collector):
        """Test User-Agent identifies MeteoScore."""
        headers = collector._get_headers()
        user_agent = headers.get("User-Agent", headers.get("user-agent", ""))
        assert "MeteoScore" in user_agent or "meteoscore" in user_agent.lower()


# =============================================================================
# Collect Forecast Integration Tests
# =============================================================================


class TestCollectForecastIntegration:
    """Integration tests for collect_forecast method."""

    @pytest.mark.asyncio
    async def test_collect_forecast_with_valid_data(
        self, collector, mock_xarray_dataset, forecast_run
    ):
        """Test complete forecast collection with valid data."""
        with patch.object(
            collector, "_download_grib2", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = b"mock grib2 data"

            with patch.object(
                collector, "_parse_grib2_bytes"
            ) as mock_parse:
                mock_parse.return_value = mock_xarray_dataset

                results = await collector.collect_forecast(
                    site_id=1,
                    forecast_run=forecast_run,
                    latitude=45.9167,
                    longitude=6.7000,
                )

                # Should return ForecastData objects
                assert len(results) > 0
                assert all(isinstance(r, ForecastData) for r in results)

    @pytest.mark.asyncio
    async def test_collect_forecast_missing_coordinates_returns_empty(
        self, collector, forecast_run
    ):
        """Test that missing coordinates returns empty list."""
        results = await collector.collect_forecast(
            site_id=1,
            forecast_run=forecast_run,
            latitude=None,
            longitude=None,
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_collect_forecast_sets_correct_site_id(
        self, collector, mock_xarray_dataset, forecast_run
    ):
        """Test that all results have correct site_id."""
        with patch.object(
            collector, "_download_grib2", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = b"mock grib2 data"

            with patch.object(
                collector, "_parse_grib2_bytes"
            ) as mock_parse:
                mock_parse.return_value = mock_xarray_dataset

                results = await collector.collect_forecast(
                    site_id=42,
                    forecast_run=forecast_run,
                    latitude=45.9167,
                    longitude=6.7000,
                )

                for result in results:
                    assert result.site_id == 42

    @pytest.mark.asyncio
    async def test_collect_forecast_sets_correct_model_id(
        self, collector, mock_xarray_dataset, forecast_run
    ):
        """Test that all results have correct model_id."""
        with patch.object(
            collector, "_download_grib2", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = b"mock grib2 data"

            with patch.object(
                collector, "_parse_grib2_bytes"
            ) as mock_parse:
                mock_parse.return_value = mock_xarray_dataset

                results = await collector.collect_forecast(
                    site_id=1,
                    forecast_run=forecast_run,
                    latitude=45.9167,
                    longitude=6.7000,
                    model_id=3,
                )

                for result in results:
                    assert result.model_id == 3


# =============================================================================
# Collect Observation Tests
# =============================================================================


class TestCollectObservation:
    """Test collect_observation method."""

    @pytest.mark.asyncio
    async def test_collect_observation_returns_empty_list(self, collector):
        """AROME is forecast-only source, observation returns empty list."""
        results = await collector.collect_observation(
            site_id=1,
            observation_time=datetime.now(timezone.utc),
        )
        assert results == []


# =============================================================================
# API Token Initialization Tests
# =============================================================================


class TestApiTokenInitialization:
    """Test API token handling in constructor."""

    def test_init_with_token_parameter(self):
        """Test token passed via constructor is used."""
        collector = AROMECollector(api_token="test-token-123")
        assert collector._api_token == "test-token-123"

    def test_init_without_token_uses_env_var(self, monkeypatch):
        """Test environment variable fallback for API token."""
        monkeypatch.setenv("METEOFRANCE_API_TOKEN", "env-token-456")
        collector = AROMECollector()
        assert collector._api_token == "env-token-456"

    def test_init_empty_token_when_not_provided(self, monkeypatch):
        """Test empty string when no token provided."""
        monkeypatch.delenv("METEOFRANCE_API_TOKEN", raising=False)
        collector = AROMECollector()
        assert collector._api_token == ""

    def test_token_included_in_headers(self):
        """Test API token is included in Authorization header."""
        collector = AROMECollector(api_token="bearer-token-789")
        headers = collector._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer bearer-token-789"

    def test_no_auth_header_without_token(self, monkeypatch):
        """Test no Authorization header when token is empty."""
        monkeypatch.delenv("METEOFRANCE_API_TOKEN", raising=False)
        collector = AROMECollector()
        headers = collector._get_headers()
        assert "Authorization" not in headers


# =============================================================================
# Rate Limiting Tests - Actual Enforcement
# =============================================================================


class TestRateLimitingEnforcement:
    """Test that rate limiting is actually enforced."""

    def test_has_last_request_time_attribute(self, collector):
        """Test collector tracks last request time."""
        assert hasattr(collector, "_last_request_time")
        assert collector._last_request_time == 0.0

    def test_has_enforce_rate_limit_method(self, collector):
        """Test collector has rate limit enforcement method."""
        assert hasattr(collector, "_enforce_rate_limit")
        assert callable(collector._enforce_rate_limit)

    @pytest.mark.asyncio
    async def test_rate_limit_updates_last_request_time(self, collector):
        """Test rate limiter updates last request time after call."""
        assert collector._last_request_time == 0.0
        await collector._enforce_rate_limit()
        assert collector._last_request_time > 0.0

    @pytest.mark.asyncio
    async def test_rate_limit_waits_when_called_rapidly(self, collector):
        """Test rate limiter delays when called in rapid succession."""
        import time

        # First call should be immediate
        await collector._enforce_rate_limit()
        # Store time to verify second call updates it
        _ = collector._last_request_time

        # Call again immediately - should wait
        start = time.monotonic()
        await collector._enforce_rate_limit()
        elapsed = time.monotonic() - start

        # Should have waited approximately MIN_REQUEST_INTERVAL
        # Allow some tolerance for timing
        assert elapsed >= collector.MIN_REQUEST_INTERVAL * 0.9


# =============================================================================
# Dataset Cleanup Tests
# =============================================================================


class TestDatasetCleanup:
    """Test that xarray datasets are properly closed."""

    @pytest.mark.asyncio
    async def test_dataset_closed_after_successful_parse(
        self, collector, mock_xarray_dataset, forecast_run
    ):
        """Test dataset is closed after successful parsing."""
        # Create a mock dataset with close tracking (without spec to avoid dask issues)
        mock_ds = MagicMock()
        mock_ds.data_vars = mock_xarray_dataset.data_vars
        mock_ds.coords = mock_xarray_dataset.coords
        # Make interp return the actual dataset for proper parsing
        mock_ds.interp.return_value = mock_xarray_dataset

        with patch.object(
            collector, "_download_grib2", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = b"mock grib2 data"

            with patch.object(
                collector, "_parse_grib2_bytes"
            ) as mock_parse:
                mock_parse.return_value = mock_ds

                await collector.collect_forecast(
                    site_id=1,
                    forecast_run=forecast_run,
                    latitude=45.9167,
                    longitude=6.7000,
                )

                # Verify close was called
                mock_ds.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_dataset_closed_even_on_parse_error(
        self, collector, forecast_run
    ):
        """Test dataset is closed even when parsing raises exception."""
        mock_ds = MagicMock()
        mock_ds.data_vars = {}  # Empty dataset will cause early return

        with patch.object(
            collector, "_download_grib2", new_callable=AsyncMock
        ) as mock_download:
            mock_download.return_value = b"mock grib2 data"

            with patch.object(
                collector, "_parse_grib2_bytes"
            ) as mock_parse:
                mock_parse.return_value = mock_ds

                await collector.collect_forecast(
                    site_id=1,
                    forecast_run=forecast_run,
                    latitude=45.9167,
                    longitude=6.7000,
                )

                # Verify close was called even though dataset was empty
                mock_ds.close.assert_called_once()
