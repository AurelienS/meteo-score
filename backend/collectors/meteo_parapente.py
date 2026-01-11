"""Meteo-Parapente forecast collector.

This module implements the MeteoParapenteCollector class for fetching
weather forecast data from the Meteo-Parapente API.

API Documentation:
- Endpoint: https://data0.meteo-parapente.com/data.php
- Parameters:
  - run: Forecast run time (YYYYMMDDHH format)
  - location: Coordinates as lat,lon
  - date: Target date (YYYYMMDD format)
  - plot: "sounding" for temperature data
- Response: JSON with gridCoords, data (keyed by hour), status, time

Data fields per hour:
- tc: Temperature in °C (list, index 0 = surface)
- umet/vmet: Wind U/V components in m/s (list, index 0 = surface)
- z: Altitude levels in meters
- ter: Terrain altitude
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from backend.collectors.base import BaseCollector
from backend.collectors.utils import (
    HttpClient,
    HttpClientError,
    RetryExhaustedError,
    retry_with_backoff,
)
from backend.core.data_models import ForecastData

logger = logging.getLogger(__name__)


class MeteoParapenteCollector(BaseCollector):
    """Collector for Meteo-Parapente JSON API.

    Retrieves weather forecast data from Meteo-Parapente API
    and converts it to ForecastData objects for storage.

    Attributes:
        name: Collector identifier.
        source: Data source name.
        API_ENDPOINT: Base URL for the API.
        TIMEOUT: Request timeout in seconds.

    Example:
        >>> collector = MeteoParapenteCollector()
        >>> forecasts = await collector.collect_forecast(
        ...     site_id=1,
        ...     forecast_run=datetime(2026, 1, 11, 6, 0, tzinfo=timezone.utc),
        ...     latitude=45.9167,
        ...     longitude=6.7000,
        ... )
    """

    name: str = "MeteoParapenteCollector"
    source: str = "Meteo-Parapente"
    API_ENDPOINT: str = "https://data0.meteo-parapente.com/data.php"
    TIMEOUT: float = 10.0

    # Validation ranges for aberrant value detection
    VALIDATION_RANGES: dict[str, tuple[Decimal, Decimal]] = {
        "wind_speed": (Decimal("0"), Decimal("200")),
        "wind_direction": (Decimal("0"), Decimal("360")),
        "temperature": (Decimal("-50"), Decimal("50")),
    }

    # Default parameter IDs (can be overridden in collect_forecast)
    DEFAULT_PARAMETER_IDS: dict[str, int] = {
        "wind_speed": 1,
        "wind_direction": 2,
        "temperature": 3,
    }

    async def collect_forecast(
        self,
        site_id: int,
        forecast_run: datetime,
        latitude: float | None = None,
        longitude: float | None = None,
        model_id: int = 2,
        parameter_ids: dict[str, int] | None = None,
        target_date: datetime | None = None,
    ) -> list[ForecastData]:
        """Collect forecast data from Meteo-Parapente API.

        Args:
            site_id: Database ID of the site.
            forecast_run: Datetime of the forecast model run (UTC).
            latitude: Site latitude (required for API call).
            longitude: Site longitude (required for API call).
            model_id: Database ID for Meteo-Parapente model (default: 2).
            parameter_ids: Mapping of parameter names to IDs.
            target_date: Target date for forecast (default: day after forecast_run).

        Returns:
            List of ForecastData objects, empty list on error.

        Raises:
            No exceptions are raised - errors return empty list.
        """
        if latitude is None or longitude is None:
            logger.warning(
                f"Missing coordinates for site {site_id}. "
                "Cannot fetch from Meteo-Parapente API."
            )
            return []

        if parameter_ids is None:
            parameter_ids = self.DEFAULT_PARAMETER_IDS

        if target_date is None:
            # Default to the day after forecast_run for forecast data
            target_date = forecast_run + timedelta(days=1)

        try:
            response = await self._fetch_api(
                latitude=latitude,
                longitude=longitude,
                forecast_run=forecast_run,
                target_date=target_date,
            )
            return self._parse_response(
                response=response,
                site_id=site_id,
                model_id=model_id,
                parameter_ids=parameter_ids,
                forecast_run=forecast_run,
                target_date=target_date,
            )
        except (HttpClientError, RetryExhaustedError) as e:
            logger.warning(
                f"HTTP error fetching Meteo-Parapente data for site {site_id}: {e}"
            )
            return []
        except Exception as e:
            logger.error(
                f"Unexpected error fetching Meteo-Parapente data for site {site_id}: {e}"
            )
            return []

    async def collect_observation(
        self,
        site_id: int,
        observation_time: datetime,
    ) -> list:
        """Not implemented for Meteo-Parapente (forecast-only source).

        Meteo-Parapente provides forecasts only, not observations.

        Args:
            site_id: Database ID of the site.
            observation_time: Datetime of the observation.

        Returns:
            Empty list (observations not supported).
        """
        logger.debug(
            f"collect_observation called for Meteo-Parapente site {site_id}, "
            "but this is a forecast-only source."
        )
        return []

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def _fetch_api(
        self,
        latitude: float,
        longitude: float,
        forecast_run: datetime,
        target_date: datetime,
    ) -> dict[str, Any]:
        """Fetch data from Meteo-Parapente API with retry logic.

        Args:
            latitude: Site latitude.
            longitude: Site longitude.
            forecast_run: Forecast model run datetime.
            target_date: Target date for forecast data.

        Returns:
            Parsed JSON response as dictionary.

        Raises:
            HttpClientError: If HTTP request fails.
            RetryExhaustedError: If all retry attempts fail.
        """
        url = self._build_api_url(
            latitude=latitude,
            longitude=longitude,
            forecast_run=forecast_run,
            target_date=target_date,
        )
        headers = self._get_headers()

        async with HttpClient(timeout=self.TIMEOUT, headers=headers) as client:
            return await client.get(url)

    def _build_api_url(
        self,
        latitude: float,
        longitude: float,
        forecast_run: datetime,
        target_date: datetime,
    ) -> str:
        """Build API URL with query parameters.

        Args:
            latitude: Site latitude.
            longitude: Site longitude.
            forecast_run: Forecast model run datetime.
            target_date: Target date for forecast data.

        Returns:
            Complete API URL with query parameters.
        """
        # Format: run=YYYYMMDDHH
        run_str = forecast_run.strftime("%Y%m%d%H")
        # Format: date=YYYYMMDD
        date_str = target_date.strftime("%Y%m%d")
        # Format: location=lat,lon
        location_str = f"{latitude},{longitude}"

        return (
            f"{self.API_ENDPOINT}"
            f"?run={run_str}"
            f"&location={location_str}"
            f"&date={date_str}"
            f"&plot=sounding"
        )

    def _get_headers(self) -> dict[str, str]:
        """Get required HTTP headers for API request.

        Returns:
            Dictionary of HTTP headers.
        """
        return {
            "origin": "https://meteo-parapente.com",
            "referer": "https://meteo-parapente.com/",
            "user-agent": "MeteoScore/1.0 (Weather Forecast Accuracy Platform)",
            "accept": "application/json",
            "x-auth": "",
        }

    def _parse_response(
        self,
        response: Any,
        site_id: int,
        model_id: int,
        parameter_ids: dict[str, int],
        forecast_run: datetime,
        target_date: datetime,
    ) -> list[ForecastData]:
        """Parse API response into ForecastData objects.

        Args:
            response: API response (dict or other).
            site_id: Database ID of the site.
            model_id: Database ID of the model.
            parameter_ids: Mapping of parameter names to IDs.
            forecast_run: Forecast model run datetime.
            target_date: Target date for forecast data.

        Returns:
            List of ForecastData objects.
        """
        # Validate response is a dict
        if not isinstance(response, dict):
            logger.warning(f"Invalid response type: {type(response)}")
            return []

        # Check status
        status = response.get("status")
        if status != "ok":
            logger.warning(f"API returned non-ok status: {status}")
            return []

        # Get data section
        data = response.get("data")
        if not data or not isinstance(data, dict):
            logger.warning("No data in API response or invalid format")
            return []

        results: list[ForecastData] = []

        # Process each hour
        for hour_key, hour_data in data.items():
            try:
                hour_results = self._parse_hour_data(
                    hour_key=hour_key,
                    hour_data=hour_data,
                    site_id=site_id,
                    model_id=model_id,
                    parameter_ids=parameter_ids,
                    forecast_run=forecast_run,
                    target_date=target_date,
                )
                results.extend(hour_results)
            except Exception as e:
                logger.warning(f"Error parsing hour {hour_key}: {e}")
                continue

        return results

    def _parse_hour_data(
        self,
        hour_key: str,
        hour_data: dict[str, Any],
        site_id: int,
        model_id: int,
        parameter_ids: dict[str, int],
        forecast_run: datetime,
        target_date: datetime,
    ) -> list[ForecastData]:
        """Parse data for a single hour.

        Args:
            hour_key: Hour string (e.g., "12:00").
            hour_data: Data dictionary for this hour.
            site_id: Database ID of the site.
            model_id: Database ID of the model.
            parameter_ids: Mapping of parameter names to IDs.
            forecast_run: Forecast model run datetime.
            target_date: Target date for forecast data.

        Returns:
            List of ForecastData objects for this hour.
        """
        results: list[ForecastData] = []

        # Parse valid_time from hour_key
        valid_time = self._parse_valid_time(hour_key, target_date)
        if valid_time is None:
            return []

        # Calculate horizon (hours from forecast_run to valid_time)
        horizon = int((valid_time - forecast_run).total_seconds() / 3600)

        # Extract surface values (index 0)
        umet_list = hour_data.get("umet", [])
        vmet_list = hour_data.get("vmet", [])
        tc_list = hour_data.get("tc", [])

        # Wind data
        if umet_list and vmet_list:
            u = float(umet_list[0])
            v = float(vmet_list[0])

            # Wind speed
            wind_speed = self._calculate_wind_speed(u, v)
            if self._is_valid_value("wind_speed", wind_speed):
                results.append(
                    ForecastData(
                        site_id=site_id,
                        model_id=model_id,
                        parameter_id=parameter_ids.get("wind_speed", 1),
                        forecast_run=forecast_run,
                        valid_time=valid_time,
                        horizon=horizon,
                        value=wind_speed,
                    )
                )
            else:
                logger.warning(
                    f"Aberrant wind speed {wind_speed} km/h at {hour_key}, skipping"
                )

            # Wind direction
            wind_direction = self._calculate_wind_direction(u, v)
            if self._is_valid_value("wind_direction", wind_direction):
                results.append(
                    ForecastData(
                        site_id=site_id,
                        model_id=model_id,
                        parameter_id=parameter_ids.get("wind_direction", 2),
                        forecast_run=forecast_run,
                        valid_time=valid_time,
                        horizon=horizon,
                        value=wind_direction,
                    )
                )
            else:
                logger.warning(
                    f"Aberrant wind direction {wind_direction}° at {hour_key}, skipping"
                )

        # Temperature data
        if tc_list:
            temperature = Decimal(str(tc_list[0])).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
            if self._is_valid_value("temperature", temperature):
                results.append(
                    ForecastData(
                        site_id=site_id,
                        model_id=model_id,
                        parameter_id=parameter_ids.get("temperature", 3),
                        forecast_run=forecast_run,
                        valid_time=valid_time,
                        horizon=horizon,
                        value=temperature,
                    )
                )
            else:
                logger.warning(
                    f"Aberrant temperature {temperature}°C at {hour_key}, skipping"
                )

        return results

    def _parse_valid_time(
        self,
        hour_key: str,
        target_date: datetime,
    ) -> datetime | None:
        """Parse valid_time from hour key and target date.

        Args:
            hour_key: Hour string (e.g., "12:00" or "12:30").
            target_date: Target date for the forecast.

        Returns:
            Timezone-aware datetime or None if parsing fails.
        """
        try:
            parts = hour_key.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0

            return target_date.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
                tzinfo=timezone.utc,
            )
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse hour key '{hour_key}': {e}")
            return None

    def _calculate_wind_speed(self, u: float, v: float) -> Decimal:
        """Calculate wind speed from U/V components.

        Args:
            u: U wind component in m/s.
            v: V wind component in m/s.

        Returns:
            Wind speed in km/h as Decimal.
        """
        speed_ms = math.sqrt(u**2 + v**2)
        speed_kmh = speed_ms * 3.6
        return Decimal(str(speed_kmh)).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    def _calculate_wind_direction(self, u: float, v: float) -> Decimal:
        """Calculate meteorological wind direction from U/V components.

        Wind direction is where the wind comes FROM (meteorological convention).

        Args:
            u: U wind component in m/s (positive = from west).
            v: V wind component in m/s (positive = from south).

        Returns:
            Wind direction in degrees (0-360) as Decimal.
        """
        if u == 0 and v == 0:
            return Decimal("0")

        # Meteorological direction: where wind comes FROM
        # atan2(-u, -v) gives direction wind is coming from
        direction_rad = math.atan2(-u, -v)
        direction_deg = math.degrees(direction_rad)

        # Normalize to 0-360 range
        if direction_deg < 0:
            direction_deg += 360

        return Decimal(str(direction_deg)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

    def _is_valid_value(self, parameter: str, value: Decimal) -> bool:
        """Check if value is within valid range for parameter.

        Args:
            parameter: Parameter name (wind_speed, wind_direction, temperature).
            value: Value to validate.

        Returns:
            True if value is within valid range, False otherwise.
        """
        if parameter not in self.VALIDATION_RANGES:
            return True

        min_val, max_val = self.VALIDATION_RANGES[parameter]
        return min_val <= value <= max_val
