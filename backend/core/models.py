"""SQLAlchemy ORM models for MétéoScore.

This module defines the database schema for storing weather deviation data.
All models use async-compatible patterns with SQLAlchemy 2.0 style.

Tables:
    - sites: Weather observation/forecast locations
    - models: Weather forecast model sources (AROME, Meteo-Parapente, etc.)
    - parameters: Weather parameters (wind speed, direction, temperature)
    - forecasts: Individual forecast predictions from weather models
    - observations: Actual observed values from weather beacons
    - forecast_observation_pairs: Staging table for matched forecast-observation pairs
    - deviations: Time-series data storing forecast vs observation deviations (hypertable)
"""

from datetime import datetime
from decimal import Decimal

from typing import Optional

from sqlalchemy import (
    DECIMAL,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
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


class Forecast(Base):
    """Individual forecast prediction from a weather model.

    Stores forecast data collected from weather models (AROME, Meteo-Parapente, etc.)
    before matching with observations. This is intermediate storage for the matching
    pipeline.

    Attributes:
        id: Primary key, auto-incremented.
        site_id: Foreign key to sites table.
        model_id: Foreign key to models table.
        parameter_id: Foreign key to parameters table.
        forecast_run: When the forecast was generated (model run time).
        valid_time: When the forecast is valid for (target time).
        value: The forecasted value in the parameter's unit.
        created_at: Timestamp when record was created.
    """

    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=False,
    )
    parameter_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("parameters.id", ondelete="CASCADE"),
        nullable=False,
    )
    forecast_run: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    valid_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    value: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    site: Mapped["Site"] = relationship("Site", lazy="selectin")
    model: Mapped["Model"] = relationship("Model", lazy="selectin")
    parameter: Mapped["Parameter"] = relationship("Parameter", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "site_id", "model_id", "parameter_id", "forecast_run", "valid_time",
            name="uq_forecasts_unique"
        ),
        Index("idx_forecasts_site_model_param", "site_id", "model_id", "parameter_id"),
        Index("idx_forecasts_valid_time", "valid_time"),
    )

    def __repr__(self) -> str:
        """Return string representation of Forecast."""
        return (
            f"<Forecast(id={self.id}, site={self.site_id}, model={self.model_id}, "
            f"valid={self.valid_time}, value={self.value})>"
        )


class Observation(Base):
    """Actual observed value from a weather beacon.

    Stores observation data collected from weather beacons (ROMMA, FFVL, etc.)
    before matching with forecasts. This is intermediate storage for the matching
    pipeline.

    Attributes:
        id: Primary key, auto-incremented.
        site_id: Foreign key to sites table.
        parameter_id: Foreign key to parameters table.
        observation_time: When the observation was recorded.
        value: The observed value in the parameter's unit.
        source: Data source identifier (e.g., 'ROMMA', 'FFVL').
        created_at: Timestamp when record was created.
    """

    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    parameter_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("parameters.id", ondelete="CASCADE"),
        nullable=False,
    )
    observation_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    value: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    site: Mapped["Site"] = relationship("Site", lazy="selectin")
    parameter: Mapped["Parameter"] = relationship("Parameter", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "site_id", "parameter_id", "observation_time", "source",
            name="uq_observations_unique"
        ),
        Index("idx_observations_site_param", "site_id", "parameter_id"),
        Index("idx_observations_time", "observation_time"),
    )

    def __repr__(self) -> str:
        """Return string representation of Observation."""
        return (
            f"<Observation(id={self.id}, site={self.site_id}, "
            f"time={self.observation_time}, value={self.value})>"
        )


class ForecastObservationPair(Base):
    """Matched forecast-observation pair for deviation calculation.

    Staging table that stores matched pairs of forecasts and observations
    within the time tolerance window. These pairs are then used by the
    DeviationService to calculate and store deviations in the hypertable.

    Attributes:
        id: Primary key, auto-incremented.
        forecast_id: Foreign key to forecasts table.
        observation_id: Foreign key to observations table.
        site_id: Foreign key to sites table (denormalized for query efficiency).
        model_id: Foreign key to models table (denormalized for query efficiency).
        parameter_id: Foreign key to parameters table (denormalized for query efficiency).
        forecast_run: When the forecast was generated.
        valid_time: When the forecast is valid for.
        horizon: Forecast lead time in hours (valid_time - forecast_run).
        forecast_value: The predicted value.
        observed_value: The actual observed value.
        time_diff_minutes: Actual time difference for quality tracking.
        processed_at: Timestamp when pair was processed into deviation (NULL if not yet).
        created_at: Timestamp when pair was created.
    """

    __tablename__ = "forecast_observation_pairs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("forecasts.id", ondelete="CASCADE"),
        nullable=False,
    )
    observation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("observations.id", ondelete="CASCADE"),
        nullable=False,
    )
    site_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=False,
    )
    parameter_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("parameters.id", ondelete="CASCADE"),
        nullable=False,
    )
    forecast_run: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    valid_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    forecast_value: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    observed_value: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    time_diff_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    forecast: Mapped["Forecast"] = relationship("Forecast", lazy="selectin")
    observation: Mapped["Observation"] = relationship("Observation", lazy="selectin")
    site: Mapped["Site"] = relationship("Site", lazy="selectin")
    model: Mapped["Model"] = relationship("Model", lazy="selectin")
    parameter: Mapped["Parameter"] = relationship("Parameter", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "forecast_id", "observation_id",
            name="uq_pairs_forecast_observation"
        ),
        Index("idx_pairs_site_model_param", "site_id", "model_id", "parameter_id"),
        Index("idx_pairs_valid_time", "valid_time"),
        Index("idx_pairs_horizon", "horizon"),
    )

    def __repr__(self) -> str:
        """Return string representation of ForecastObservationPair."""
        return (
            f"<ForecastObservationPair(id={self.id}, forecast={self.forecast_id}, "
            f"observation={self.observation_id}, horizon={self.horizon}h)>"
        )
