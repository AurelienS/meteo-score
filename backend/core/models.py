"""SQLAlchemy ORM models for MétéoScore.

This module defines the database schema for storing weather deviation data.
All models use async-compatible patterns with SQLAlchemy 2.0 style.

Tables:
    - sites: Weather observation/forecast locations
    - models: Weather forecast model sources (AROME, Meteo-Parapente, etc.)
    - parameters: Weather parameters (wind speed, direction, temperature)
    - deviations: Time-series data storing forecast vs observation deviations (hypertable)
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class Site(Base):
    """Weather observation/forecast location.

    Represents a geographic location where weather data is collected.
    For example: Passy Plaine Joux paragliding site.

    Attributes:
        id: Primary key, auto-incremented.
        name: Human-readable site name.
        latitude: Geographic latitude (decimal degrees).
        longitude: Geographic longitude (decimal degrees).
        altitude: Elevation in meters above sea level.
        created_at: Timestamp when record was created.
        deviations: Relationship to deviation records for this site.
    """

    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(DECIMAL(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(DECIMAL(9, 6), nullable=False)
    altitude: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    deviations: Mapped[list["Deviation"]] = relationship(
        "Deviation", back_populates="site", lazy="selectin"
    )

    def __repr__(self) -> str:
        """Return string representation of Site."""
        return f"<Site(id={self.id}, name='{self.name}', alt={self.altitude}m)>"


class Model(Base):
    """Weather forecast model source.

    Represents a weather prediction model or service.
    For example: AROME (Météo-France) or Meteo-Parapente.

    Attributes:
        id: Primary key, auto-incremented.
        name: Unique model identifier (e.g., "AROME", "Meteo-Parapente").
        source: Description of the model source/origin.
        created_at: Timestamp when record was created.
        deviations: Relationship to deviation records from this model.
    """

    __tablename__ = "models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    deviations: Mapped[list["Deviation"]] = relationship(
        "Deviation", back_populates="model", lazy="selectin"
    )

    def __repr__(self) -> str:
        """Return string representation of Model."""
        return f"<Model(id={self.id}, name='{self.name}')>"


class Parameter(Base):
    """Weather parameter type.

    Represents a measurable weather variable.
    For example: Wind Speed (km/h), Wind Direction (degrees), Temperature (°C).

    Attributes:
        id: Primary key, auto-incremented.
        name: Unique parameter name (e.g., "Wind Speed").
        unit: Unit of measurement (e.g., "km/h", "degrees", "°C").
        created_at: Timestamp when record was created.
        deviations: Relationship to deviation records for this parameter.
    """

    __tablename__ = "parameters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    deviations: Mapped[list["Deviation"]] = relationship(
        "Deviation", back_populates="parameter", lazy="selectin"
    )

    def __repr__(self) -> str:
        """Return string representation of Parameter."""
        return f"<Parameter(id={self.id}, name='{self.name}', unit='{self.unit}')>"


class Deviation(Base):
    """Weather forecast deviation record (time-series hypertable).

    Stores the difference between forecasted and observed weather values.
    This is the core time-series data table, converted to a TimescaleDB hypertable.

    The composite primary key includes timestamp (required for hypertables).
    Each record captures a single forecast-observation comparison at a specific
    point in time, for a specific site, model, parameter, and forecast horizon.

    Attributes:
        timestamp: Time of the observation (part of composite PK).
        site_id: Foreign key to sites table.
        model_id: Foreign key to models table.
        parameter_id: Foreign key to parameters table.
        horizon: Forecast lead time in hours (e.g., 6h, 12h, 24h ahead).
        forecast_value: Predicted value from the weather model.
        observed_value: Actual measured value from observations.
        deviation: Calculated difference (forecast - observed).
        created_at: Timestamp when record was inserted.
        site: Relationship to Site object.
        model: Relationship to Model object.
        parameter: Relationship to Parameter object.
    """

    __tablename__ = "deviations"

    # Composite primary key - timestamp must be first for hypertable
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )
    site_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sites.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("models.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    parameter_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("parameters.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    horizon: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    # Data columns
    forecast_value: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    observed_value: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    deviation: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    site: Mapped["Site"] = relationship("Site", back_populates="deviations")
    model: Mapped["Model"] = relationship("Model", back_populates="deviations")
    parameter: Mapped["Parameter"] = relationship(
        "Parameter", back_populates="deviations"
    )

    # Indexes defined at table level for better control
    __table_args__ = (
        Index("idx_deviations_site_model", "site_id", "model_id"),
        Index("idx_deviations_parameter", "parameter_id"),
        Index("idx_deviations_timestamp", timestamp.desc()),
    )

    def __repr__(self) -> str:
        """Return string representation of Deviation."""
        return (
            f"<Deviation(ts={self.timestamp}, site={self.site_id}, "
            f"model={self.model_id}, param={self.parameter_id}, "
            f"dev={self.deviation})>"
        )
