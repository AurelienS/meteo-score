"""TDD tests for MeteoParapenteCollector.

These tests are written FIRST following TDD approach (Red -> Green -> Refactor).
Tests use mocked HTTP responses - NEVER call real API in tests.

API Documentation (discovered via research):
- Endpoint: https://data0.meteo-parapente.com/data.php
- Parameters:
  - run: Forecast run time (YYYYMMDDHH format)
  - location: Coordinates as lat,lon
  - date: Target date (YYYYMMDD format)
  - plot: "sounding" for temperature data
- Response: JSON with gridCoords, data (keyed by hour), status, time
- Data fields per hour:
  - tc: Temperature in °C (list, index 0 = surface)
  - umet/vmet: Wind U/V components in m/s (list, index 0 = surface)
  - z: Altitude levels in meters
  - ter: Terrain altitude
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def valid_api_response() -> dict:
    """Mock valid Meteo-Parapente API response.

    Based on real API response structure discovered during research.
    """
    return {
        "gridCoords": {
            "domain": 2,
            "sn": 558,
            "we": 554,
            "lat": 45.947,
            "lon": 6.7391,
            "latDiff": 0,
            "lonDiff": 0,
        },
        "status": "ok",
        "time": 1736600000,
        "data": {
            "06:00": {
                "tc": [2.5, 1.8, 0.5, -1.2],  # Temperature at altitude levels
                "td": [0.5, -0.2, -2.0, -4.5],  # Dew point
                "z": [1365.0, 1500.0, 2000.0, 2500.0],  # Altitude levels
                "ter": 1357.4,  # Terrain altitude
                "umet": [3.0, 5.0, 8.0, 12.0],  # U wind component (m/s)
                "vmet": [4.0, 6.0, 10.0, 15.0],  # V wind component (m/s)
                "p": [865.0, 850.0, 800.0, 750.0],  # Pressure (hPa)
                "pblh": 300.0,
                "ths": [0, 0, 0, 0],
                "thr": [10, 14, 18, 22],
            },
            "12:00": {
                "tc": [8.5, 6.2, 3.0, -2.0],
                "td": [3.0, 1.5, -1.0, -6.0],
                "z": [1365.1, 1500.0, 2000.0, 2500.0],
                "ter": 1357.4,
                "umet": [-2.0, -1.0, 2.0, 5.0],  # Negative = from east
                "vmet": [-3.0, -2.0, 1.0, 4.0],  # Negative = from north
                "p": [864.9, 849.5, 799.0, 749.0],
                "pblh": 500.0,
                "ths": [0, 0, 0, 0],
                "thr": [10, 14, 18, 22],
            },
            "18:00": {
                "tc": [5.0, 3.5, 0.5, -3.0],
                "td": [1.0, 0.0, -2.5, -7.0],
                "z": [1365.0, 1500.0, 2000.0, 2500.0],
                "ter": 1357.4,
                "umet": [0.0, 1.0, 3.0, 6.0],
                "vmet": [5.0, 7.0, 10.0, 12.0],
                "p": [865.0, 850.0, 800.0, 750.0],
                "pblh": 200.0,
                "ths": [0, 0, 0, 0],
                "thr": [10, 14, 18, 22],
            },
        },
    }


@pytest.fixture
def response_missing_fields() -> dict:
    """API response with missing optional fields."""
    return {
        "gridCoords": {"lat": 45.947, "lon": 6.7391},
        "status": "ok",
        "time": 1736600000,
        "data": {
            "12:00": {
                "tc": [5.0],
                "z": [1365.0],
                "ter": 1357.4,
                "umet": [2.0],
                "vmet": [3.0],
                # Missing: td, p, pblh, ths, thr
            },
        },
    }


@pytest.fixture
def response_empty_data() -> dict:
    """API response with empty data section."""
    return {
        "gridCoords": {"lat": 45.947, "lon": 6.7391},
        "status": "ok",
        "time": 1736600000,
        "data": {},
    }


@pytest.fixture
def response_bad_status() -> dict:
    """API response with error status."""
    return {
        "message": "Invalid coordinates",
        "status": "bad_format",
        "time": 1736600000,
    }


# =============================================================================
# Test: Basic Collector Structure
# =============================================================================


class TestMeteoParapenteCollectorStructure:
    """Tests for collector class structure and interface."""

    def test_collector_inherits_base_collector(self):
        """MeteoParapenteCollector must inherit from BaseCollector."""
        from backend.collectors.base import BaseCollector
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        assert issubclass(MeteoParapenteCollector, BaseCollector)

    def test_collector_has_required_attributes(self):
        """Collector must have name, source, and API_ENDPOINT attributes."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        assert hasattr(collector, "name")
        assert hasattr(collector, "source")
        assert hasattr(collector, "API_ENDPOINT")
        assert collector.name == "MeteoParapenteCollector"
        assert collector.source == "Meteo-Parapente"
        assert "data0.meteo-parapente.com" in collector.API_ENDPOINT

    def test_collector_has_collect_forecast_method(self):
        """Collector must implement async collect_forecast method."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        assert hasattr(collector, "collect_forecast")
        import asyncio

        assert asyncio.iscoroutinefunction(collector.collect_forecast)


# =============================================================================
# Test: API Response Parsing
# =============================================================================


class TestResponseParsing:
    """Tests for parsing Meteo-Parapente API responses."""

    @pytest.mark.asyncio
    async def test_parse_valid_response_returns_forecast_data_list(
        self, valid_api_response
    ):
        """Valid response should return list of ForecastData objects."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector
        from backend.core.data_models import ForecastData

        collector = MeteoParapenteCollector()

        with patch.object(collector, "_fetch_api", return_value=valid_api_response):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(item, ForecastData) for item in result)

    @pytest.mark.asyncio
    async def test_parse_extracts_all_hours(self, valid_api_response):
        """Parser should extract data for all hours in response."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        with patch.object(collector, "_fetch_api", return_value=valid_api_response):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        # 3 hours * 3 parameters = 9 ForecastData objects
        hours_in_response = len(valid_api_response["data"])  # 3 hours
        parameters = 3  # wind_speed, wind_direction, temperature
        expected_count = hours_in_response * parameters
        assert len(result) == expected_count

    @pytest.mark.asyncio
    async def test_forecast_data_has_correct_site_id(self, valid_api_response):
        """ForecastData should have the correct site_id."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        test_site_id = 42

        with patch.object(collector, "_fetch_api", return_value=valid_api_response):
            result = await collector.collect_forecast(
                site_id=test_site_id,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        assert all(fd.site_id == test_site_id for fd in result)


# =============================================================================
# Test: Wind Data Extraction
# =============================================================================


class TestWindExtraction:
    """Tests for wind speed and direction extraction from umet/vmet."""

    @pytest.mark.asyncio
    async def test_wind_speed_calculated_correctly(self, valid_api_response):
        """Wind speed should be sqrt(u² + v²) converted to km/h."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        with patch.object(collector, "_fetch_api", return_value=valid_api_response):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        # Find wind speed for 06:00
        # umet=3.0, vmet=4.0 -> speed = sqrt(9+16) = 5 m/s = 18 km/h
        wind_speed_data = [fd for fd in result if fd.parameter_id == 1]
        hour_06_data = [fd for fd in wind_speed_data if fd.valid_time.hour == 6]

        if hour_06_data:
            expected_speed = Decimal("18.0")
            assert hour_06_data[0].value == expected_speed

    @pytest.mark.asyncio
    async def test_wind_direction_calculated_correctly(self, valid_api_response):
        """Wind direction should be meteorological convention (where wind comes FROM)."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        with patch.object(collector, "_fetch_api", return_value=valid_api_response):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        wind_dir_data = [fd for fd in result if fd.parameter_id == 2]

        # Verify direction is in valid range
        for fd in wind_dir_data:
            assert Decimal("0") <= fd.value <= Decimal("360")

    def test_wind_calculation_pure_north(self):
        """Wind from pure north (u=0, v<0) should give direction 0° or 360°."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        direction = collector._calculate_wind_direction(u=0.0, v=-5.0)
        assert direction == Decimal("0") or direction == Decimal("360")

    def test_wind_calculation_pure_east(self):
        """Wind from pure east (u<0, v=0) should give direction 90°."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        direction = collector._calculate_wind_direction(u=-5.0, v=0.0)
        assert direction == Decimal("90")

    def test_wind_calculation_pure_south(self):
        """Wind from pure south (u=0, v>0) should give direction 180°."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        direction = collector._calculate_wind_direction(u=0.0, v=5.0)
        assert direction == Decimal("180")

    def test_wind_calculation_pure_west(self):
        """Wind from pure west (u>0, v=0) should give direction 270°."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        direction = collector._calculate_wind_direction(u=5.0, v=0.0)
        assert direction == Decimal("270")

    def test_wind_speed_zero_when_calm(self):
        """Wind speed should be 0 when u=0 and v=0."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        speed = collector._calculate_wind_speed(u=0.0, v=0.0)
        assert speed == Decimal("0")


# =============================================================================
# Test: Temperature Extraction
# =============================================================================


class TestTemperatureExtraction:
    """Tests for temperature extraction from tc field."""

    @pytest.mark.asyncio
    async def test_temperature_extracted_from_surface(self, valid_api_response):
        """Temperature should be extracted from tc[0] (surface level)."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        with patch.object(collector, "_fetch_api", return_value=valid_api_response):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        # Find temperature for 06:00 - tc[0] = 2.5°C
        temp_data = [fd for fd in result if fd.parameter_id == 3]
        hour_06_temp = [fd for fd in temp_data if fd.valid_time.hour == 6]

        if hour_06_temp:
            assert hour_06_temp[0].value == Decimal("2.5")

    @pytest.mark.asyncio
    async def test_temperature_in_celsius(self, valid_api_response):
        """Temperature values should be in Celsius (reasonable range)."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        with patch.object(collector, "_fetch_api", return_value=valid_api_response):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        temp_data = [fd for fd in result if fd.parameter_id == 3]
        for fd in temp_data:
            assert Decimal("-50") <= fd.value <= Decimal("50")


# =============================================================================
# Test: Forecast Horizon Calculation
# =============================================================================


class TestForecastHorizon:
    """Tests for forecast horizon (H+X hours) calculation."""

    @pytest.mark.asyncio
    async def test_horizon_calculated_from_valid_time(self, valid_api_response):
        """Horizon should be hours between forecast_run and valid_time."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        forecast_run = datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc)

        with patch.object(collector, "_fetch_api", return_value=valid_api_response):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=forecast_run,
                latitude=45.9167,
                longitude=6.7000,
            )

        for fd in result:
            expected_horizon = int(
                (fd.valid_time - forecast_run).total_seconds() / 3600
            )
            assert fd.horizon == expected_horizon

    @pytest.mark.asyncio
    async def test_valid_time_parsed_correctly(self, valid_api_response):
        """Valid time should be parsed from hour key and date parameter."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        forecast_run = datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc)

        with patch.object(collector, "_fetch_api", return_value=valid_api_response):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=forecast_run,
                latitude=45.9167,
                longitude=6.7000,
            )

        for fd in result:
            assert fd.valid_time.tzinfo is not None


# =============================================================================
# Test: Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_http_error_returns_empty_list(self):
        """HTTP errors should return empty list and log warning."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector
        from backend.collectors.utils import HttpClientError

        collector = MeteoParapenteCollector()

        with patch.object(
            collector, "_fetch_api", side_effect=HttpClientError("404 Not Found", 404)
        ):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_json_parse_error_returns_empty_list(self):
        """JSON parsing errors should return empty list."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        with patch.object(collector, "_fetch_api", return_value="not valid json"):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_bad_status_returns_empty_list(self, response_bad_status):
        """Response with bad_format status should return empty list."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        with patch.object(collector, "_fetch_api", return_value=response_bad_status):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_empty_data_returns_empty_list(self, response_empty_data):
        """Response with empty data section should return empty list."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        with patch.object(collector, "_fetch_api", return_value=response_empty_data):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_missing_fields_handled_gracefully(self, response_missing_fields):
        """Missing optional fields should not cause crash."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        with patch.object(
            collector, "_fetch_api", return_value=response_missing_fields
        ):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        assert isinstance(result, list)


# =============================================================================
# Test: Data Validation
# =============================================================================


class TestDataValidation:
    """Tests for data validation (aberrant value detection)."""

    @pytest.mark.asyncio
    async def test_aberrant_wind_speed_skipped(self):
        """Wind speed > 200 km/h should be skipped with warning."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        aberrant_response = {
            "gridCoords": {"lat": 45.947, "lon": 6.7391},
            "status": "ok",
            "time": 1736600000,
            "data": {
                "12:00": {
                    "tc": [5.0],
                    "z": [1365.0],
                    "ter": 1357.4,
                    "umet": [100.0],  # Aberrant! 100 m/s = 360 km/h
                    "vmet": [0.0],
                    "p": [865.0],
                },
            },
        }

        with patch.object(collector, "_fetch_api", return_value=aberrant_response):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        wind_speeds = [fd for fd in result if fd.parameter_id == 1]
        assert len(wind_speeds) == 0

    @pytest.mark.asyncio
    async def test_aberrant_temperature_skipped(self):
        """Temperature outside -50 to +50°C should be skipped."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        aberrant_response = {
            "gridCoords": {"lat": 45.947, "lon": 6.7391},
            "status": "ok",
            "time": 1736600000,
            "data": {
                "12:00": {
                    "tc": [100.0],  # Aberrant! 100°C
                    "z": [1365.0],
                    "ter": 1357.4,
                    "umet": [2.0],
                    "vmet": [3.0],
                    "p": [865.0],
                },
            },
        }

        with patch.object(collector, "_fetch_api", return_value=aberrant_response):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
            )

        temperatures = [fd for fd in result if fd.parameter_id == 3]
        assert len(temperatures) == 0

    def test_validate_wind_speed_in_range(self):
        """Wind speed 0-200 km/h should be valid."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        assert collector._is_valid_value("wind_speed", Decimal("0")) is True
        assert collector._is_valid_value("wind_speed", Decimal("100")) is True
        assert collector._is_valid_value("wind_speed", Decimal("200")) is True
        assert collector._is_valid_value("wind_speed", Decimal("201")) is False
        assert collector._is_valid_value("wind_speed", Decimal("-1")) is False

    def test_validate_wind_direction_in_range(self):
        """Wind direction 0-360° should be valid."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        assert collector._is_valid_value("wind_direction", Decimal("0")) is True
        assert collector._is_valid_value("wind_direction", Decimal("180")) is True
        assert collector._is_valid_value("wind_direction", Decimal("360")) is True
        assert collector._is_valid_value("wind_direction", Decimal("361")) is False
        assert collector._is_valid_value("wind_direction", Decimal("-1")) is False

    def test_validate_temperature_in_range(self):
        """Temperature -50 to +50°C should be valid."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        assert collector._is_valid_value("temperature", Decimal("-50")) is True
        assert collector._is_valid_value("temperature", Decimal("0")) is True
        assert collector._is_valid_value("temperature", Decimal("50")) is True
        assert collector._is_valid_value("temperature", Decimal("51")) is False
        assert collector._is_valid_value("temperature", Decimal("-51")) is False


# =============================================================================
# Test: API URL Construction
# =============================================================================


class TestApiUrlConstruction:
    """Tests for API URL and request construction."""

    def test_build_api_url_with_coordinates(self):
        """API URL should include location parameter with lat,lon."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        url = collector._build_api_url(
            latitude=45.9167,
            longitude=6.7000,
            forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
            target_date=datetime(2026, 1, 12, tzinfo=timezone.utc),
        )

        assert "location=45.9167,6.7" in url
        assert "run=2026011106" in url
        assert "date=20260112" in url
        assert "plot=sounding" in url

    def test_build_api_url_uses_correct_endpoint(self):
        """API URL should use the correct base endpoint."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        url = collector._build_api_url(
            latitude=45.9167,
            longitude=6.7000,
            forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
            target_date=datetime(2026, 1, 12, tzinfo=timezone.utc),
        )

        assert url.startswith("https://data0.meteo-parapente.com/data.php")


# =============================================================================
# Test: Required Headers
# =============================================================================


class TestRequiredHeaders:
    """Tests for required HTTP headers."""

    def test_get_headers_includes_origin(self):
        """Headers should include origin: https://meteo-parapente.com."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        headers = collector._get_headers()

        assert headers.get("origin") == "https://meteo-parapente.com"

    def test_get_headers_includes_referer(self):
        """Headers should include referer: https://meteo-parapente.com/."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        headers = collector._get_headers()

        assert headers.get("referer") == "https://meteo-parapente.com/"

    def test_get_headers_includes_user_agent(self):
        """Headers should include User-Agent identifying MétéoScore."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        headers = collector._get_headers()

        assert "user-agent" in headers
        assert "MeteoScore" in headers["user-agent"]


# =============================================================================
# Test: Model and Parameter ID Mapping
# =============================================================================


class TestIdMapping:
    """Tests for model_id and parameter_id mapping."""

    @pytest.mark.asyncio
    async def test_model_id_set_correctly(self, valid_api_response):
        """All ForecastData should have correct model_id for Meteo-Parapente."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        with patch.object(collector, "_fetch_api", return_value=valid_api_response):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
                model_id=2,
            )

        assert all(fd.model_id == 2 for fd in result)

    @pytest.mark.asyncio
    async def test_parameter_ids_mapped_correctly(self, valid_api_response):
        """Parameter IDs should map to wind_speed=1, wind_direction=2, temperature=3."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()

        with patch.object(collector, "_fetch_api", return_value=valid_api_response):
            result = await collector.collect_forecast(
                site_id=1,
                forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
                latitude=45.9167,
                longitude=6.7000,
                model_id=2,
                parameter_ids={"wind_speed": 1, "wind_direction": 2, "temperature": 3},
            )

        parameter_ids = {fd.parameter_id for fd in result}
        assert parameter_ids == {1, 2, 3}


# =============================================================================
# Test: collect_observation Not Implemented
# =============================================================================


class TestCollectObservation:
    """Tests for collect_observation method (not implemented for this source)."""

    @pytest.mark.asyncio
    async def test_collect_observation_returns_empty_list(self):
        """collect_observation should return empty list (forecast-only source)."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        result = await collector.collect_observation(
            site_id=1,
            observation_time=datetime(2026, 1, 11, 12, 0, tzinfo=timezone.utc),
        )

        assert result == []


# =============================================================================
# Test: Missing Coordinates
# =============================================================================


class TestMissingCoordinates:
    """Tests for handling missing latitude/longitude."""

    @pytest.mark.asyncio
    async def test_missing_latitude_returns_empty_list(self):
        """Missing latitude should return empty list with warning."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        result = await collector.collect_forecast(
            site_id=1,
            forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
            longitude=6.7000,  # latitude missing
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_missing_longitude_returns_empty_list(self):
        """Missing longitude should return empty list with warning."""
        from backend.collectors.meteo_parapente import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        result = await collector.collect_forecast(
            site_id=1,
            forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
            latitude=45.9167,  # longitude missing
        )

        assert result == []
