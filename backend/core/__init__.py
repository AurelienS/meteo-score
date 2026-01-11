"""Core module for MétéoScore backend.

Exports:
    - Database utilities: get_db, get_engine, test_connection, close_engine
    - ORM models: Base, Site, Model, Parameter, Deviation
"""

from core.database import (
    close_engine,
    get_async_session_factory,
    get_db,
    get_engine,
    test_connection,
)
from core.models import Base, Deviation, Model, Parameter, Site

__all__ = [
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
]
