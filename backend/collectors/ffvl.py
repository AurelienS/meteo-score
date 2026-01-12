"""FFVL observation collector for weather beacon HTML scraping.

This module implements the FFVLCollector class for fetching
real-time weather observations from FFVL (Fédération Française
de Vol Libre) weather stations via HTML scraping.

FFVL Network:
- Weather beacons across French flying sites (paragliding/hang-gliding)
- Data: wind speed (avg/min/max), wind direction, temperature
- Update frequency: Real-time (typically every 5-6 minutes)
- Website: https://www.balisemeteo.com/

Data Source:
- URL pattern: https://www.balisemeteo.com/balise.php?idBalise=XX
- Format: HTML with embedded weather data

Design Decision - Regex vs BeautifulSoup:
    This collector uses regex patterns instead of BeautifulSoup DOM parsing.
    Rationale:
    1. FFVL HTML structure uses simple, predictable text patterns
    2. Regex is more robust against minor HTML structure changes
    3. No DOM parsing overhead for simple text extraction
    4. Patterns like "Vitesse : **XX km/h**" are stable text markers
    5. Consistent with ROMMaCollector design for maintainability
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from collectors.base import BaseCollector
from collectors.utils import (
    HttpClient,
    HttpClientError,
    RetryExhaustedError,
    retry_with_backoff,
)
from core.data_models import ForecastData, ObservationData

logger = logging.getLogger(__name__)


class FFVLCollector(BaseCollector):
    """Collector for FFVL weather beacon observations.

    Scrapes HTML from FFVL (balisemeteo.com) weather station pages
    to extract real-time wind and temperature observations.

    Attributes:
        name: Human-readable collector name.
        source: Description of data source.
        BASE_URL: Base URL for FFVL beacon pages.
        TIMEOUT: HTTP request timeout in seconds.
        MIN_REQUEST_INTERVAL: Minimum seconds between requests (polite scraping).
        STALE_THRESHOLD_HOURS: Hours after which data is considered stale.

    Example:
        >>> collector = FFVLCollector()
        >>> observations = await collector.collect_observation(
        ...     site_id=1,
        ...     observation_time=datetime.now(timezone.utc),
        ...     beacon_id=67
        ... )
    """

    name: str = "FFVL"
    source: str = "Fédération Française de Vol Libre - Balises Météo"

    # FFVL beacon page URL pattern
    BASE_URL: str = "https://www.balisemeteo.com/balise.php"
    TIMEOUT: float = 10.0  # 10 seconds per AC6

    # Polite scraping: minimum 2 seconds between requests
    MIN_REQUEST_INTERVAL: float = 2.0

    # Data older than 2 hours is considered stale
    STALE_THRESHOLD_HOURS: float = 2.0

    # Default parameter IDs (matching database schema)
    DEFAULT_PARAMETER_IDS: dict[str, int] = {
        "wind_speed": 1,
        "wind_direction": 2,
        "temperature": 3,
    }

    # Validation ranges for aberrant value detection
    VALIDATION_RANGES: dict[str, tuple[Decimal, Decimal]] = {
        "wind_speed": (Decimal("0"), Decimal("200")),
        "wind_direction": (Decimal("0"), Decimal("360")),
        "temperature": (Decimal("-50"), Decimal("50")),
    }

    # French cardinal direction to degrees conversion
    # Note: French uses "O" for West (Ouest) instead of "W"
    FRENCH_CARDINAL_TO_DEGREES: dict[str, Decimal] = {
        "N": Decimal("0"),
        "NNE": Decimal("22.5"),
        "NE": Decimal("45"),
        "ENE": Decimal("67.5"),
        "E": Decimal("90"),
        "ESE": Decimal("112.5"),
        "SE": Decimal("135"),
        "SSE": Decimal("157.5"),
        "S": Decimal("180"),
        "SSO": Decimal("202.5"),
        "SO": Decimal("225"),
        "OSO": Decimal("247.5"),
        "O": Decimal("270"),
        "ONO": Decimal("292.5"),
        "NO": Decimal("315"),
        "NNO": Decimal("337.5"),
    }

    def __init__(self, beacon_id: int | None = None):
        """Initialize FFVL collector.

        Args:
            beacon_id: Optional FFVL beacon station ID.
                       If not provided, uses site-to-beacon mapping.
        """
        self._beacon_id = beacon_id
        self._last_request_time: float = 0.0

    async def _enforce_rate_limit(self) -> None:
        """Enforce polite scraping rate limit.

        Ensures minimum interval between requests to respect
        FFVL server resources.
        """
        current_time = time.monotonic()
        elapsed = current_time - self._last_request_time

        if elapsed < self.MIN_REQUEST_INTERVAL:
            wait_time = self.MIN_REQUEST_INTERVAL - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s before next request")
            await asyncio.sleep(wait_time)

        self._last_request_time = time.monotonic()

    async def collect_forecast(
        self,
        site_id: int,
        forecast_run: datetime,
    ) -> list[ForecastData]:
        """Not implemented for FFVL (observation-only source).

        FFVL provides observations only, not forecasts.

        Args:
            site_id: Database ID of the site.
            forecast_run: Datetime of the forecast model run.

        Returns:
            Empty list (forecasts not supported).
        """
        logger.debug(
            f"collect_forecast called for FFVL site {site_id}, "
            "but this is an observation-only source."
        )
        return []

    async def collect_observation(
        self,
        site_id: int,
        observation_time: datetime,
        beacon_id: int | None = None,
        parameter_ids: dict[str, int] | None = None,
    ) -> list[ObservationData]:
        """Collect observation data from FFVL beacon.

        Scrapes the FFVL station page HTML to extract current
        wind and temperature observations.

        Args:
            site_id: Database ID of the site.
            observation_time: Target observation timestamp.
            beacon_id: Optional FFVL beacon station ID.
            parameter_ids: Mapping of parameter names to IDs.

        Returns:
            List of ObservationData objects, empty list on error.
        """
        if parameter_ids is None:
            parameter_ids = self.DEFAULT_PARAMETER_IDS

        # Use provided beacon_id or instance default
        station_id = beacon_id or self._beacon_id
        if station_id is None:
            # Default to a known beacon for testing
            # In production, this would be looked up from site coordinates
            station_id = 67  # Example: Le Semnoz beacon

        try:
            # Fetch HTML from beacon page
            html = await self._fetch_beacon_html(station_id)

            if not html:
                logger.warning(f"Empty HTML received for beacon {station_id}")
                return []

            # Check for error messages in HTML
            if "ERROR" in html or "no data for idBalise" in html:
                logger.warning(f"Error response from FFVL beacon {station_id}")
                return []

            # Parse observation data from HTML
            return self._parse_beacon_html(
                html=html,
                site_id=site_id,
                parameter_ids=parameter_ids,
            )

        except (HttpClientError, RetryExhaustedError) as e:
            logger.warning(
                f"HTTP error fetching FFVL beacon {station_id}: {e}"
            )
            return []
        except TimeoutError as e:
            logger.warning(
                f"Timeout fetching FFVL beacon {station_id}: {e}"
            )
            return []
        except Exception as e:
            logger.error(
                f"Unexpected error fetching FFVL beacon {station_id}: {e}"
            )
            return []

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def _fetch_beacon_html(self, beacon_id: int) -> str:
        """Fetch HTML from FFVL beacon station page.

        Args:
            beacon_id: FFVL station ID.

        Returns:
            HTML content as string.

        Raises:
            HttpClientError: If HTTP request fails.
            RetryExhaustedError: If all retry attempts fail.
        """
        # Enforce rate limiting
        await self._enforce_rate_limit()

        url = f"{self.BASE_URL}?idBalise={beacon_id}"
        headers = self._get_headers()

        async with HttpClient(timeout=self.TIMEOUT, headers=headers) as client:
            return await client.get_text(url)

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for requests.

        Returns:
            Headers dict with User-Agent identifying MeteoScore.
        """
        return {
            "User-Agent": "MeteoScore/1.0 (Weather accuracy analysis; contact@meteoscore.fr)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        }

    def _parse_beacon_html(
        self,
        html: str,
        site_id: int,
        parameter_ids: dict[str, int],
    ) -> list[ObservationData]:
        """Parse weather data from beacon HTML.

        Args:
            html: Raw HTML content.
            site_id: Database ID of the site.
            parameter_ids: Mapping of parameter names to IDs.

        Returns:
            List of ObservationData objects.
        """
        observations: list[ObservationData] = []

        try:
            # Parse observation timestamp
            obs_time = self._parse_observation_time(html)
            if obs_time is None:
                logger.warning("Could not parse observation timestamp from HTML")
                return []

            # Check for stale data
            if self._is_stale(obs_time):
                logger.warning(
                    f"Observation data is stale (timestamp: {obs_time})"
                )
                # Still return data but log warning

            # Extract wind speed
            wind_speed = self._extract_wind_speed(html)
            if wind_speed is not None:
                if self._is_valid_value("wind_speed", wind_speed):
                    observations.append(ObservationData(
                        site_id=site_id,
                        parameter_id=parameter_ids.get("wind_speed", 1),
                        observation_time=obs_time,
                        value=wind_speed,
                    ))
                else:
                    logger.warning(f"Aberrant wind speed value: {wind_speed} km/h")

            # Extract wind direction
            wind_direction = self._extract_wind_direction(html)
            if wind_direction is not None:
                if self._is_valid_value("wind_direction", wind_direction):
                    observations.append(ObservationData(
                        site_id=site_id,
                        parameter_id=parameter_ids.get("wind_direction", 2),
                        observation_time=obs_time,
                        value=wind_direction,
                    ))
                else:
                    logger.warning(f"Aberrant wind direction value: {wind_direction}°")

            # Extract temperature
            temperature = self._extract_temperature(html)
            if temperature is not None:
                if self._is_valid_value("temperature", temperature):
                    observations.append(ObservationData(
                        site_id=site_id,
                        parameter_id=parameter_ids.get("temperature", 3),
                        observation_time=obs_time,
                        value=temperature,
                    ))
                else:
                    logger.warning(f"Aberrant temperature value: {temperature}°C")

        except Exception as e:
            logger.error(f"Error parsing beacon HTML: {e}")
            return []

        return observations

    def _extract_wind_speed(self, html: str) -> Decimal | None:
        """Extract average wind speed from HTML.

        Looks for pattern: "Vitesse : **XX km/h**" or "Vitesse : <b>XX km/h</b>"

        Note: FFVL pages show multiple wind speeds (avg, min, max) but we only
        extract the FIRST match (average). This is intentional - for deviation
        analysis, we compare average forecast vs average observation. Max wind
        extraction could be added later if needed for gust analysis.

        Args:
            html: Raw HTML content.

        Returns:
            Average wind speed in km/h as Decimal, or None if not found.
        """
        # Check for WARNING state first
        if "!!! WARNING !!!" in html:
            # Check if the warning is for wind speed
            warning_pattern = r"Vitesse\s*:\s*(?:<b>)?\*?\*?\s*!!!\s*WARNING\s*!!!"
            if re.search(warning_pattern, html, re.IGNORECASE):
                return None

        # Pattern: "Vitesse : <b>33 km/h</b>" or "Vitesse : **33 km/h**"
        pattern = r"Vitesse\s*:\s*(?:<b>|\*\*)\s*([\d.]+)\s*km/h"
        match = re.search(pattern, html, re.IGNORECASE)

        if match:
            try:
                value = match.group(1)
                return Decimal(value).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            except Exception:
                return None

        return None

    def _extract_wind_direction(self, html: str) -> Decimal | None:
        """Extract wind direction from HTML and convert to degrees.

        Looks for patterns:
        1. "Direction : <b>SO : 224°</b>" - cardinal with degrees (preferred)
        2. "Direction : <b>SO</b>" - cardinal only (fallback using FRENCH_CARDINAL_TO_DEGREES)

        Args:
            html: Raw HTML content.

        Returns:
            Wind direction in degrees as Decimal, or None if not found.
        """
        # Check for WARNING state first
        if "!!! WARNING !!!" in html:
            warning_pattern = r"Direction\s*:\s*(?:<b>)?\*?\*?\s*!!!\s*WARNING\s*!!!"
            if re.search(warning_pattern, html, re.IGNORECASE):
                return None

        # Pattern 1: "Direction : <b>SO : 224°</b>" - extract the degrees part
        pattern_with_degrees = r"Direction\s*:\s*(?:<b>|\*\*)?\s*([A-Z]{1,3})\s*:\s*(\d+)°"
        match = re.search(pattern_with_degrees, html, re.IGNORECASE)

        if match:
            try:
                # Use the numeric degrees from the pattern
                degrees = match.group(2)
                return Decimal(degrees)
            except Exception:
                pass

        # Pattern 2 (fallback): "Direction : <b>SO</b>" - cardinal only
        pattern_cardinal_only = r"Direction\s*:\s*(?:<b>|\*\*)?\s*([A-Z]{1,3})\s*(?:</b>|\*\*)"
        match_cardinal = re.search(pattern_cardinal_only, html, re.IGNORECASE)

        if match_cardinal:
            cardinal = match_cardinal.group(1).upper()
            if cardinal in self.FRENCH_CARDINAL_TO_DEGREES:
                return self.FRENCH_CARDINAL_TO_DEGREES[cardinal]
            else:
                logger.warning(f"Unknown French cardinal direction: {cardinal}")

        return None

    def _extract_temperature(self, html: str) -> Decimal | None:
        """Extract temperature from HTML.

        Looks for pattern: "Température : X°" or "Température : -X°"

        Args:
            html: Raw HTML content.

        Returns:
            Temperature in Celsius as Decimal, or None if not found.
        """
        # Check for NC (no data) state
        nc_pattern = r"Température\s*:\s*NC"
        if re.search(nc_pattern, html, re.IGNORECASE):
            return None

        # Pattern: "Température : 3°" or "Température : -8°" or "Température : 8.5°"
        pattern = r"Température\s*:\s*([-\d.]+)°"
        match = re.search(pattern, html, re.IGNORECASE)

        if match:
            try:
                value = match.group(1)
                if value in ("--", "-.-", "NC"):
                    return None
                return Decimal(value).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            except Exception:
                return None

        return None

    def _parse_observation_time(self, html: str) -> datetime | None:
        """Parse observation timestamp from HTML.

        Looks for pattern: "Relevé du DD/MM/YYYY - HH:MM"

        Args:
            html: Raw HTML content.

        Returns:
            Timezone-aware datetime or None if not found.
        """
        # Pattern: "Relevé du 12/01/2026 - 14:30"
        pattern = r"Relevé du\s+(\d{1,2})/(\d{1,2})/(\d{4})\s*-\s*(\d{1,2}):(\d{2})"
        match = re.search(pattern, html, re.IGNORECASE)

        if match:
            try:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                hour = int(match.group(4))
                minute = int(match.group(5))

                # TODO: FFVL times are in local French time (CET/CEST = UTC+1/+2)
                # Currently treating as UTC which causes 1-2h offset in stale detection.
                # For production, use pytz or zoneinfo to convert: Europe/Paris -> UTC
                # Impact: May incorrectly flag fresh data as stale during winter (UTC+1)
                return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
            except Exception as e:
                logger.warning(f"Error parsing timestamp: {e}")
                return None

        return None

    def _is_stale(self, observation_time: datetime) -> bool:
        """Check if observation data is stale.

        Args:
            observation_time: Observation timestamp.

        Returns:
            True if data is older than STALE_THRESHOLD_HOURS.
        """
        now = datetime.now(timezone.utc)
        age = now - observation_time
        return age > timedelta(hours=self.STALE_THRESHOLD_HOURS)

    def _is_valid_value(self, parameter: str, value: Decimal) -> bool:
        """Validate value is within acceptable range.

        Args:
            parameter: Parameter name (wind_speed, wind_direction, temperature).
            value: Value to validate.

        Returns:
            True if value is within valid range.
        """
        if parameter not in self.VALIDATION_RANGES:
            return True

        min_val, max_val = self.VALIDATION_RANGES[parameter]
        return min_val <= value <= max_val
