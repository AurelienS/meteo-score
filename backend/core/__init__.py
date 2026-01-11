"""Core module for MétéoScore backend.

Exports:
    - Configuration: settings, get_settings, Settings
    - Database utilities: get_db, get_engine, test_connection, close_engine
    - ORM models: Base, Site, Model, Parameter, Deviation
    - Pydantic schemas: SiteResponse, ModelResponse, ParameterResponse, etc.
"""

from core.config import Settings, get_settings, settings
from core.database import (
    close_engine,
    get_async_session_factory,
    get_db,
    get_engine,
    test_connection,
)
from core.models import Base, Deviation, Model, Parameter, Site
from core.schemas import (
    HealthResponse,
    MetaResponse,
    ModelResponse,
    PaginatedResponse,
    ParameterResponse,
    SiteResponse,
)

__all__ = [
    # Configuration
    "settings",
    "get_settings",
    "Settings",
    # Database utilities
    "get_db",
    "get_engine",
    "get_async_session_factory",
    "test_connection",
    "close_engine",
    # ORM models
    "Base",
    "Site",
    "Model",
    "Parameter",
    "Deviation",
    # Pydantic schemas
    "SiteResponse",
    "ModelResponse",
    "ParameterResponse",
    "MetaResponse",
    "PaginatedResponse",
    "HealthResponse",
]
