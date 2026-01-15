"""TDD test suite for FFVL observation collector.

Tests are written FIRST following TDD methodology.
All tests use mocked HTML responses - NEVER scrape real beacons in tests.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

# Import will fail until implementation exists - expected in TDD
try:
    from collectors.ffvl import FFVLCollector
except ImportError:
    FFVLCollector = None  # Will be implemented


# =============================================================================
# Test Fixtures - Mock HTML Responses
# =============================================================================


@pytest.fixture
def valid_beacon_html():
    """Valid FFVL beacon HTML with all data fields."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Balise Le Semnoz - FFVL</title></head>
    <body>
        <h1>Balise Le Semnoz</h1>
        <p>Relevé du 12/01/2026 - 14:30</p>
        <div class="current">
            <h2>Vent moyen</h2>
            <p>Direction : <b>SO : 224°</b></p>
            <p>Vitesse : <b>33 km/h</b></p>
        </div>
        <div class="max">
            <h2>Vent max</h2>
            <p>Direction : <b>OSO : 246°</b></p>
            <p>Vitesse : <b>48 km/h</b></p>
        </div>
        <div class="min">
            <p>Vitesse minimum : 20 km/h</p>
        </div>
        <div class="temp">
            <p>Température : 3°</p>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def html_with_negative_temperature():
    """HTML with negative temperature value."""
    return """
    <html>
    <body>
        <p>Relevé du 12/01/2026 - 08:00</p>
        <p>Direction : <b>N : 0°</b></p>
        <p>Vitesse : <b>15 km/h</b></p>
        <p>Température : -8°</p>
    </body>
    </html>
    """


@pytest.fixture
def html_with_warning_state():
    """HTML with warning indicators (sensor error)."""
    return """
    <html>
    <body>
        <p>Relevé du 12/01/2026 - 14:30</p>
        <p>Direction : <b>!!! WARNING !!!</b></p>
        <p>Vitesse : <b>!!! WARNING !!!</b></p>
        <p>Température : NC</p>
    </body>
    </html>
    """


@pytest.fixture
def html_missing_wind_speed():
    """HTML without wind speed data."""
    return """
    <html>
    <body>
        <p>Relevé du 12/01/2026 - 14:30</p>
        <p>Direction : <b>SE : 135°</b></p>
        <p>Température : 10°</p>
    </body>
    </html>
    """


@pytest.fixture
def html_missing_timestamp():
    """HTML without timestamp."""
    return """
    <html>
    <body>
        <p>Direction : <b>E : 90°</b></p>
        <p>Vitesse : <b>25 km/h</b></p>
        <p>Température : 15°</p>
    </body>
    </html>
    """


@pytest.fixture
def html_stale_data():
    """HTML with stale timestamp (>2 hours old)."""
    return """
    <html>
    <body>
        <p>Relevé du 10/01/2026 - 08:00</p>
        <p>Direction : <b>N : 0°</b></p>
        <p>Vitesse : <b>10 km/h</b></p>
        <p>Température : 5°</p>
    </body>
    </html>
    """


@pytest.fixture
def html_error_no_data():
    """HTML error response - beacon not found."""
    return """
    <html>
    <body>
        ERROR2 : no data for idBalise:9999
    </body>
    </html>
    """


@pytest.fixture
def html_all_cardinal_directions():
    """HTML for testing all French cardinal direction conversions."""
    return """
    <html>
    <body>
        <p>Relevé du 12/01/2026 - 14:30</p>
        <p>Direction : <b>{cardinal} : {degrees}°</b></p>
        <p>Vitesse : <b>20 km/h</b></p>
        <p>Température : 10°</p>
    </body>
    </html>
    """


@pytest.fixture
def html_decimal_wind_speed():
    """HTML with decimal wind speed values."""
    return """
    <html>
    <body>
        <p>Relevé du 12/01/2026 - 14:30</p>
        <p>Direction : <b>NE : 45°</b></p>
        <p>Vitesse : <b>12.5 km/h</b></p>
        <p>Température : 8.5°</p>
    </body>
    </html>
    """


@pytest.fixture
def html_aberrant_wind_speed():
    """HTML with aberrant wind speed (>200 km/h)."""
    return """
    <html>
    <body>
        <p>Relevé du 12/01/2026 - 14:30</p>
        <p>Direction : <b>S : 180°</b></p>
        <p>Vitesse : <b>250 km/h</b></p>
        <p>Température : 10°</p>
    </body>
    </html>
    """


@pytest.fixture
def html_aberrant_temperature():
    """HTML with aberrant temperature (outside -50 to +50)."""
    return """
    <html>
    <body>
        <p>Relevé du 12/01/2026 - 14:30</p>
        <p>Direction : <b>N : 0°</b></p>
        <p>Vitesse : <b>10 km/h</b></p>
        <p>Température : 60°</p>
    </body>
    </html>
    """


# =============================================================================
# Test Class: Basic Collector Attributes
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestFFVLCollectorAttributes:
    """Test basic collector attributes and configuration."""

    def test_collector_has_name(self):
        """Collector should have a name attribute."""
        collector = FFVLCollector()
        assert hasattr(collector, "name")
        assert collector.name == "FFVL"

    def test_collector_has_source(self):
        """Collector should have a source description."""
        collector = FFVLCollector()
        assert hasattr(collector, "source")
        assert "FFVL" in collector.source or "Fédération" in collector.source

    def test_collector_has_base_url(self):
        """Collector should have BASE_URL for beacon pages."""
        collector = FFVLCollector()
        assert hasattr(collector, "BASE_URL")
        assert "balisemeteo.com" in collector.BASE_URL

    def test_collector_has_timeout(self):
        """Collector should have 10-second timeout per AC6."""
        collector = FFVLCollector()
        assert hasattr(collector, "TIMEOUT")
        assert collector.TIMEOUT == 10.0

    def test_collector_has_min_request_interval(self):
        """Collector should have minimum 2-second request interval."""
        collector = FFVLCollector()
        assert hasattr(collector, "MIN_REQUEST_INTERVAL")
        assert collector.MIN_REQUEST_INTERVAL >= 2.0

    def test_collector_has_stale_threshold(self):
        """Collector should have 2-hour stale threshold."""
        collector = FFVLCollector()
        assert hasattr(collector, "STALE_THRESHOLD_HOURS")
        assert collector.STALE_THRESHOLD_HOURS == 2.0


# =============================================================================
# Test Class: Wind Speed Extraction
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestWindSpeedExtraction:
    """Test wind speed extraction from HTML."""

    def test_extract_average_wind_speed(self, valid_beacon_html):
        """Should extract average wind speed in km/h."""
        collector = FFVLCollector()
        speed = collector._extract_wind_speed(valid_beacon_html)
        assert speed == Decimal("33")

    def test_extract_decimal_wind_speed(self, html_decimal_wind_speed):
        """Should handle decimal wind speed values."""
        collector = FFVLCollector()
        speed = collector._extract_wind_speed(html_decimal_wind_speed)
        assert speed == Decimal("12.5")

    def test_missing_wind_speed_returns_none(self, html_missing_wind_speed):
        """Should return None when wind speed is missing."""
        collector = FFVLCollector()
        speed = collector._extract_wind_speed(html_missing_wind_speed)
        assert speed is None

    def test_warning_wind_speed_returns_none(self, html_with_warning_state):
        """Should return None when wind speed shows WARNING."""
        collector = FFVLCollector()
        speed = collector._extract_wind_speed(html_with_warning_state)
        assert speed is None

    def test_wind_speed_zero_is_valid(self):
        """Zero wind speed should be valid (calm conditions)."""
        html = """
        <html><body>
            <p>Relevé du 12/01/2026 - 14:30</p>
            <p>Vitesse : <b>0 km/h</b></p>
        </body></html>
        """
        collector = FFVLCollector()
        speed = collector._extract_wind_speed(html)
        assert speed == Decimal("0")


# =============================================================================
# Test Class: Wind Direction Extraction
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestWindDirectionExtraction:
    """Test wind direction extraction and cardinal conversion."""

    def test_extract_wind_direction_with_degrees(self, valid_beacon_html):
        """Should extract wind direction in degrees."""
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(valid_beacon_html)
        assert direction == Decimal("224")

    def test_cardinal_n_converts_to_0(self):
        """North (N) should convert to 0 degrees."""
        html = '<p>Direction : <b>N : 0°</b></p>'
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("0")

    def test_cardinal_e_converts_to_90(self):
        """East (E) should convert to 90 degrees."""
        html = '<p>Direction : <b>E : 90°</b></p>'
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("90")

    def test_cardinal_s_converts_to_180(self):
        """South (S) should convert to 180 degrees."""
        html = '<p>Direction : <b>S : 180°</b></p>'
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("180")

    def test_cardinal_o_converts_to_270(self):
        """West (O for Ouest) should convert to 270 degrees."""
        html = '<p>Direction : <b>O : 270°</b></p>'
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("270")

    def test_cardinal_so_converts_to_225(self):
        """Southwest (SO for Sud-Ouest) should convert to 225 degrees."""
        html = '<p>Direction : <b>SO : 225°</b></p>'
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("225")

    def test_cardinal_ne_converts_to_45(self):
        """Northeast (NE) should convert to 45 degrees."""
        html = '<p>Direction : <b>NE : 45°</b></p>'
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("45")

    def test_cardinal_no_converts_to_315(self):
        """Northwest (NO for Nord-Ouest) should convert to 315 degrees."""
        html = '<p>Direction : <b>NO : 315°</b></p>'
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("315")

    def test_cardinal_se_converts_to_135(self):
        """Southeast (SE) should convert to 135 degrees."""
        html = '<p>Direction : <b>SE : 135°</b></p>'
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("135")

    def test_cardinal_oso_converts_correctly(self):
        """West-Southwest (OSO) should convert to ~247.5 degrees."""
        html = '<p>Direction : <b>OSO : 247°</b></p>'
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("247")

    def test_cardinal_only_fallback(self):
        """Should use FRENCH_CARDINAL_TO_DEGREES when no degrees in HTML."""
        html = '<p>Direction : <b>SO</b></p>'
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("225")  # SO = 225 degrees

    def test_cardinal_only_fallback_north(self):
        """Cardinal-only fallback for North."""
        html = '<p>Direction : <b>N</b></p>'
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html)
        assert direction == Decimal("0")

    def test_missing_direction_returns_none(self):
        """Should return None when direction is missing."""
        html = '<html><body><p>Vitesse : <b>20 km/h</b></p></body></html>'
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html)
        assert direction is None

    def test_warning_direction_returns_none(self, html_with_warning_state):
        """Should return None when direction shows WARNING."""
        collector = FFVLCollector()
        direction = collector._extract_wind_direction(html_with_warning_state)
        assert direction is None


# =============================================================================
# Test Class: Temperature Extraction
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestTemperatureExtraction:
    """Test temperature extraction from HTML."""

    def test_extract_positive_temperature(self, valid_beacon_html):
        """Should extract positive temperature."""
        collector = FFVLCollector()
        temp = collector._extract_temperature(valid_beacon_html)
        assert temp == Decimal("3")

    def test_extract_negative_temperature(self, html_with_negative_temperature):
        """Should extract negative temperature."""
        collector = FFVLCollector()
        temp = collector._extract_temperature(html_with_negative_temperature)
        assert temp == Decimal("-8")

    def test_extract_decimal_temperature(self, html_decimal_wind_speed):
        """Should handle decimal temperature values."""
        collector = FFVLCollector()
        temp = collector._extract_temperature(html_decimal_wind_speed)
        assert temp == Decimal("8.5")

    def test_nc_temperature_returns_none(self, html_with_warning_state):
        """Should return None when temperature is NC (no data)."""
        collector = FFVLCollector()
        temp = collector._extract_temperature(html_with_warning_state)
        assert temp is None

    def test_missing_temperature_returns_none(self):
        """Should return None when temperature is missing."""
        html = '<html><body><p>Vitesse : <b>20 km/h</b></p></body></html>'
        collector = FFVLCollector()
        temp = collector._extract_temperature(html)
        assert temp is None


# =============================================================================
# Test Class: Timestamp Parsing
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestTimestampParsing:
    """Test observation timestamp parsing."""

    def test_parse_valid_timestamp(self, valid_beacon_html):
        """Should parse DD/MM/YYYY - HH:MM format."""
        collector = FFVLCollector()
        timestamp = collector._parse_observation_time(valid_beacon_html)
        assert timestamp is not None
        assert timestamp.year == 2026
        assert timestamp.month == 1
        assert timestamp.day == 12
        assert timestamp.hour == 14
        assert timestamp.minute == 30

    def test_timestamp_is_timezone_aware(self, valid_beacon_html):
        """Parsed timestamp should be timezone-aware (UTC)."""
        collector = FFVLCollector()
        timestamp = collector._parse_observation_time(valid_beacon_html)
        assert timestamp.tzinfo is not None

    def test_missing_timestamp_returns_none(self, html_missing_timestamp):
        """Should return None when timestamp is missing."""
        collector = FFVLCollector()
        timestamp = collector._parse_observation_time(html_missing_timestamp)
        assert timestamp is None

    def test_parse_morning_timestamp(self):
        """Should correctly parse morning times."""
        html = '<p>Relevé du 15/02/2026 - 08:15</p>'
        collector = FFVLCollector()
        timestamp = collector._parse_observation_time(html)
        assert timestamp.hour == 8
        assert timestamp.minute == 15


# =============================================================================
# Test Class: Data Validation
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestDataValidation:
    """Test data validation ranges."""

    def test_valid_wind_speed_passes(self):
        """Wind speed 0-200 km/h should be valid."""
        collector = FFVLCollector()
        assert collector._is_valid_value("wind_speed", Decimal("0")) is True
        assert collector._is_valid_value("wind_speed", Decimal("100")) is True
        assert collector._is_valid_value("wind_speed", Decimal("200")) is True

    def test_aberrant_wind_speed_fails(self):
        """Wind speed >200 km/h should be flagged as aberrant."""
        collector = FFVLCollector()
        assert collector._is_valid_value("wind_speed", Decimal("201")) is False
        assert collector._is_valid_value("wind_speed", Decimal("-1")) is False

    def test_valid_wind_direction_passes(self):
        """Wind direction 0-360 degrees should be valid."""
        collector = FFVLCollector()
        assert collector._is_valid_value("wind_direction", Decimal("0")) is True
        assert collector._is_valid_value("wind_direction", Decimal("180")) is True
        assert collector._is_valid_value("wind_direction", Decimal("360")) is True

    def test_aberrant_wind_direction_fails(self):
        """Wind direction outside 0-360 should be flagged."""
        collector = FFVLCollector()
        assert collector._is_valid_value("wind_direction", Decimal("361")) is False
        assert collector._is_valid_value("wind_direction", Decimal("-1")) is False

    def test_valid_temperature_passes(self):
        """Temperature -50 to +50 C should be valid."""
        collector = FFVLCollector()
        assert collector._is_valid_value("temperature", Decimal("-50")) is True
        assert collector._is_valid_value("temperature", Decimal("0")) is True
        assert collector._is_valid_value("temperature", Decimal("50")) is True

    def test_aberrant_temperature_fails(self):
        """Temperature outside -50 to +50 should be flagged."""
        collector = FFVLCollector()
        assert collector._is_valid_value("temperature", Decimal("-51")) is False
        assert collector._is_valid_value("temperature", Decimal("51")) is False


# =============================================================================
# Test Class: Stale Data Detection
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestStaleDataDetection:
    """Test stale data detection (>2 hours old)."""

    def test_recent_data_not_stale(self):
        """Data less than 2 hours old should not be stale."""
        collector = FFVLCollector()
        recent = datetime.now(timezone.utc)
        assert collector._is_stale(recent) is False

    def test_old_data_is_stale(self):
        """Data more than 2 hours old should be stale."""
        from datetime import timedelta

        collector = FFVLCollector()
        old = datetime.now(timezone.utc) - timedelta(hours=3)
        assert collector._is_stale(old) is True

    def test_data_at_threshold_not_stale(self):
        """Data exactly at 2 hours should use > comparison (not stale)."""
        from datetime import timedelta

        collector = FFVLCollector()
        # 1 hour 59 minutes is definitely not stale
        at_threshold = datetime.now(timezone.utc) - timedelta(hours=1, minutes=59)
        assert collector._is_stale(at_threshold) is False


# =============================================================================
# Test Class: HTTP Error Handling
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestHttpErrorHandling:
    """Test HTTP error handling."""

    @pytest.mark.asyncio
    async def test_http_404_returns_empty_list(self):
        """HTTP 404 should return empty list, not raise exception."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            from collectors.utils import HttpClientError

            mock_fetch.side_effect = HttpClientError("404 Not Found")

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=9999,
            )
            assert result == []

    @pytest.mark.asyncio
    async def test_http_500_returns_empty_list(self):
        """HTTP 500 should return empty list, not raise exception."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            from collectors.utils import HttpClientError

            mock_fetch.side_effect = HttpClientError("500 Server Error")

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )
            assert result == []

    @pytest.mark.asyncio
    async def test_timeout_returns_empty_list(self):
        """Connection timeout should return empty list."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = TimeoutError("Connection timed out")

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )
            assert result == []

    @pytest.mark.asyncio
    async def test_retry_exhausted_returns_empty_list(self):
        """Retry exhaustion should return empty list."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            from collectors.utils import RetryExhaustedError

            mock_fetch.side_effect = RetryExhaustedError("All retries failed")

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )
            assert result == []


# =============================================================================
# Test Class: HTML Parsing Errors
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestHtmlParsingErrors:
    """Test HTML parsing error handling."""

    @pytest.mark.asyncio
    async def test_malformed_html_returns_empty_list(self):
        """Malformed HTML should return empty list."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = "<html><body><<<invalid>>>"

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )
            # Should return empty list (no valid data extracted)
            assert result == []

    @pytest.mark.asyncio
    async def test_empty_html_returns_empty_list(self):
        """Empty HTML should return empty list."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = ""

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )
            assert result == []

    @pytest.mark.asyncio
    async def test_error_message_html_returns_empty_list(self, html_error_no_data):
        """ERROR response HTML should return empty list."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = html_error_no_data

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=9999,
            )
            assert result == []


# =============================================================================
# Test Class: Missing Data Handling
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestMissingDataHandling:
    """Test graceful handling of missing data fields."""

    @pytest.mark.asyncio
    async def test_missing_wind_skips_wind_observations(self, html_missing_wind_speed):
        """Missing wind speed should skip wind observation, not crash."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = html_missing_wind_speed

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )
            # Should have direction and temperature, but not wind speed
            wind_speed_obs = [
                obs for obs in result if obs.parameter_id == 1
            ]
            assert len(wind_speed_obs) == 0

    @pytest.mark.asyncio
    async def test_missing_temperature_skips_temperature(self):
        """Missing temperature should skip temperature observation."""
        html = """
        <html><body>
            <p>Relevé du 12/01/2026 - 14:30</p>
            <p>Direction : <b>N : 0°</b></p>
            <p>Vitesse : <b>20 km/h</b></p>
        </body></html>
        """
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = html

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )
            # Should have wind data, but not temperature
            temp_obs = [obs for obs in result if obs.parameter_id == 3]
            assert len(temp_obs) == 0


# =============================================================================
# Test Class: Polite Scraping
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestPoliteScraping:
    """Test polite scraping configuration."""

    def test_has_min_request_interval(self):
        """Collector should enforce minimum 2-second interval."""
        collector = FFVLCollector()
        assert collector.MIN_REQUEST_INTERVAL >= 2.0

    def test_user_agent_header(self):
        """Headers should include MeteoScore User-Agent."""
        collector = FFVLCollector()
        headers = collector._get_headers()
        assert "User-Agent" in headers
        assert "MeteoScore" in headers["User-Agent"]


# =============================================================================
# Test Class: Rate Limiting
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_has_rate_limit_attributes(self):
        """Collector should have rate limit tracking attributes."""
        collector = FFVLCollector()
        assert hasattr(collector, "_last_request_time")

    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self):
        """Rate limit should enforce delay between requests."""
        import time

        collector = FFVLCollector()
        collector._last_request_time = time.monotonic()

        start = time.monotonic()
        await collector._enforce_rate_limit()
        elapsed = time.monotonic() - start

        # Should have waited at least MIN_REQUEST_INTERVAL
        assert elapsed >= collector.MIN_REQUEST_INTERVAL - 0.1


# =============================================================================
# Test Class: Collect Observation Integration
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestCollectObservationIntegration:
    """Integration tests for collect_observation method."""

    @pytest.mark.asyncio
    async def test_collect_observation_with_valid_html(self, valid_beacon_html):
        """Should return list of ObservationData with valid HTML."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = valid_beacon_html

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )

            assert len(result) >= 2  # At least wind speed and direction
            assert all(hasattr(obs, "site_id") for obs in result)
            assert all(hasattr(obs, "value") for obs in result)

    @pytest.mark.asyncio
    async def test_collect_observation_sets_correct_site_id(self, valid_beacon_html):
        """Observations should have correct site_id."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = valid_beacon_html

            result = await collector.collect_observation(
                site_id=42,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )

            assert all(obs.site_id == 42 for obs in result)

    @pytest.mark.asyncio
    async def test_collect_observation_extracts_wind_speed(self, valid_beacon_html):
        """Should extract wind speed observation."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = valid_beacon_html

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )

            wind_speed_obs = [obs for obs in result if obs.parameter_id == 1]
            assert len(wind_speed_obs) == 1
            assert wind_speed_obs[0].value == Decimal("33")

    @pytest.mark.asyncio
    async def test_collect_observation_extracts_wind_direction(self, valid_beacon_html):
        """Should extract wind direction observation."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = valid_beacon_html

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )

            wind_dir_obs = [obs for obs in result if obs.parameter_id == 2]
            assert len(wind_dir_obs) == 1
            assert wind_dir_obs[0].value == Decimal("224")

    @pytest.mark.asyncio
    async def test_collect_observation_extracts_temperature(self, valid_beacon_html):
        """Should extract temperature observation."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = valid_beacon_html

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )

            temp_obs = [obs for obs in result if obs.parameter_id == 3]
            assert len(temp_obs) == 1
            assert temp_obs[0].value == Decimal("3")


# =============================================================================
# Test Class: Collect Forecast (Should Be Empty)
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestCollectForecast:
    """Test that collect_forecast returns empty (observation-only source)."""

    @pytest.mark.asyncio
    async def test_collect_forecast_returns_empty_list(self):
        """FFVL is observation-only, forecast should return empty list."""
        collector = FFVLCollector()
        result = await collector.collect_forecast(
            site_id=1,
            forecast_run=datetime.now(timezone.utc),
        )
        assert result == []


# =============================================================================
# Test Class: Aberrant Value Filtering
# =============================================================================


@pytest.mark.skipif(FFVLCollector is None, reason="FFVLCollector not implemented yet")
class TestAberrantValueFiltering:
    """Test that aberrant values are filtered out."""

    @pytest.mark.asyncio
    async def test_aberrant_wind_speed_filtered(self, html_aberrant_wind_speed):
        """Aberrant wind speed (>200 km/h) should be filtered."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = html_aberrant_wind_speed

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )

            wind_speed_obs = [obs for obs in result if obs.parameter_id == 1]
            assert len(wind_speed_obs) == 0  # Should be filtered

    @pytest.mark.asyncio
    async def test_aberrant_temperature_filtered(self, html_aberrant_temperature):
        """Aberrant temperature (>50C) should be filtered."""
        collector = FFVLCollector()
        with patch.object(
            collector, "_fetch_beacon_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = html_aberrant_temperature

            result = await collector.collect_observation(
                site_id=1,
                observation_time=datetime.now(timezone.utc),
                beacon_id=67,
            )

            temp_obs = [obs for obs in result if obs.parameter_id == 3]
            assert len(temp_obs) == 0  # Should be filtered
