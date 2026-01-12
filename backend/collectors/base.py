"""Base collector interface for weather data sources.

This module defines the abstract base class that all weather data
collectors must implement. The Strategy pattern allows uniform
orchestration of different data sources (AROME, Meteo-Parapente,
ROMMA, FFVL) through a common interface.

All concrete collectors inherit from BaseCollector and implement
the abstract methods for collecting forecast and observation data.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from core.data_models import ForecastData, ObservationData


class BaseCollector(ABC):
    """Abstract base class for weather data collectors.

    Defines the interface that all weather data collectors must implement.
    Collectors are responsible for fetching data from external sources
    and converting it to the standard ForecastData/ObservationData format.

    Each concrete collector handles:
    - Connection to specific data source (API, file, scraping)
    - Parsing source-specific data formats (JSON, GRIB2, HTML)
    - Converting to standard data transfer objects
    - Error handling and retry logic

    Attributes:
        name: Human-readable name of the collector.
        source: Description of the data source.

    Example:
        >>> class MeteoParapenteCollector(BaseCollector):
        ...     name = "Meteo-Parapente"
        ...     source = "Meteo-Parapente API"
        ...
        ...     async def collect_forecast(self, site_id, forecast_run):
        ...         # Fetch from Meteo-Parapente API
        ...         ...
        ...
        ...     async def collect_observation(self, site_id, observation_time):
        ...         # Meteo-Parapente doesn't provide observations
        ...         return []
    """

    name: str = "BaseCollector"
    source: str = "Unknown"

    @abstractmethod
    async def collect_forecast(
        self,
        site_id: int,
        forecast_run: datetime,
    ) -> List[ForecastData]:
        """Collect forecast data for a specific site and forecast run.

        Fetches forecast predictions from the data source for the given
        site and model run time. Returns multiple data points for different
        parameters (wind speed, direction, temperature) and horizons.

        Args:
            site_id: ID of the observation site to collect forecasts for.
            forecast_run: The model run timestamp (when forecast was generated).

        Returns:
            List of ForecastData objects, one per parameter/horizon combination.
            Returns empty list if no forecasts available for the given inputs.

        Raises:
            CollectorError: If the data source is unavailable or returns
                invalid data after all retry attempts.

        Note:
            Implementations should use retry_with_backoff decorator for
            resilient API calls and proper error handling.
        """
        pass

    @abstractmethod
    async def collect_observation(
        self,
        site_id: int,
        observation_time: datetime,
    ) -> List[ObservationData]:
        """Collect observation data for a specific site and time.

        Fetches actual observed weather values from the data source
        (typically weather beacons or stations) for the given site
        and observation time.

        Args:
            site_id: ID of the observation site to collect observations for.
            observation_time: The target observation timestamp.

        Returns:
            List of ObservationData objects, one per parameter.
            Returns empty list if no observations available for the given inputs.

        Raises:
            CollectorError: If the data source is unavailable or returns
                invalid data after all retry attempts.

        Note:
            Not all collectors provide observations. Forecast-only collectors
            (like AROME, Meteo-Parapente) should return an empty list.
            Observation collectors (ROMMA, FFVL) implement the actual logic.
        """
        pass
