"""Pydantic schemas for analysis API endpoints.

This module defines response schemas for accuracy metrics, bias characterization,
and time series data. All schemas use Field aliases for camelCase JSON output.

Implements story 3.6: Analysis API Endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelAccuracyMetrics(BaseModel):
    """Accuracy metrics for a single forecast model.

    Attributes:
        model_id: Model identifier.
        model_name: Human-readable model name.
        mae: Mean Absolute Error.
        bias: Average deviation (positive = over-forecast).
        std_dev: Standard deviation of errors.
        sample_size: Number of data points used.
        confidence_level: Data reliability level (insufficient/preliminary/validated).
        confidence_message: User-friendly message about data reliability.
    """

    model_config = ConfigDict(populate_by_name=True)

    model_id: int = Field(..., serialization_alias="modelId")
    model_name: str = Field(..., serialization_alias="modelName")
    mae: float
    bias: float
    std_dev: float = Field(..., serialization_alias="stdDev")
    sample_size: int = Field(..., serialization_alias="sampleSize")
    confidence_level: str = Field(..., serialization_alias="confidenceLevel")
    confidence_message: str = Field(..., serialization_alias="confidenceMessage")


class SiteAccuracyResponse(BaseModel):
    """Response schema for site accuracy comparison across models.

    Attributes:
        site_id: Site identifier.
        site_name: Human-readable site name.
        parameter_id: Weather parameter identifier.
        parameter_name: Human-readable parameter name.
        horizon: Forecast horizon in hours.
        models: List of accuracy metrics for each model.
    """

    model_config = ConfigDict(populate_by_name=True)

    site_id: int = Field(..., serialization_alias="siteId")
    site_name: str = Field(..., serialization_alias="siteName")
    parameter_id: int = Field(..., serialization_alias="parameterId")
    parameter_name: str = Field(..., serialization_alias="parameterName")
    horizon: int
    models: List[ModelAccuracyMetrics]


class HorizonBiasData(BaseModel):
    """Bias data for a specific forecast horizon.

    Attributes:
        horizon: Forecast horizon in hours.
        bias: Average deviation at this horizon.
        mae: Mean Absolute Error at this horizon.
        sample_size: Number of data points.
        confidence_level: Data reliability level.
    """

    model_config = ConfigDict(populate_by_name=True)

    horizon: int
    bias: float
    mae: float
    sample_size: int = Field(..., serialization_alias="sampleSize")
    confidence_level: str = Field(..., serialization_alias="confidenceLevel")


class ModelBiasResponse(BaseModel):
    """Response schema for model bias characterization across horizons.

    Attributes:
        model_id: Model identifier.
        model_name: Human-readable model name.
        site_id: Site identifier.
        site_name: Human-readable site name.
        parameter_id: Weather parameter identifier.
        parameter_name: Human-readable parameter name.
        horizons: List of bias data for each forecast horizon.
    """

    model_config = ConfigDict(populate_by_name=True)

    model_id: int = Field(..., serialization_alias="modelId")
    model_name: str = Field(..., serialization_alias="modelName")
    site_id: int = Field(..., serialization_alias="siteId")
    site_name: str = Field(..., serialization_alias="siteName")
    parameter_id: int = Field(..., serialization_alias="parameterId")
    parameter_name: str = Field(..., serialization_alias="parameterName")
    horizons: List[HorizonBiasData]


class TimeSeriesDataPoint(BaseModel):
    """Single data point in time series accuracy data.

    Attributes:
        bucket: Time bucket (start of period).
        mae: Mean Absolute Error for the period.
        bias: Average deviation for the period.
        sample_size: Number of data points in the period.
        avg_forecast: Average forecast value for the period.
        avg_observed: Average observed value for the period.
    """

    model_config = ConfigDict(populate_by_name=True)

    bucket: datetime
    mae: float
    bias: float
    sample_size: int = Field(..., serialization_alias="sampleSize")
    avg_forecast: Optional[float] = Field(None, serialization_alias="avgForecast")
    avg_observed: Optional[float] = Field(None, serialization_alias="avgObserved")


class TimeSeriesAccuracyResponse(BaseModel):
    """Response schema for time series accuracy data.

    Attributes:
        site_id: Site identifier.
        site_name: Human-readable site name.
        model_id: Model identifier.
        model_name: Human-readable model name.
        parameter_id: Weather parameter identifier.
        parameter_name: Human-readable parameter name.
        granularity: Time granularity (daily/weekly/monthly).
        data_points: List of time series data points.
    """

    model_config = ConfigDict(populate_by_name=True)

    site_id: int = Field(..., serialization_alias="siteId")
    site_name: str = Field(..., serialization_alias="siteName")
    model_id: int = Field(..., serialization_alias="modelId")
    model_name: str = Field(..., serialization_alias="modelName")
    parameter_id: int = Field(..., serialization_alias="parameterId")
    parameter_name: str = Field(..., serialization_alias="parameterName")
    granularity: str
    data_points: List[TimeSeriesDataPoint] = Field(..., serialization_alias="dataPoints")
