"""AROME forecast collector for Météo-France GRIB2 data.

This module implements the AROMECollector class for fetching
weather forecast data from the Météo-France public API in GRIB2 format.

API Documentation:
- Endpoint: https://public-api.meteofrance.fr/previnum/DPPaquetAROME/v1/
- Authentication: Bearer token from portail-api.meteofrance.fr
- Format: GRIB2 multi-message files
- Rate Limit: 50 requests per minute

AROME Model Characteristics:
- High-resolution mesoscale model for France
- Spatial resolution: ~1.3 km (0.025°)
- Temporal resolution: Hourly forecasts
- Forecast runs: 00h, 06h, 12h, 18h UTC
- Forecast range: Up to 48 hours

Data fields:
- u10: 10m U wind component (m/s)
- v10: 10m V wind component (m/s)
- t2m: 2m temperature (Kelvin)
"""

import asyncio
import logging
import math
import os
import tempfile
import time
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import xarray as xr

from collectors.base import BaseCollector
from collectors.utils import (
    HttpClient,
    HttpClientError,
    RetryExhaustedError,
    retry_with_backoff,
)
from core.data_models import ForecastData

logger = logging.getLogger(__name__)


class AROMECollector(BaseCollector):
    """Collector for AROME GRIB2 data from Météo-France.

    Retrieves weather forecast data from Météo-France public API
    in GRIB2 format and converts it to ForecastData objects.

    The collector handles:
    - GRIB2 file download from Météo-France API
    - Parsing with cfgrib and xarray
    - Coordinate interpolation to site location
    - Wind U/V to speed/direction conversion
    - Temperature Kelvin to Celsius conversion

    Attributes:
        name: Collector identifier.
        source: Data source name.
        API_ENDPOINT: Base URL for the Météo-France API.
        TIMEOUT: Request timeout in seconds (longer for GRIB2 files).
        RATE_LIMIT_PER_MINUTE: Maximum requests per minute.

    Example:
        >>> collector = AROMECollector()
        >>> forecasts = await collector.collect_forecast(
        ...     site_id=1,
        ...     forecast_run=datetime(2026, 1, 12, 6, 0, tzinfo=timezone.utc),
        ...     latitude=45.9167,
        ...     longitude=6.7000,
        ... )
    """

    name: str = "AROMECollector"
    source: str = "AROME"
    API_ENDPOINT: str = "https://public-api.meteofrance.fr/previnum/DPPaquetAROME/v1/models/AROME/grids/0.025/packages"
    TIMEOUT: float = 30.0  # Longer timeout for GRIB2 files
    RATE_LIMIT_PER_MINUTE: int = 50
    MIN_REQUEST_INTERVAL: float = 1.2  # 60/50 = 1.2 seconds between requests

    # Validation ranges for aberrant value detection (same as MeteoParapenteCollector)
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

    # GRIB2 variable names for AROME
    GRIB2_VARS = {
        "u_wind": "u10",  # 10m U wind component
        "v_wind": "v10",  # 10m V wind component
        "temperature": "t2m",  # 2m temperature
    }

    def __init__(self, api_token: str | None = None):
        """Initialize AROME collector.

        Args:
            api_token: Optional API token for Météo-France.
                       If not provided, uses METEOFRANCE_API_TOKEN env var.
        """
        self._api_token = api_token or os.getenv("METEOFRANCE_API_TOKEN", "")
        self._last_request_time: float = 0.0

    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between API requests.

        Ensures minimum interval between requests to respect
        Météo-France API rate limit of 50 requests per minute.
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
        latitude: float | None = None,
        longitude: float | None = None,
        model_id: int = 3,  # AROME model ID
        parameter_ids: dict[str, int] | None = None,
    ) -> list[ForecastData]:
        """Collect forecast data from Météo-France AROME API.

        Args:
            site_id: Database ID of the site.
            forecast_run: Datetime of the forecast model run (UTC).
            latitude: Site latitude (required for interpolation).
            longitude: Site longitude (required for interpolation).
            model_id: Database ID for AROME model (default: 3).
            parameter_ids: Mapping of parameter names to IDs.

        Returns:
            List of ForecastData objects, empty list on error.

        Raises:
            No exceptions are raised - errors return empty list.
        """
        if latitude is None or longitude is None:
            logger.warning(
                f"Missing coordinates for site {site_id}. "
                "Cannot fetch from AROME API."
            )
            return []

        if parameter_ids is None:
            parameter_ids = self.DEFAULT_PARAMETER_IDS

        try:
            # Download GRIB2 data
            grib2_bytes = await self._download_grib2(
                forecast_run=forecast_run,
                package="SP1",  # Surface parameters package
            )

            if not grib2_bytes:
                logger.warning(f"Empty GRIB2 data received for site {site_id}")
                return []

            # Parse GRIB2 to xarray dataset
            dataset = self._parse_grib2_bytes(grib2_bytes)
            if dataset is None:
                logger.warning(f"Failed to parse GRIB2 data for site {site_id}")
                return []

            try:
                # Extract forecast data
                return self._parse_grib2_data(
                    dataset=dataset,
                    site_id=site_id,
                    model_id=model_id,
                    latitude=latitude,
                    longitude=longitude,
                    forecast_run=forecast_run,
                    parameter_ids=parameter_ids,
                )
            finally:
                # Close xarray dataset to release resources
                dataset.close()

        except (HttpClientError, RetryExhaustedError) as e:
            logger.warning(
                f"HTTP error fetching AROME data for site {site_id}: {e}"
            )
            return []
        except Exception as e:
            logger.error(
                f"Unexpected error fetching AROME data for site {site_id}: {e}"
            )
            return []

    async def collect_observation(
        self,
        site_id: int,
        observation_time: datetime,  # noqa: ARG002 - Required by interface
    ) -> list[Any]:
        """Not implemented for AROME (forecast-only source).

        AROME provides forecasts only, not observations.

        Args:
            site_id: Database ID of the site.
            observation_time: Datetime of the observation (unused).

        Returns:
            Empty list (observations not supported).
        """
        logger.debug(
            f"collect_observation called for AROME site {site_id}, "
            "but this is a forecast-only source."
        )
        return []

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def _download_grib2(
        self,
        forecast_run: datetime,
        package: str = "SP1",
    ) -> bytes:
        """Download GRIB2 file from Météo-France API with retry logic.

        Args:
            forecast_run: Forecast model run datetime.
            package: AROME package name (SP1 = surface parameters).

        Returns:
            Raw GRIB2 file bytes.

        Raises:
            HttpClientError: If HTTP request fails.
            RetryExhaustedError: If all retry attempts fail.
        """
        # Enforce rate limiting before making request
        await self._enforce_rate_limit()

        url = self._build_api_url(
            forecast_run=forecast_run,
            package=package,
        )
        headers = self._get_headers()

        async with HttpClient(timeout=self.TIMEOUT, headers=headers) as client:
            # Note: For GRIB2, we need raw bytes, not JSON
            return await client.get_bytes(url)

    def _build_api_url(
        self,
        forecast_run: datetime,
        package: str = "SP1",
        time_range: str = "00H24H",
    ) -> str:
        """Build API URL for GRIB2 download.

        Args:
            forecast_run: Forecast model run datetime.
            package: AROME package (SP1, SP2, etc.).
            time_range: Forecast time range (e.g., "00H24H").

        Returns:
            Complete API URL.
        """
        # Format reference time as ISO 8601
        ref_time = forecast_run.strftime("%Y-%m-%dT%H:%M:%SZ")

        return (
            f"{self.API_ENDPOINT}/{package}/productARO"
            f"?referencetime={ref_time}"
            f"&time={time_range}"
            f"&format=grib2"
        )

    def _get_headers(self) -> dict[str, str]:
        """Get required HTTP headers for API request.

        Returns:
            Dictionary of HTTP headers.
        """
        headers = {
            "User-Agent": "MeteoScore/1.0 (Weather Forecast Accuracy Platform)",
            "Accept": "*/*",
        }

        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"

        return headers

    def _parse_grib2_bytes(self, grib2_bytes: bytes) -> xr.Dataset | None:
        """Parse GRIB2 bytes into xarray Dataset.

        Args:
            grib2_bytes: Raw GRIB2 file bytes.

        Returns:
            xarray Dataset or None if parsing fails.
        """
        if not grib2_bytes:
            return None

        try:
            # Write bytes to temporary file (cfgrib requires file path)
            with tempfile.NamedTemporaryFile(suffix=".grib2", delete=False) as f:
                f.write(grib2_bytes)
                temp_path = f.name

            try:
                # Open with cfgrib engine
                # Use filter_by_keys to get surface level data
                ds = xr.open_dataset(
                    temp_path,
                    engine="cfgrib",
                    backend_kwargs={
                        "filter_by_keys": {
                            "typeOfLevel": "heightAboveGround",
                        }
                    },
                )
                return ds
            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.warning(f"Failed to parse GRIB2 data: {e}")
            return None

    def _parse_grib2_data(
        self,
        dataset: xr.Dataset,
        site_id: int,
        model_id: int,
        latitude: float,
        longitude: float,
        forecast_run: datetime,
        parameter_ids: dict[str, int] | None = None,
    ) -> list[ForecastData]:
        """Parse xarray dataset into ForecastData objects.

        Args:
            dataset: xarray Dataset from GRIB2 file.
            site_id: Database ID of the site.
            model_id: Database ID of the model.
            latitude: Site latitude for interpolation.
            longitude: Site longitude for interpolation.
            forecast_run: Forecast model run datetime.
            parameter_ids: Mapping of parameter names to IDs.

        Returns:
            List of ForecastData objects.
        """
        if parameter_ids is None:
            parameter_ids = self.DEFAULT_PARAMETER_IDS

        results: list[ForecastData] = []

        # Check if dataset has any data
        if not dataset.data_vars:
            logger.warning("Empty dataset - no data variables found")
            return []

        # Interpolate to site location
        site_data = self._interpolate_to_site(dataset, latitude, longitude)
        if site_data is None:
            logger.warning(
                f"Failed to interpolate data to site ({latitude}, {longitude})"
            )
            return []

        # Get time coordinate
        time_coord = self._get_time_coordinate(site_data)
        if time_coord is None:
            logger.warning("No time coordinate found in dataset")
            return []

        # Process each time step
        for time_val in time_coord.values:
            try:
                # Convert numpy datetime64 to Python datetime
                valid_time = self._numpy_to_datetime(time_val)
                if valid_time is None:
                    continue

                # Calculate horizon (hours from forecast_run to valid_time)
                horizon = int((valid_time - forecast_run).total_seconds() / 3600)

                # Extract wind data if available
                wind_results = self._extract_wind_data(
                    data=site_data,
                    time_val=time_val,
                    site_id=site_id,
                    model_id=model_id,
                    parameter_ids=parameter_ids,
                    forecast_run=forecast_run,
                    valid_time=valid_time,
                    horizon=horizon,
                )
                results.extend(wind_results)

                # Extract temperature if available
                temp_result = self._extract_temperature(
                    data=site_data,
                    time_val=time_val,
                    site_id=site_id,
                    model_id=model_id,
                    parameter_ids=parameter_ids,
                    forecast_run=forecast_run,
                    valid_time=valid_time,
                    horizon=horizon,
                )
                if temp_result:
                    results.append(temp_result)

            except Exception as e:
                logger.warning(f"Error processing time step {time_val}: {e}")
                continue

        return results

    def _interpolate_to_site(
        self,
        dataset: xr.Dataset,
        latitude: float,
        longitude: float,
    ) -> xr.Dataset | None:
        """Interpolate grid data to site coordinates.

        Args:
            dataset: xarray Dataset with gridded data.
            latitude: Site latitude.
            longitude: Site longitude.

        Returns:
            Interpolated dataset or None if interpolation fails.
        """
        try:
            # Find coordinate names (may vary: latitude/lat, longitude/lon)
            lat_name = None
            lon_name = None

            for name in ["latitude", "lat"]:
                if name in dataset.coords:
                    lat_name = name
                    break

            for name in ["longitude", "lon"]:
                if name in dataset.coords:
                    lon_name = name
                    break

            if lat_name is None or lon_name is None:
                logger.warning("Could not find lat/lon coordinates in dataset")
                return None

            # Interpolate to site location
            return dataset.interp(
                {lat_name: latitude, lon_name: longitude},
                method="linear",
            )

        except Exception as e:
            logger.warning(f"Interpolation failed: {e}")
            return None

    def _get_time_coordinate(self, dataset: xr.Dataset) -> xr.DataArray | None:
        """Get time coordinate from dataset.

        Args:
            dataset: xarray Dataset.

        Returns:
            Time coordinate DataArray or None.
        """
        for name in ["valid_time", "time", "step"]:
            if name in dataset.coords:
                return dataset.coords[name]
        return None

    def _numpy_to_datetime(self, np_time: Any) -> datetime | None:
        """Convert numpy datetime64 to Python datetime.

        Args:
            np_time: numpy datetime64 value.

        Returns:
            Python datetime with UTC timezone or None.
        """
        try:
            import numpy as np

            # Handle different numpy datetime types
            if isinstance(np_time, np.datetime64):
                # Convert to timestamp and then to datetime
                ts = (np_time - np.datetime64("1970-01-01T00:00:00")) / np.timedelta64(
                    1, "s"
                )
                return datetime.fromtimestamp(float(ts), tz=timezone.utc)
            elif isinstance(np_time, datetime):
                if np_time.tzinfo is None:
                    return np_time.replace(tzinfo=timezone.utc)
                return np_time
            else:
                # Try to convert using pandas
                import pandas as pd

                return pd.Timestamp(np_time).to_pydatetime().replace(tzinfo=timezone.utc)
        except Exception as e:
            logger.warning(f"Failed to convert time value {np_time}: {e}")
            return None

    def _extract_wind_data(
        self,
        data: xr.Dataset,
        time_val: Any,
        site_id: int,
        model_id: int,
        parameter_ids: dict[str, int],
        forecast_run: datetime,
        valid_time: datetime,
        horizon: int,
    ) -> list[ForecastData]:
        """Extract wind speed and direction from data.

        Args:
            data: Interpolated xarray Dataset.
            time_val: Time value to extract.
            site_id: Database ID of the site.
            model_id: Database ID of the model.
            parameter_ids: Mapping of parameter names to IDs.
            forecast_run: Forecast model run datetime.
            valid_time: Valid time for this data.
            horizon: Forecast horizon in hours.

        Returns:
            List of ForecastData for wind speed and direction.
        """
        results: list[ForecastData] = []

        u_var = self.GRIB2_VARS["u_wind"]
        v_var = self.GRIB2_VARS["v_wind"]

        # Check if wind variables exist
        if u_var not in data.data_vars or v_var not in data.data_vars:
            return []

        try:
            # Get time coordinate name
            time_name = None
            for name in ["valid_time", "time"]:
                if name in data.coords:
                    time_name = name
                    break

            if time_name is None:
                return []

            # Extract U/V values at this time
            u_data = data[u_var].sel({time_name: time_val})
            v_data = data[v_var].sel({time_name: time_val})

            # Get scalar values (already interpolated to site)
            u = float(u_data.values.flatten()[0])
            v = float(v_data.values.flatten()[0])

            # Calculate wind speed
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
                    f"Aberrant wind speed {wind_speed} km/h at {valid_time}, skipping"
                )

            # Calculate wind direction
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
                    f"Aberrant wind direction {wind_direction}° at {valid_time}, skipping"
                )

        except Exception as e:
            logger.warning(f"Error extracting wind data: {e}")

        return results

    def _extract_temperature(
        self,
        data: xr.Dataset,
        time_val: Any,
        site_id: int,
        model_id: int,
        parameter_ids: dict[str, int],
        forecast_run: datetime,
        valid_time: datetime,
        horizon: int,
    ) -> ForecastData | None:
        """Extract temperature from data.

        Args:
            data: Interpolated xarray Dataset.
            time_val: Time value to extract.
            site_id: Database ID of the site.
            model_id: Database ID of the model.
            parameter_ids: Mapping of parameter names to IDs.
            forecast_run: Forecast model run datetime.
            valid_time: Valid time for this data.
            horizon: Forecast horizon in hours.

        Returns:
            ForecastData for temperature or None.
        """
        t_var = self.GRIB2_VARS["temperature"]

        if t_var not in data.data_vars:
            return None

        try:
            # Get time coordinate name
            time_name = None
            for name in ["valid_time", "time"]:
                if name in data.coords:
                    time_name = name
                    break

            if time_name is None:
                return None

            # Extract temperature at this time
            t_data = data[t_var].sel({time_name: time_val})
            t_kelvin = float(t_data.values.flatten()[0])

            # Convert to Celsius
            temperature = self._kelvin_to_celsius(t_kelvin)

            if self._is_valid_value("temperature", temperature):
                return ForecastData(
                    site_id=site_id,
                    model_id=model_id,
                    parameter_id=parameter_ids.get("temperature", 3),
                    forecast_run=forecast_run,
                    valid_time=valid_time,
                    horizon=horizon,
                    value=temperature,
                )
            else:
                logger.warning(
                    f"Aberrant temperature {temperature}°C at {valid_time}, skipping"
                )
                return None

        except Exception as e:
            logger.warning(f"Error extracting temperature: {e}")
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

    def _kelvin_to_celsius(self, kelvin: float) -> Decimal:
        """Convert temperature from Kelvin to Celsius.

        Args:
            kelvin: Temperature in Kelvin.

        Returns:
            Temperature in Celsius as Decimal.
        """
        celsius = kelvin - 273.15
        return Decimal(str(celsius)).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
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
