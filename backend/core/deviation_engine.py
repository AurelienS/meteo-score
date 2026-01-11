"""Deviation calculation engine for weather forecast accuracy analysis.

This module provides stateless functions for calculating the deviation
between forecasted and observed weather values. The core metric is the
simple difference: forecast_value - observed_value.

The deviation engine is intentionally kept simple and stateless to:
- Enable easy testing and validation
- Allow parallel processing without shared state
- Maintain clear separation from data storage concerns
"""

from decimal import Decimal

from backend.core.data_models import ForecastData, ObservationData


def calculate_deviation(
    forecast: ForecastData,
    observation: ObservationData,
) -> Decimal:
    """Calculate the deviation between a forecast and observation.

    Computes the simple difference between the forecasted value and
    the observed value. A positive deviation indicates the forecast
    predicted higher than actual; negative indicates lower.

    Args:
        forecast: The forecast data point containing the predicted value.
        observation: The observation data point containing the actual value.

    Returns:
        The deviation as a Decimal: forecast.value - observation.value

    Raises:
        ValueError: If site_id or parameter_id don't match between
            forecast and observation (they must be for the same
            location and weather parameter).

    Example:
        >>> from datetime import datetime
        >>> from decimal import Decimal
        >>> forecast = ForecastData(
        ...     site_id=1, model_id=1, parameter_id=1,
        ...     forecast_run=datetime(2026, 1, 11, 0, 0),
        ...     valid_time=datetime(2026, 1, 11, 12, 0),
        ...     horizon=12, value=Decimal("25.5")
        ... )
        >>> observation = ObservationData(
        ...     site_id=1, parameter_id=1,
        ...     observation_time=datetime(2026, 1, 11, 12, 0),
        ...     value=Decimal("22.3")
        ... )
        >>> calculate_deviation(forecast, observation)
        Decimal('3.2')
    """
    if forecast.site_id != observation.site_id:
        raise ValueError(
            f"Site ID mismatch: forecast has site_id={forecast.site_id}, "
            f"observation has site_id={observation.site_id}"
        )

    if forecast.parameter_id != observation.parameter_id:
        raise ValueError(
            f"Parameter ID mismatch: forecast has parameter_id={forecast.parameter_id}, "
            f"observation has parameter_id={observation.parameter_id}"
        )

    return forecast.value - observation.value
