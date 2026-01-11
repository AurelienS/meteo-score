"""Pydantic response schemas for MétéoScore API.

This module defines all response models with camelCase JSON mapping.
All schemas use Field(alias=) for snake_case to camelCase conversion.

Standard Response Format:
    {
        "data": [...],
        "meta": {"total": N, "page": 1, "perPage": 100}
    }
"""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# Generic type for paginated responses
T = TypeVar("T")


class SiteResponse(BaseModel):
    """Response schema for Site entity.

    Maps database snake_case fields to camelCase JSON keys.

    Attributes:
        id: Site identifier.
        name: Site name.
        latitude: Geographic latitude (alias: lat).
        longitude: Geographic longitude (alias: lon).
        altitude: Elevation in meters (alias: alt).
        created_at: Creation timestamp (alias: createdAt).
    """

    id: int
    name: str
    latitude: float = Field(serialization_alias="lat")
    longitude: float = Field(serialization_alias="lon")
    altitude: int = Field(serialization_alias="alt")
    created_at: datetime = Field(serialization_alias="createdAt")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class ModelResponse(BaseModel):
    """Response schema for weather forecast Model entity.

    Attributes:
        id: Model identifier.
        name: Model name (e.g., "AROME", "Meteo-Parapente").
        source: Model source description.
        created_at: Creation timestamp (alias: createdAt).
    """

    id: int
    name: str
    source: str
    created_at: datetime = Field(serialization_alias="createdAt")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class ParameterResponse(BaseModel):
    """Response schema for weather Parameter entity.

    Attributes:
        id: Parameter identifier.
        name: Parameter name (e.g., "Wind Speed").
        unit: Unit of measurement (e.g., "km/h").
        created_at: Creation timestamp (alias: createdAt).
    """

    id: int
    name: str
    unit: str
    created_at: datetime = Field(serialization_alias="createdAt")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class MetaResponse(BaseModel):
    """Pagination metadata for list responses.

    Attributes:
        total: Total number of items.
        page: Current page number (1-indexed).
        per_page: Number of items per page (alias: perPage).
    """

    total: int
    page: int = 1
    per_page: int = Field(default=100, serialization_alias="perPage")

    model_config = ConfigDict(
        populate_by_name=True,
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper.

    Standard response format for all list endpoints.

    Attributes:
        data: List of items.
        meta: Pagination metadata.

    Example:
        {
            "data": [{"id": 1, "name": "Site 1", ...}],
            "meta": {"total": 1, "page": 1, "perPage": 100}
        }
    """

    data: list[T]
    meta: MetaResponse


class HealthResponse(BaseModel):
    """Response schema for health check endpoint.

    Attributes:
        status: Health status ("healthy" when fully operational, "degraded" when
            database is unavailable).
        database: Database connectivity status (optional).
    """

    status: str
    database: str | None = None
