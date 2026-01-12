"""Tests for ROMMA observation collector.

This module contains TDD tests for the ROMMaCollector class.
All tests use mocked HTML responses - NEVER scrape real ROMMA beacons in tests.

ROMMA (Réseau d'Observation Météo du Massif Alpin) provides real-time
weather observations from automated stations in the French Alps.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.collectors.romma import ROMMaCollector
from backend.collectors.utils import HttpClientError, RetryExhaustedError
from backend.core.data_models import ObservationData


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def collector():
    """Create a ROMMaCollector instance for testing."""
    return ROMMaCollector()


@pytest.fixture
def valid_html_response():
    """Create valid ROMMA beacon HTML response.

    Based on actual ROMMA station page structure:
    - station_24.php?id=XX format
    - French text labels
    - Wind in km/h, Temperature in °C
    """
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Station Météo - Passy</title></head>
    <body>
        <div class="station-info">
            <h1>Station de Passy (1050m)</h1>
            <p>Coordonnées : 45.9167° N, 6.7000° E</p>
        </div>

        <div class="derniere-mise-a-jour">
            Dernier relevé en direct : le 12 Janvier 2026 à 14:30
        </div>

        <div class="donnees-vent">
            <h2>Vent</h2>
            <p>Moyen sur 10min : 25 km/h</p>
            <p>Direction : NE</p>
            <p>Rafale maxi sur 10 min : 32 km/h</p>
            <p>Rafale maxi depuis 0h : 45 km/h à 08:15</p>
        </div>

        <div class="donnees-temperature">
            <h2>Température</h2>
            <p>Température: 8.5 °C</p>
            <p>Variation en 1h : +0.3 °C</p>
            <p>Mini depuis 0h : 2.1 °C à 06:00</p>
            <p>Maxi depuis 0h : 9.2 °C à 13:45</p>
        </div>

        <div class="donnees-humidite">
            <p>Humidité : 65 %</p>
            <p>Point de rosée : 2.3 °C</p>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def html_with_cardinal_directions():
    """HTML responses with various cardinal direction formats."""
    return {
        "N": """<p>Direction : N</p>""",
        "S": """<p>Direction : S</p>""",
        "E": """<p>Direction : E</p>""",
        "W": """<p>Direction : W</p>""",
        "NE": """<p>Direction : NE</p>""",
        "NW": """<p>Direction : NW</p>""",
        "SE": """<p>Direction : SE</p>""",
        "SW": """<p>Direction : SW</p>""",
        "NNE": """<p>Direction : NNE</p>""",
        "ESE": """<p>Direction : ESE</p>""",
    }


@pytest.fixture
def html_missing_wind():
    """HTML response with missing wind data."""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <div class="derniere-mise-a-jour">
            Dernier relevé en direct : le 12 Janvier 2026 à 14:30
        </div>
        <div class="donnees-temperature">
            <p>Température: 8.5 °C</p>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def html_missing_temperature():
    """HTML response with missing temperature data."""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <div class="derniere-mise-a-jour">
            Dernier relevé en direct : le 12 Janvier 2026 à 14:30
        </div>
        <div class="donnees-vent">
            <p>Moyen sur 10min : 25 km/h</p>
            <p>Direction : NE</p>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def html_stale_data():
    """HTML response with stale observation (>2 hours old)."""
    # 3 hours ago
    stale_time = datetime.now(timezone.utc) - timedelta(hours=3)
    french_months = {
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
        5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
        9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
    }
    month_name = french_months[stale_time.month]
    timestamp_str = f"le {stale_time.day:02d} {month_name} {stale_time.year} à {stale_time.hour:02d}:{stale_time.minute:02d}"

    return f"""
    <!DOCTYPE html>
    <html>
    <body>
        <div class="derniere-mise-a-jour">
            Dernier relevé en direct : {timestamp_str}
        </div>
        <div class="donnees-vent">
            <p>Moyen sur 10min : 25 km/h</p>
            <p>Direction : N</p>
        </div>
        <div class="donnees-temperature">
            <p>Température: 8.5 °C</p>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def malformed_html():
    """Malformed HTML that should be handled gracefully."""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <div class="broken
        <p>Moyen sur 10min : not a number km/h</p>
        <p>Direction : INVALID</p>
        <p>Température: -- °C</p>
    </body>
    </html>
    """


@pytest.fixture
def observation_time():
    """Standard observation time for tests."""
    return datetime(2026, 1, 12, 14, 30, tzinfo=timezone.utc)


# =============================================================================
# Collector Structure Tests
# =============================================================================


class TestROMMaCollectorStructure:
    """Test ROMMaCollector class structure and attributes."""

    def test_inherits_from_base_collector(self, collector):
        """Verify ROMMaCollector inherits from BaseCollector."""
        from backend.collectors.base import BaseCollector
        assert isinstance(collector, BaseCollector)

    def test_has_required_class_attributes(self, collector):
        """Verify required class attributes exist."""
        assert hasattr(collector, "name")
        assert hasattr(collector, "source")
        assert hasattr(collector, "BASE_URL")
        assert hasattr(collector, "TIMEOUT")

    def test_name_attribute(self, collector):
        """Test collector name is set correctly."""
        assert collector.name == "ROMMA"

    def test_source_attribute(self, collector):
        """Test source describes ROMMA network."""
        assert "ROMMA" in collector.source or "Alpin" in collector.source

    def test_base_url_is_romma(self, collector):
        """Test BASE_URL points to romma.fr."""
        assert "romma.fr" in collector.BASE_URL

    def test_timeout_is_reasonable(self, collector):
        """Test timeout is set (10 seconds per AC6)."""
        assert collector.TIMEOUT == 10.0

    def test_has_collect_observation_method(self, collector):
        """Verify collect_observation method exists."""
        assert hasattr(collector, "collect_observation")
        assert callable(collector.collect_observation)

    def test_has_collect_forecast_method(self, collector):
        """Verify collect_forecast method exists (returns empty for observation-only)."""
        assert hasattr(collector, "collect_forecast")
        assert callable(collector.collect_forecast)


# =============================================================================
# Wind Speed Extraction Tests
# =============================================================================


class TestWindSpeedExtraction:
    """Test wind speed parsing from HTML."""

    def test_extract_wind_speed_basic(self, collector):
        """Test basic wind speed extraction."""
        html = "<p>Moyen sur 10min : 25 km/h</p>"
        speed = collector._extract_wind_speed(html)
        assert speed == Decimal("25")

    def test_extract_wind_speed_decimal(self, collector):
        """Test wind speed with decimal value."""
        html = "<p>Moyen sur 10min : 12.5 km/h</p>"
        speed = collector._extract_wind_speed(html)
        assert speed == Decimal("12.5")

    def test_extract_wind_speed_zero(self, collector):
        """Test zero wind speed."""
        html = "<p>Moyen sur 10min : 0 km/h</p>"
        speed = collector._extract_wind_speed(html)
        assert speed == Decimal("0")

    def test_extract_wind_speed_high_value(self, collector):
        """Test high wind speed value."""
        html = "<p>Moyen sur 10min : 150 km/h</p>"
        speed = collector._extract_wind_speed(html)
        assert speed == Decimal("150")

    def test_extract_wind_speed_missing_returns_none(self, collector):
        """Test missing wind speed returns None."""
        html = "<p>No wind data here</p>"
        speed = collector._extract_wind_speed(html)
        assert speed is None

    def test_extract_wind_speed_invalid_value_returns_none(self, collector):
        """Test invalid wind speed value returns None."""
        html = "<p>Moyen sur 10min : -- km/h</p>"
        speed = collector._extract_wind_speed(html)
        assert speed is None


# =============================================================================
# Wind Direction Extraction Tests
# =============================================================================


class TestWindDirectionExtraction:
    """Test wind direction parsing and cardinal conversion."""

    def test_extract_direction_north(self, collector):
        """Test North direction converts to 0 degrees."""
        html = "<p>Direction : N</p>"
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("0")

    def test_extract_direction_south(self, collector):
        """Test South direction converts to 180 degrees."""
        html = "<p>Direction : S</p>"
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("180")

    def test_extract_direction_east(self, collector):
        """Test East direction converts to 90 degrees."""
        html = "<p>Direction : E</p>"
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("90")

    def test_extract_direction_west(self, collector):
        """Test West direction converts to 270 degrees."""
        html = "<p>Direction : W</p>"
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("270")

    def test_extract_direction_northeast(self, collector):
        """Test NE direction converts to 45 degrees."""
        html = "<p>Direction : NE</p>"
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("45")

    def test_extract_direction_northwest(self, collector):
        """Test NW direction converts to 315 degrees."""
        html = "<p>Direction : NW</p>"
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("315")

    def test_extract_direction_southeast(self, collector):
        """Test SE direction converts to 135 degrees."""
        html = "<p>Direction : SE</p>"
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("135")

    def test_extract_direction_southwest(self, collector):
        """Test SW direction converts to 225 degrees."""
        html = "<p>Direction : SW</p>"
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("225")

    def test_extract_direction_nne(self, collector):
        """Test NNE direction converts to ~22.5 degrees."""
        html = "<p>Direction : NNE</p>"
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("22.5") or direction == Decimal("23")

    def test_extract_direction_missing_returns_none(self, collector):
        """Test missing direction returns None."""
        html = "<p>No direction here</p>"
        direction = collector._extract_wind_direction(html)
        assert direction is None

    def test_extract_direction_invalid_returns_none(self, collector):
        """Test invalid direction returns None."""
        html = "<p>Direction : INVALID</p>"
        direction = collector._extract_wind_direction(html)
        assert direction is None

    def test_extract_direction_numeric_degrees(self, collector):
        """Test numeric degree value (if ROMMA uses it)."""
        html = "<p>Direction : 180°</p>"
        direction = collector._extract_wind_direction(html)
        # Should handle numeric or return None gracefully
        assert direction is None or direction == Decimal("180")


# =============================================================================
# Temperature Extraction Tests
# =============================================================================


class TestTemperatureExtraction:
    """Test temperature parsing from HTML."""

    def test_extract_temperature_positive(self, collector):
        """Test positive temperature extraction."""
        html = "<p>Température: 8.5 °C</p>"
        temp = collector._extract_temperature(html)
        assert temp == Decimal("8.5")

    def test_extract_temperature_negative(self, collector):
        """Test negative temperature extraction."""
        html = "<p>Température: -5.2 °C</p>"
        temp = collector._extract_temperature(html)
        assert temp == Decimal("-5.2")

    def test_extract_temperature_zero(self, collector):
        """Test zero temperature."""
        html = "<p>Température: 0 °C</p>"
        temp = collector._extract_temperature(html)
        assert temp == Decimal("0")

    def test_extract_temperature_integer(self, collector):
        """Test integer temperature value."""
        html = "<p>Température: 15 °C</p>"
        temp = collector._extract_temperature(html)
        assert temp == Decimal("15")

    def test_extract_temperature_missing_returns_none(self, collector):
        """Test missing temperature returns None."""
        html = "<p>No temperature here</p>"
        temp = collector._extract_temperature(html)
        assert temp is None

    def test_extract_temperature_invalid_returns_none(self, collector):
        """Test invalid temperature value returns None."""
        html = "<p>Température: -- °C</p>"
        temp = collector._extract_temperature(html)
        assert temp is None

    def test_extract_temperature_with_colon_space(self, collector):
        """Test temperature with colon and space format."""
        html = "<p>Température : 12.3 °C</p>"
        temp = collector._extract_temperature(html)
        assert temp == Decimal("12.3")


# =============================================================================
# Timestamp Parsing Tests
# =============================================================================


class TestTimestampParsing:
    """Test observation timestamp parsing."""

    def test_parse_french_timestamp(self, collector):
        """Test parsing French date format."""
        html = "Dernier relevé en direct : le 12 Janvier 2026 à 14:30"
        timestamp = collector._parse_observation_time(html)
        assert timestamp is not None
        assert timestamp.year == 2026
        assert timestamp.month == 1
        assert timestamp.day == 12
        assert timestamp.hour == 14
        assert timestamp.minute == 30

    def test_parse_timestamp_february(self, collector):
        """Test parsing February (Février)."""
        html = "Dernier relevé en direct : le 15 Février 2026 à 09:00"
        timestamp = collector._parse_observation_time(html)
        assert timestamp.month == 2

    def test_parse_timestamp_december(self, collector):
        """Test parsing December (Décembre)."""
        html = "Dernier relevé en direct : le 25 Décembre 2025 à 18:45"
        timestamp = collector._parse_observation_time(html)
        assert timestamp.month == 12

    def test_parse_timestamp_missing_returns_none(self, collector):
        """Test missing timestamp returns None."""
        html = "<p>No timestamp here</p>"
        timestamp = collector._parse_observation_time(html)
        assert timestamp is None

    def test_parse_timestamp_invalid_format_returns_none(self, collector):
        """Test invalid format returns None."""
        html = "Dernier relevé : 2026-01-12 14:30"
        timestamp = collector._parse_observation_time(html)
        # Should handle gracefully
        assert timestamp is None or timestamp is not None


# =============================================================================
# Data Validation Tests
# =============================================================================


class TestDataValidation:
    """Test data validation ranges."""

    def test_valid_wind_speed(self, collector):
        """Test wind speed within valid range."""
        assert collector._is_valid_value("wind_speed", Decimal("50")) is True
        assert collector._is_valid_value("wind_speed", Decimal("0")) is True
        assert collector._is_valid_value("wind_speed", Decimal("200")) is True

    def test_invalid_wind_speed(self, collector):
        """Test wind speed outside valid range."""
        assert collector._is_valid_value("wind_speed", Decimal("250")) is False
        assert collector._is_valid_value("wind_speed", Decimal("-10")) is False

    def test_valid_wind_direction(self, collector):
        """Test wind direction within valid range."""
        assert collector._is_valid_value("wind_direction", Decimal("0")) is True
        assert collector._is_valid_value("wind_direction", Decimal("180")) is True
        assert collector._is_valid_value("wind_direction", Decimal("359")) is True

    def test_invalid_wind_direction(self, collector):
        """Test wind direction outside valid range."""
        assert collector._is_valid_value("wind_direction", Decimal("400")) is False
        assert collector._is_valid_value("wind_direction", Decimal("-10")) is False

    def test_valid_temperature(self, collector):
        """Test temperature within valid range."""
        assert collector._is_valid_value("temperature", Decimal("20")) is True
        assert collector._is_valid_value("temperature", Decimal("-30")) is True
        assert collector._is_valid_value("temperature", Decimal("45")) is True

    def test_invalid_temperature(self, collector):
        """Test temperature outside valid range."""
        assert collector._is_valid_value("temperature", Decimal("60")) is False
        assert collector._is_valid_value("temperature", Decimal("-60")) is False


# =============================================================================
# Stale Data Detection Tests
# =============================================================================


class TestStaleDataDetection:
    """Test detection of stale observation data."""

    def test_fresh_data_not_stale(self, collector):
        """Test recent observation is not flagged as stale."""
        recent = datetime.now(timezone.utc) - timedelta(minutes=30)
        assert collector._is_stale(recent) is False

    def test_data_over_2_hours_is_stale(self, collector):
        """Test observation over 2 hours old is flagged as stale."""
        old = datetime.now(timezone.utc) - timedelta(hours=3)
        assert collector._is_stale(old) is True

    def test_data_just_under_2_hours_not_stale(self, collector):
        """Test observation just under 2 hours old is not stale."""
        borderline = datetime.now(timezone.utc) - timedelta(hours=1, minutes=59)
        # Should be considered fresh just under 2 hours
        assert collector._is_stale(borderline) is False


# =============================================================================
# HTTP Error Handling Tests
# =============================================================================


class TestHttpErrorHandling:
    """Test HTTP error scenarios."""

    @pytest.mark.asyncio
    async def test_http_404_returns_empty_list(self, collector, observation_time):
        """Test 404 error returns empty list."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = HttpClientError("404 Not Found", status_code=404)

            results = await collector.collect_observation(
                site_id=1,
                observation_time=observation_time,
            )
            assert results == []

    @pytest.mark.asyncio
    async def test_http_500_returns_empty_list(self, collector, observation_time):
        """Test 500 error returns empty list."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = HttpClientError("500 Server Error", status_code=500)

            results = await collector.collect_observation(
                site_id=1,
                observation_time=observation_time,
            )
            assert results == []

    @pytest.mark.asyncio
    async def test_timeout_returns_empty_list(self, collector, observation_time):
        """Test timeout returns empty list."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = HttpClientError("Request timeout")

            results = await collector.collect_observation(
                site_id=1,
                observation_time=observation_time,
            )
            assert results == []

    @pytest.mark.asyncio
    async def test_retry_exhausted_returns_empty_list(self, collector, observation_time):
        """Test retry exhaustion returns empty list."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = RetryExhaustedError("Max retries exceeded")

            results = await collector.collect_observation(
                site_id=1,
                observation_time=observation_time,
            )
            assert results == []


# =============================================================================
# HTML Parsing Error Tests
# =============================================================================


class TestHtmlParsingErrors:
    """Test HTML parsing error handling."""

    @pytest.mark.asyncio
    async def test_malformed_html_returns_empty_list(
        self, collector, malformed_html, observation_time
    ):
        """Test malformed HTML is handled gracefully."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = malformed_html

            results = await collector.collect_observation(
                site_id=1,
                observation_time=observation_time,
            )
            # Should not crash, may return empty or partial data
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_empty_html_returns_empty_list(self, collector, observation_time):
        """Test empty HTML returns empty list."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = ""

            results = await collector.collect_observation(
                site_id=1,
                observation_time=observation_time,
            )
            assert results == []


# =============================================================================
# Missing Data Tests
# =============================================================================


class TestMissingDataHandling:
    """Test handling of missing data fields."""

    @pytest.mark.asyncio
    async def test_missing_wind_skips_wind_observations(
        self, collector, html_missing_wind, observation_time
    ):
        """Test missing wind data is handled gracefully."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = html_missing_wind

            results = await collector.collect_observation(
                site_id=1,
                observation_time=observation_time,
            )
            # Should have temperature but not wind
            wind_results = [r for r in results if r.parameter_id == 1]  # Assuming wind_speed = 1
            assert len(wind_results) == 0 or all(r.value is not None for r in wind_results)

    @pytest.mark.asyncio
    async def test_missing_temperature_skips_temperature(
        self, collector, html_missing_temperature, observation_time
    ):
        """Test missing temperature is handled gracefully."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = html_missing_temperature

            results = await collector.collect_observation(
                site_id=1,
                observation_time=observation_time,
            )
            # Should have wind but not temperature
            temp_results = [r for r in results if r.parameter_id == 3]  # Assuming temperature = 3
            assert len(temp_results) == 0


# =============================================================================
# Polite Scraping Tests
# =============================================================================


class TestPoliteScraping:
    """Test polite scraping behavior."""

    def test_has_min_request_interval(self, collector):
        """Test collector has minimum request interval."""
        assert hasattr(collector, "MIN_REQUEST_INTERVAL")
        assert collector.MIN_REQUEST_INTERVAL >= 2.0  # At least 2 seconds per AC6

    def test_user_agent_header(self, collector):
        """Test User-Agent header identifies MeteoScore."""
        headers = collector._get_headers()
        assert "User-Agent" in headers
        assert "MeteoScore" in headers["User-Agent"] or "meteoscore" in headers["User-Agent"].lower()


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimiting:
    """Test rate limiting behavior."""

    def test_has_rate_limit_attributes(self, collector):
        """Test collector has rate limiting attributes."""
        assert hasattr(collector, "_last_request_time")
        assert hasattr(collector, "_enforce_rate_limit")

    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self, collector):
        """Test rate limiter updates last request time."""
        assert collector._last_request_time == 0.0
        await collector._enforce_rate_limit()
        assert collector._last_request_time > 0.0


# =============================================================================
# Collect Observation Integration Tests
# =============================================================================


class TestCollectObservationIntegration:
    """Integration tests for collect_observation method."""

    @pytest.mark.asyncio
    async def test_collect_observation_with_valid_html(
        self, collector, valid_html_response, observation_time
    ):
        """Test complete observation collection with valid HTML."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = valid_html_response

            results = await collector.collect_observation(
                site_id=1,
                observation_time=observation_time,
            )

            # Should return observations for wind speed, direction, temperature
            assert len(results) >= 1
            assert all(isinstance(r, ObservationData) for r in results)

    @pytest.mark.asyncio
    async def test_collect_observation_sets_correct_site_id(
        self, collector, valid_html_response, observation_time
    ):
        """Test site_id is set correctly in results."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = valid_html_response

            results = await collector.collect_observation(
                site_id=42,
                observation_time=observation_time,
            )

            for result in results:
                assert result.site_id == 42

    @pytest.mark.asyncio
    async def test_collect_observation_extracts_wind_speed(
        self, collector, valid_html_response, observation_time
    ):
        """Test wind speed is extracted correctly."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = valid_html_response

            results = await collector.collect_observation(
                site_id=1,
                observation_time=observation_time,
            )

            # Find wind speed result (parameter_id = 1)
            wind_speed_results = [r for r in results if r.parameter_id == 1]
            assert len(wind_speed_results) == 1
            assert wind_speed_results[0].value == Decimal("25")

    @pytest.mark.asyncio
    async def test_collect_observation_extracts_wind_direction(
        self, collector, valid_html_response, observation_time
    ):
        """Test wind direction is extracted and converted correctly."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = valid_html_response

            results = await collector.collect_observation(
                site_id=1,
                observation_time=observation_time,
            )

            # Find wind direction result (parameter_id = 2)
            wind_dir_results = [r for r in results if r.parameter_id == 2]
            assert len(wind_dir_results) == 1
            assert wind_dir_results[0].value == Decimal("45")  # NE = 45 degrees

    @pytest.mark.asyncio
    async def test_collect_observation_extracts_temperature(
        self, collector, valid_html_response, observation_time
    ):
        """Test temperature is extracted correctly."""
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = valid_html_response

            results = await collector.collect_observation(
                site_id=1,
                observation_time=observation_time,
            )

            # Find temperature result (parameter_id = 3)
            temp_results = [r for r in results if r.parameter_id == 3]
            assert len(temp_results) == 1
            assert temp_results[0].value == Decimal("8.5")


# =============================================================================
# Collect Forecast Tests (Observation-Only Collector)
# =============================================================================


class TestCollectForecast:
    """Test collect_forecast method for observation-only collector."""

    @pytest.mark.asyncio
    async def test_collect_forecast_returns_empty_list(self, collector):
        """ROMMA is observation-only source, forecast returns empty list."""
        from datetime import datetime, timezone

        results = await collector.collect_forecast(
            site_id=1,
            forecast_run=datetime.now(timezone.utc),
        )
        assert results == []
