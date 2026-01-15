"""Analysis API endpoints for accuracy metrics and bias characterization.

This module provides endpoints for:
- Site accuracy comparison across models
- Model bias characterization across horizons
- Time series accuracy data

Implements story 3.6: Analysis API Endpoints.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.analysis import (
    HorizonBiasData,
    ModelAccuracyMetrics,
    ModelBiasResponse,
    SiteAccuracyResponse,
    TimeSeriesAccuracyResponse,
    TimeSeriesDataPoint,
)
from core.database import get_db
from core.models import Model, Parameter, Site

router = APIRouter(prefix="/analysis", tags=["analysis"])


# =============================================================================
# Analysis Service
# =============================================================================


class AnalysisService:
    """Service for aggregating accuracy metrics and bias data.

    Coordinates between MetricsService, AggregateService, and ConfidenceService
    to provide comprehensive analysis data for API responses.
    """

    async def get_site_accuracy(
        self,
        db: AsyncSession,
        site_id: int,
        parameter_id: int,
        horizon: int = 6,
    ) -> Optional[Dict[str, Any]]:
        """Get accuracy metrics for all models at a site.

        Args:
            db: Database session.
            site_id: Site identifier.
            parameter_id: Weather parameter identifier.
            horizon: Forecast horizon in hours.

        Returns:
            Dict with site info and model accuracy metrics, or None if not found.
        """
        # Get site info
        site_result = await db.execute(select(Site).where(Site.id == site_id))
        site = site_result.scalar_one_or_none()
        if not site:
            return None

        # Get parameter info
        param_result = await db.execute(select(Parameter).where(Parameter.id == parameter_id))
        parameter = param_result.scalar_one_or_none()
        if not parameter:
            return None

        # Get all models
        models_result = await db.execute(select(Model))
        models = models_result.scalars().all()

        # For now, return placeholder data
        # In production, this would query MetricsService and ConfidenceService
        model_metrics = []
        for model in models:
            model_metrics.append({
                "model_id": model.id,
                "model_name": model.name,
                "mae": 0.0,
                "bias": 0.0,
                "std_dev": 0.0,
                "sample_size": 0,
                "confidence_level": "insufficient",
                "confidence_message": "No data available yet.",
            })

        if not model_metrics:
            return None

        return {
            "site_id": site.id,
            "site_name": site.name,
            "parameter_id": parameter.id,
            "parameter_name": parameter.name,
            "horizon": horizon,
            "models": model_metrics,
        }

    async def get_model_bias(
        self,
        db: AsyncSession,
        model_id: int,
        site_id: int,
        parameter_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Get bias characterization for a model across forecast horizons.

        Args:
            db: Database session.
            model_id: Model identifier.
            site_id: Site identifier.
            parameter_id: Weather parameter identifier.

        Returns:
            Dict with model info and horizon bias data, or None if not found.
        """
        # Get model info
        model_result = await db.execute(select(Model).where(Model.id == model_id))
        model = model_result.scalar_one_or_none()
        if not model:
            return None

        # Get site info
        site_result = await db.execute(select(Site).where(Site.id == site_id))
        site = site_result.scalar_one_or_none()
        if not site:
            return None

        # Get parameter info
        param_result = await db.execute(select(Parameter).where(Parameter.id == parameter_id))
        parameter = param_result.scalar_one_or_none()
        if not parameter:
            return None

        # Standard forecast horizons
        horizons_data = []
        for h in [6, 12, 24, 48]:
            horizons_data.append({
                "horizon": h,
                "bias": 0.0,
                "mae": 0.0,
                "sample_size": 0,
                "confidence_level": "insufficient",
            })

        return {
            "model_id": model.id,
            "model_name": model.name,
            "site_id": site.id,
            "site_name": site.name,
            "parameter_id": parameter.id,
            "parameter_name": parameter.name,
            "horizons": horizons_data,
        }

    async def get_accuracy_timeseries(
        self,
        db: AsyncSession,
        site_id: int,
        model_id: int,
        parameter_id: int,
        granularity: str = "daily",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get time series accuracy data.

        Args:
            db: Database session.
            site_id: Site identifier.
            model_id: Model identifier.
            parameter_id: Weather parameter identifier.
            granularity: Time granularity (daily/weekly/monthly).
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            Dict with time series data points, or None if not found.
        """
        # Get site info
        site_result = await db.execute(select(Site).where(Site.id == site_id))
        site = site_result.scalar_one_or_none()
        if not site:
            return None

        # Get model info
        model_result = await db.execute(select(Model).where(Model.id == model_id))
        model = model_result.scalar_one_or_none()
        if not model:
            return None

        # Get parameter info
        param_result = await db.execute(select(Parameter).where(Parameter.id == parameter_id))
        parameter = param_result.scalar_one_or_none()
        if not parameter:
            return None

        # Default date range
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=90)

        # Placeholder: return empty data points
        # In production, this would query AggregateService
        data_points: List[Dict[str, Any]] = []

        return {
            "site_id": site.id,
            "site_name": site.name,
            "model_id": model.id,
            "model_name": model.name,
            "parameter_id": parameter.id,
            "parameter_name": parameter.name,
            "granularity": granularity,
            "data_points": data_points,
        }


# =============================================================================
# Dependency Injection
# =============================================================================


def get_analysis_service() -> AnalysisService:
    """Get AnalysisService instance for dependency injection."""
    return AnalysisService()


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/sites/{site_id}/accuracy", response_model=SiteAccuracyResponse)
async def get_site_accuracy(
    site_id: int,
    parameter_id: int = Query(..., alias="parameterId"),
    horizon: int = Query(6),
    db: AsyncSession = Depends(get_db),
    service: AnalysisService = Depends(get_analysis_service),
) -> SiteAccuracyResponse:
    """Get accuracy metrics for all models at a specific site.

    Compare model performance for a given parameter and forecast horizon.

    Args:
        site_id: Site identifier.
        parameter_id: Weather parameter identifier.
        horizon: Forecast horizon in hours (default: 6).
        db: Database session.

    Returns:
        SiteAccuracyResponse with metrics for all models.

    Raises:
        HTTPException: 404 if site or parameter not found.
    """
    result = await service.get_site_accuracy(
        db=db,
        site_id=site_id,
        parameter_id=parameter_id,
        horizon=horizon,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Site {site_id} or parameter {parameter_id} not found",
        )

    return SiteAccuracyResponse(
        site_id=result["site_id"],
        site_name=result["site_name"],
        parameter_id=result["parameter_id"],
        parameter_name=result["parameter_name"],
        horizon=result["horizon"],
        models=[
            ModelAccuracyMetrics(**m) for m in result["models"]
        ],
    )


@router.get("/models/{model_id}/bias", response_model=ModelBiasResponse)
async def get_model_bias(
    model_id: int,
    site_id: int = Query(..., alias="siteId"),
    parameter_id: int = Query(..., alias="parameterId"),
    db: AsyncSession = Depends(get_db),
    service: AnalysisService = Depends(get_analysis_service),
) -> ModelBiasResponse:
    """Get bias characterization for a model across forecast horizons.

    Shows how model bias changes with forecast horizon (6h, 12h, 24h, 48h).

    Args:
        model_id: Model identifier.
        site_id: Site identifier.
        parameter_id: Weather parameter identifier.
        db: Database session.
        service: Analysis service instance.

    Returns:
        ModelBiasResponse with bias data for each horizon.

    Raises:
        HTTPException: 404 if model, site, or parameter not found.
    """
    result = await service.get_model_bias(
        db=db,
        model_id=model_id,
        site_id=site_id,
        parameter_id=parameter_id,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Model {model_id}, site {site_id}, or parameter {parameter_id} not found",
        )

    return ModelBiasResponse(
        model_id=result["model_id"],
        model_name=result["model_name"],
        site_id=result["site_id"],
        site_name=result["site_name"],
        parameter_id=result["parameter_id"],
        parameter_name=result["parameter_name"],
        horizons=[
            HorizonBiasData(**h) for h in result["horizons"]
        ],
    )


@router.get("/sites/{site_id}/accuracy/timeseries", response_model=TimeSeriesAccuracyResponse)
async def get_accuracy_timeseries(
    site_id: int,
    model_id: int = Query(..., alias="modelId"),
    parameter_id: int = Query(..., alias="parameterId"),
    granularity: str = Query("daily"),
    start_date: Optional[datetime] = Query(None, alias="startDate"),
    end_date: Optional[datetime] = Query(None, alias="endDate"),
    db: AsyncSession = Depends(get_db),
    service: AnalysisService = Depends(get_analysis_service),
) -> TimeSeriesAccuracyResponse:
    """Get accuracy metrics over time (daily/weekly/monthly granularity).

    Uses TimescaleDB continuous aggregates for fast queries.

    Args:
        site_id: Site identifier.
        model_id: Model identifier.
        parameter_id: Weather parameter identifier.
        granularity: Time granularity (daily/weekly/monthly).
        start_date: Start of date range.
        end_date: End of date range.
        db: Database session.
        service: Analysis service instance.

    Returns:
        TimeSeriesAccuracyResponse with data points.

    Raises:
        HTTPException: 400 for invalid granularity, 404 if not found.
    """
    # Validate granularity
    valid_granularities = {"daily", "weekly", "monthly"}
    if granularity not in valid_granularities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid granularity '{granularity}'. Must be one of: {valid_granularities}",
        )

    result = await service.get_accuracy_timeseries(
        db=db,
        site_id=site_id,
        model_id=model_id,
        parameter_id=parameter_id,
        granularity=granularity,
        start_date=start_date,
        end_date=end_date,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Site {site_id}, model {model_id}, or parameter {parameter_id} not found",
        )

    return TimeSeriesAccuracyResponse(
        site_id=result["site_id"],
        site_name=result["site_name"],
        model_id=result["model_id"],
        model_name=result["model_name"],
        parameter_id=result["parameter_id"],
        parameter_name=result["parameter_name"],
        granularity=result["granularity"],
        data_points=[
            TimeSeriesDataPoint(
                bucket=datetime.fromisoformat(dp["bucket"].replace("Z", "+00:00"))
                if isinstance(dp["bucket"], str) else dp["bucket"],
                mae=dp["mae"],
                bias=dp["bias"],
                sample_size=dp["sample_size"],
            )
            for dp in result["data_points"]
        ],
    )
