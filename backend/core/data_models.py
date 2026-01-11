"""Data transfer objects for weather data collection.

This module defines lightweight dataclasses for passing data between
collectors and the database layer. These are NOT ORM models - they are
simple data containers for in-memory data transfer.

Note:
    - ForecastData: Represents forecast values from weather models
    - ObservationData: Represents actual observed values from beacons
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ForecastData:
    """Data transfer object for forecast values.

    Represents a single forecast data point collected from a weather
    prediction model (e.g., AROME, Meteo-Parapente).

    Attributes:
        site_id: ID of the observation site.
        model_id: ID of the weather model source.
        parameter_id: ID of the weather parameter (wind speed, temp, etc.).
        forecast_run: When the forecast was generated (model run time).
        valid_time: When the forecast is valid for (target time).
        horizon: Hours ahead from forecast_run to valid_time.
        value: The forecasted value in the parameter's unit.

    Example:
        >>> forecast = ForecastData(
        ...     site_id=1,
        ...     model_id=1,
        ...     parameter_id=1,
        ...     forecast_run=datetime(2026, 1, 11, 0, 0),
        ...     valid_time=datetime(2026, 1, 11, 12, 0),
        ...     horizon=12,
        ...     value=Decimal("25.5")
        ... )
    """

    site_id: int
    model_id: int
    parameter_id: int
    forecast_run: datetime
    valid_time: datetime
    horizon: int
    value: Decimal


@dataclass(frozen=True)
class ObservationData:
    """Data transfer object for observation values.

    Represents a single observation data point collected from a
    weather beacon (e.g., ROMMA, FFVL stations).

    Attributes:
        site_id: ID of the observation site.
        parameter_id: ID of the weather parameter (wind speed, temp, etc.).
        observation_time: When the observation was recorded.
        value: The observed value in the parameter's unit.

    Example:
        >>> observation = ObservationData(
        ...     site_id=1,
        ...     parameter_id=1,
        ...     observation_time=datetime(2026, 1, 11, 12, 0),
        ...     value=Decimal("22.3")
        ... )
    """

    site_id: int
    parameter_id: int
    observation_time: datetime
    value: Decimal
