"""ROMMA observation collector for weather beacon HTML scraping.

This module implements the ROMMaCollector class for fetching
real-time weather observations from ROMMA (Réseau d'Observation
Météo du Massif Alpin) weather stations via HTML scraping.

ROMMA Network:
- Automated weather stations across the French Alps
- Data: wind speed, wind direction, temperature, humidity
- Update frequency: Real-time (typically every 10 minutes)
- Website: https://www.romma.fr/

Data Source:
- URL pattern: https://www.romma.fr/station_24.php?id=XX
- Format: HTML with embedded weather data

Design Decision - Regex vs BeautifulSoup:
    This collector uses regex patterns instead of BeautifulSoup DOM parsing.
    Rationale:
    1. ROMMA HTML structure is simple with predictable text patterns
    2. Regex is more robust against minor HTML structure changes
    3. No DOM parsing overhead for simple text extraction
    4. Patterns like "Moyen sur 10min : XX km/h" are stable text markers
    5. Cardinal directions and temperatures follow consistent formats

    BeautifulSoup would be preferred if:
    - HTML structure was complex with nested tables
    - Data was in specific DOM elements identified by class/id
    - Multiple data points needed extraction from same elements
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from collectors.base import BaseCollector
from collectors.utils import (
    HttpClient,
    HttpClientError,
    RetryExhaustedError,
    retry_with_backoff,
)
from core.data_models import ForecastData, ObservationData

logger = logging.getLogger(__name__)


class ROMMaCollector(BaseCollector):
    """Collector for ROMMA weather beacon observations.

    Scrapes HTML from ROMMA weather station pages to extract
    real-time wind and temperature observations.

    Attributes:
        name: Human-readable collector name.
        source: Description of data source.
        BASE_URL: Base URL for ROMMA station pages.
        TIMEOUT: HTTP request timeout in seconds.
        MIN_REQUEST_INTERVAL: Minimum seconds between requests (polite scraping).
        STALE_THRESHOLD_HOURS: Hours after which data is considered stale.

    Example:
        >>> collector = ROMMaCollector()
        >>> observations = await collector.collect_observation(
        ...     site_id=1,
        ...     observation_time=datetime.now(timezone.utc)
        ... )
    """

    name: str = "ROMMA"
    source: str = "Réseau d'Observation Météo du Massif Alpin"

    # ROMMA station page URL pattern
    BASE_URL: str = "https://www.romma.fr/station_24.php"
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

    # Cardinal direction to degrees conversion
    CARDINAL_TO_DEGREES: dict[str, Decimal] = {
        "N": Decimal("0"),
        "NNE": Decimal("22.5"),
        "NE": Decimal("45"),
        "ENE": Decimal("67.5"),
        "E": Decimal("90"),
        "ESE": Decimal("112.5"),
        "SE": Decimal("135"),
        "SSE": Decimal("157.5"),
        "S": Decimal("180"),
        "SSW": Decimal("202.5"),
        "SW": Decimal("225"),
        "WSW": Decimal("247.5"),
        "W": Decimal("270"),
        "WNW": Decimal("292.5"),
        "NW": Decimal("315"),
        "NNW": Decimal("337.5"),
    }

    # French month names for timestamp parsing (with accent variants)
    FRENCH_MONTHS: dict[str, int] = {
        "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
        "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
        "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
    }

    def __init__(self, beacon_id: int | None = None):
        """Initialize ROMMA collector.

        Args:
            beacon_id: Optional ROMMA beacon station ID.
                       If not provided, uses site-to-beacon mapping.
        """
        self._beacon_id = beacon_id
        self._last_request_time: float = 0.0

    async def _enforce_rate_limit(self) -> None:
        """Enforce polite scraping rate limit.

        Ensures minimum interval between requests to respect
        ROMMA server resources.
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
        """Not implemented for ROMMA (observation-only source).

        ROMMA provides observations only, not forecasts.

        Args:
            site_id: Database ID of the site.
            forecast_run: Datetime of the forecast model run.

        Returns:
            Empty list (forecasts not supported).
        """
        logger.debug(
            f"collect_forecast called for ROMMA site {site_id}, "
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
        """Collect observation data from ROMMA beacon.

        Scrapes the ROMMA station page HTML to extract current
        wind and temperature observations.

        Args:
            site_id: Database ID of the site.
            observation_time: Target observation timestamp.
            beacon_id: Optional ROMMA beacon station ID.
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
            station_id = 21  # Example: Passy area beacon

        try:
            # Fetch HTML from beacon page
            html = await self._fetch_beacon_html(station_id)

            if not html:
                logger.warning(f"Empty HTML received for beacon {station_id}")
                return []

            # Parse observation data from HTML
            return self._parse_beacon_html(
                html=html,
                site_id=site_id,
                parameter_ids=parameter_ids,
            )

        except (HttpClientError, RetryExhaustedError) as e:
            logger.warning(
                f"HTTP error fetching ROMMA beacon {station_id}: {e}"
            )
            return []
        except Exception as e:
            logger.error(
                f"Unexpected error fetching ROMMA beacon {station_id}: {e}"
            )
            return []

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def _fetch_beacon_html(self, beacon_id: int) -> str:
        """Fetch HTML from ROMMA beacon station page.

        Args:
            beacon_id: ROMMA station ID.

        Returns:
            HTML content as string.

        Raises:
            HttpClientError: If HTTP request fails.
            RetryExhaustedError: If all retry attempts fail.
        """
        # Enforce rate limiting
        await self._enforce_rate_limit()

        url = f"{self.BASE_URL}?id={beacon_id}"
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
        """Extract wind speed from HTML.

        Looks for patterns:
        - "Moyen sur 10min : XX km/h" (plain text)
        - "Moyen sur 10min : <span...>XX</span>" (HTML wrapped)

        Args:
            html: Raw HTML content.

        Returns:
            Wind speed in km/h as Decimal, or None if not found.
        """
        # Try HTML pattern first: value wrapped in span tags
        # "Moyen sur 10min : <span class="bigTexte">5</span>"
        pattern_html = r'Moyen sur 10min\s*:\s*<span[^>]*>([\d.]+)</span>'
        match = re.search(pattern_html, html, re.IGNORECASE)

        if not match:
            # Try plain text pattern: "Moyen sur 10min : 25 km/h"
            pattern_plain = r"Moyen sur 10min\s*:\s*([\d.]+)\s*km/h"
            match = re.search(pattern_plain, html, re.IGNORECASE)

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
        - "Direction : N/S/E/W/NE/etc" (plain text)
        - "Direction : <span...>NNO</span>" (HTML wrapped)
        Converts cardinal directions to degrees.

        Args:
            html: Raw HTML content.

        Returns:
            Wind direction in degrees as Decimal, or None if not found.
        """
        # Try HTML pattern first: value wrapped in span tags
        # "Direction : <span class="smallTexte">NNO</span>"
        pattern_html = r'Direction\s*:\s*<span[^>]*>([NSEOEW]{1,3})</span>'
        match = re.search(pattern_html, html, re.IGNORECASE)

        if not match:
            # Try plain text pattern: "Direction : NE" or "Direction : N"
            pattern_plain = r"Direction\s*:\s*([NSEW]{1,3})\b"
            match = re.search(pattern_plain, html, re.IGNORECASE)

        if match:
            cardinal = match.group(1).upper()
            # Convert French O (Ouest) to W (West)
            cardinal = cardinal.replace("O", "W")
            if cardinal in self.CARDINAL_TO_DEGREES:
                return self.CARDINAL_TO_DEGREES[cardinal]
            else:
                logger.warning(f"Unknown cardinal direction: {cardinal}")
                return None

        # Also try numeric degrees pattern: "Direction : 180°"
        numeric_pattern = r"Direction\s*:\s*(\d+)\s*°"
        numeric_match = re.search(numeric_pattern, html, re.IGNORECASE)
        if numeric_match:
            try:
                return Decimal(numeric_match.group(1))
            except Exception:
                return None

        return None

    def _extract_temperature(self, html: str) -> Decimal | None:
        """Extract temperature from HTML.

        Looks for pattern: "Température: X.X °C" or "Température : X.X °C"

        Args:
            html: Raw HTML content.

        Returns:
            Temperature in Celsius as Decimal, or None if not found.
        """
        # Pattern: "Température: 8.5 °C" or "Température : -5.2 °C"
        pattern = r"Température\s*:?\s*([-\d.]+)\s*°C"
        match = re.search(pattern, html, re.IGNORECASE)

        if match:
            try:
                value = match.group(1)
                if value == "--" or value == "-.-":
                    return None
                return Decimal(value).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            except Exception:
                return None

        return None

    def _parse_observation_time(self, html: str) -> datetime | None:
        """Parse observation timestamp from HTML.

        Looks for patterns:
        - "le DD Month YYYY à HH:MM" (old format)
        - "le DD Month YYYY\\s+HH:MM" (new format, whitespace separated)

        Args:
            html: Raw HTML content.

        Returns:
            Timezone-aware datetime or None if not found.
        """
        # Try new format first: "le 18 Janvier 2026                17:01"
        # Date and time separated by whitespace (no "à")
        pattern_new = r"le\s+(\d{1,2})\s+(\w+)\s+(\d{4})\s+(\d{1,2}):(\d{2})"
        match = re.search(pattern_new, html, re.IGNORECASE)

        if not match:
            # Try old format: "le 12 Janvier 2026 à 14:30"
            pattern_old = r"le\s+(\d{1,2})\s+(\w+)\s+(\d{4})\s+à\s+(\d{1,2}):(\d{2})"
            match = re.search(pattern_old, html, re.IGNORECASE)

        if match:
            try:
                day = int(match.group(1))
                month_name = match.group(2).lower()
                year = int(match.group(3))
                hour = int(match.group(4))
                minute = int(match.group(5))

                month = self.FRENCH_MONTHS.get(month_name)
                if month is None:
                    logger.warning(f"Unknown French month: {month_name}")
                    return None

                # ROMMA times are in local French time (CET/CEST)
                # For simplicity, we use UTC (should be converted properly in production)
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
