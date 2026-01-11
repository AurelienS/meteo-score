"""Tests for SQLAlchemy ORM models.

Tests verify:
- Model instantiation and field types
- Database persistence and retrieval
- Relationships between models
- Unique constraints
- String representations
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from core.models import Deviation, Model, Parameter, Site


class TestSiteModel:
    """Tests for Site model."""

    @pytest.mark.asyncio
    async def test_create_site(self, test_db, sample_site_data):
        """Test creating a site record."""
        site = Site(**sample_site_data)
        test_db.add(site)
        await test_db.flush()

        assert site.id is not None
        assert site.name == sample_site_data["name"]
        assert site.latitude == sample_site_data["latitude"]
        assert site.longitude == sample_site_data["longitude"]
        assert site.altitude == sample_site_data["altitude"]

    @pytest.mark.asyncio
    async def test_site_created_at_default(self, test_db, sample_site_data):
        """Test that created_at is set automatically."""
        site = Site(**sample_site_data)
        test_db.add(site)
        await test_db.flush()

        # created_at should be set by database default
        assert site.created_at is not None

    @pytest.mark.asyncio
    async def test_site_repr(self, sample_site_data):
        """Test Site string representation."""
        site = Site(id=1, **sample_site_data)
        repr_str = repr(site)

        assert "Site" in repr_str
        assert "id=1" in repr_str
        assert sample_site_data["name"] in repr_str
        assert str(sample_site_data["altitude"]) in repr_str

    @pytest.mark.asyncio
    async def test_retrieve_site(self, test_db, sample_site_data):
        """Test retrieving a site from database."""
        # Insert
        site = Site(**sample_site_data)
        test_db.add(site)
        await test_db.flush()
        site_id = site.id

        # Retrieve
        result = await test_db.execute(select(Site).where(Site.id == site_id))
        retrieved = result.scalar_one()

        assert retrieved.name == sample_site_data["name"]
        assert retrieved.altitude == sample_site_data["altitude"]


class TestModelModel:
    """Tests for Model (weather forecast model) ORM class."""

    @pytest.mark.asyncio
    async def test_create_model(self, test_db, sample_model_data):
        """Test creating a weather model record."""
        model = Model(**sample_model_data)
        test_db.add(model)
        await test_db.flush()

        assert model.id is not None
        assert model.name == sample_model_data["name"]
        assert model.source == sample_model_data["source"]

    @pytest.mark.asyncio
    async def test_model_unique_name(self, test_db, sample_model_data):
        """Test that model name must be unique."""
        model1 = Model(**sample_model_data)
        test_db.add(model1)
        await test_db.flush()

        # Try to add another model with same name
        model2 = Model(**sample_model_data)
        test_db.add(model2)

        with pytest.raises(Exception):  # IntegrityError
            await test_db.flush()

    @pytest.mark.asyncio
    async def test_model_repr(self, sample_model_data):
        """Test Model string representation."""
        model = Model(id=1, **sample_model_data)
        repr_str = repr(model)

        assert "Model" in repr_str
        assert "id=1" in repr_str
        assert sample_model_data["name"] in repr_str


class TestParameterModel:
    """Tests for Parameter model."""

    @pytest.mark.asyncio
    async def test_create_parameter(self, test_db, sample_parameter_data):
        """Test creating a parameter record."""
        param = Parameter(**sample_parameter_data)
        test_db.add(param)
        await test_db.flush()

        assert param.id is not None
        assert param.name == sample_parameter_data["name"]
        assert param.unit == sample_parameter_data["unit"]

    @pytest.mark.asyncio
    async def test_parameter_unique_name(self, test_db, sample_parameter_data):
        """Test that parameter name must be unique."""
        param1 = Parameter(**sample_parameter_data)
        test_db.add(param1)
        await test_db.flush()

        param2 = Parameter(**sample_parameter_data)
        test_db.add(param2)

        with pytest.raises(Exception):  # IntegrityError
            await test_db.flush()

    @pytest.mark.asyncio
    async def test_parameter_repr(self, sample_parameter_data):
        """Test Parameter string representation."""
        param = Parameter(id=1, **sample_parameter_data)
        repr_str = repr(param)

        assert "Parameter" in repr_str
        assert "id=1" in repr_str
        assert sample_parameter_data["name"] in repr_str
        assert sample_parameter_data["unit"] in repr_str


class TestDeviationModel:
    """Tests for Deviation model."""

    @pytest.mark.asyncio
    async def test_create_deviation(self, test_db, sample_site_data, sample_model_data, sample_parameter_data):
        """Test creating a deviation record with foreign keys."""
        # Create reference data first
        site = Site(**sample_site_data)
        model = Model(**sample_model_data)
        param = Parameter(**sample_parameter_data)
        test_db.add_all([site, model, param])
        await test_db.flush()

        # Create deviation
        deviation = Deviation(
            timestamp=datetime.now(timezone.utc),
            site_id=site.id,
            model_id=model.id,
            parameter_id=param.id,
            horizon=6,
            forecast_value=Decimal("25.50"),
            observed_value=Decimal("23.00"),
            deviation=Decimal("2.50"),
        )
        test_db.add(deviation)
        await test_db.flush()

        assert deviation.timestamp is not None
        assert deviation.forecast_value == Decimal("25.50")
        assert deviation.deviation == Decimal("2.50")

    @pytest.mark.asyncio
    async def test_deviation_composite_key(self, test_db, sample_site_data, sample_model_data, sample_parameter_data):
        """Test that deviation has composite primary key."""
        # Create reference data
        site = Site(**sample_site_data)
        model = Model(**sample_model_data)
        param = Parameter(**sample_parameter_data)
        test_db.add_all([site, model, param])
        await test_db.flush()

        ts = datetime.now(timezone.utc)

        # Create first deviation
        dev1 = Deviation(
            timestamp=ts,
            site_id=site.id,
            model_id=model.id,
            parameter_id=param.id,
            horizon=6,
            forecast_value=Decimal("25.00"),
            observed_value=Decimal("23.00"),
            deviation=Decimal("2.00"),
        )
        test_db.add(dev1)
        await test_db.flush()

        # Same timestamp but different horizon should work
        dev2 = Deviation(
            timestamp=ts,
            site_id=site.id,
            model_id=model.id,
            parameter_id=param.id,
            horizon=12,  # Different horizon
            forecast_value=Decimal("26.00"),
            observed_value=Decimal("24.00"),
            deviation=Decimal("2.00"),
        )
        test_db.add(dev2)
        await test_db.flush()

        # Both should exist
        result = await test_db.execute(select(Deviation))
        deviations = result.scalars().all()
        assert len(deviations) == 2

    @pytest.mark.asyncio
    async def test_deviation_repr(self, sample_site_data, sample_model_data, sample_parameter_data):
        """Test Deviation string representation."""
        ts = datetime.now(timezone.utc)
        deviation = Deviation(
            timestamp=ts,
            site_id=1,
            model_id=1,
            parameter_id=1,
            horizon=6,
            forecast_value=Decimal("25.00"),
            observed_value=Decimal("23.00"),
            deviation=Decimal("2.00"),
        )
        repr_str = repr(deviation)

        assert "Deviation" in repr_str
        assert "site=1" in repr_str
        assert "model=1" in repr_str
        assert "param=1" in repr_str


class TestModelRelationships:
    """Tests for model relationships."""

    @pytest.mark.asyncio
    async def test_deviation_foreign_keys(self, test_db, sample_site_data, sample_model_data, sample_parameter_data):
        """Test that Deviation has valid foreign keys to Site, Model, Parameter."""
        site = Site(**sample_site_data)
        model = Model(**sample_model_data)
        param = Parameter(**sample_parameter_data)
        test_db.add_all([site, model, param])
        await test_db.flush()

        # Create a single deviation
        dev = Deviation(
            timestamp=datetime.now(timezone.utc),
            site_id=site.id,
            model_id=model.id,
            parameter_id=param.id,
            horizon=6,
            forecast_value=Decimal("25.00"),
            observed_value=Decimal("23.00"),
            deviation=Decimal("2.00"),
        )
        test_db.add(dev)
        await test_db.flush()

        # Verify foreign key values are set correctly
        assert dev.site_id == site.id
        assert dev.model_id == model.id
        assert dev.parameter_id == param.id
