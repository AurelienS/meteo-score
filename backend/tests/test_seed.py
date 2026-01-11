"""Tests for seed data script.

Tests verify:
- Seed data is inserted correctly
- Idempotent behavior (can run multiple times)
- Correct values for Passy Plaine Joux site
- Correct values for AROME and Meteo-Parapente models
- Correct values for wind speed, direction, temperature parameters
"""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from core.models import Model, Parameter, Site
from db.seed import (
    MODELS,
    PARAMETERS,
    SITES,
    seed_models,
    seed_parameters,
    seed_sites,
)


class TestSeedData:
    """Tests for seed data constants."""

    def test_sites_contains_passy(self):
        """Test that SITES contains Passy Plaine Joux."""
        assert len(SITES) >= 1
        passy = SITES[0]
        assert passy["name"] == "Passy Plaine Joux"
        assert passy["latitude"] == Decimal("45.916700")
        assert passy["longitude"] == Decimal("6.700000")
        assert passy["altitude"] == 1360

    def test_models_contains_arome(self):
        """Test that MODELS contains AROME."""
        model_names = [m["name"] for m in MODELS]
        assert "AROME" in model_names

    def test_models_contains_meteo_parapente(self):
        """Test that MODELS contains Meteo-Parapente."""
        model_names = [m["name"] for m in MODELS]
        assert "Meteo-Parapente" in model_names

    def test_parameters_contains_wind_speed(self):
        """Test that PARAMETERS contains Wind Speed."""
        param_names = [p["name"] for p in PARAMETERS]
        assert "Wind Speed" in param_names

        wind_speed = next(p for p in PARAMETERS if p["name"] == "Wind Speed")
        assert wind_speed["unit"] == "km/h"

    def test_parameters_contains_wind_direction(self):
        """Test that PARAMETERS contains Wind Direction."""
        param_names = [p["name"] for p in PARAMETERS]
        assert "Wind Direction" in param_names

        wind_dir = next(p for p in PARAMETERS if p["name"] == "Wind Direction")
        assert wind_dir["unit"] == "degrees"

    def test_parameters_contains_temperature(self):
        """Test that PARAMETERS contains Temperature."""
        param_names = [p["name"] for p in PARAMETERS]
        assert "Temperature" in param_names

        temp = next(p for p in PARAMETERS if p["name"] == "Temperature")
        assert temp["unit"] == "°C"


class TestSeedFunctions:
    """Tests for seed functions."""

    @pytest.mark.asyncio
    async def test_seed_sites_inserts_data(self, test_db):
        """Test that seed_sites inserts site records."""
        count = await seed_sites(test_db)
        await test_db.flush()

        assert count == len(SITES)

        # Verify site exists
        result = await test_db.execute(
            select(Site).where(Site.name == "Passy Plaine Joux")
        )
        site = result.scalar_one()
        assert site.altitude == 1360

    @pytest.mark.asyncio
    async def test_seed_sites_is_idempotent(self, test_db):
        """Test that seed_sites can be run multiple times."""
        # First run
        count1 = await seed_sites(test_db)
        await test_db.flush()

        # Second run
        count2 = await seed_sites(test_db)
        await test_db.flush()

        assert count1 == len(SITES)
        assert count2 == 0  # No new inserts

        # Should still have only 1 site
        result = await test_db.execute(select(func.count(Site.id)))
        total = result.scalar()
        assert total == len(SITES)

    @pytest.mark.asyncio
    async def test_seed_models_inserts_data(self, test_db):
        """Test that seed_models inserts model records."""
        count = await seed_models(test_db)
        await test_db.flush()

        assert count == len(MODELS)

        # Verify models exist
        result = await test_db.execute(select(Model))
        models = result.scalars().all()
        model_names = [m.name for m in models]

        assert "AROME" in model_names
        assert "Meteo-Parapente" in model_names

    @pytest.mark.asyncio
    async def test_seed_models_is_idempotent(self, test_db):
        """Test that seed_models can be run multiple times."""
        count1 = await seed_models(test_db)
        await test_db.flush()

        count2 = await seed_models(test_db)
        await test_db.flush()

        assert count1 == len(MODELS)
        assert count2 == 0

    @pytest.mark.asyncio
    async def test_seed_parameters_inserts_data(self, test_db):
        """Test that seed_parameters inserts parameter records."""
        count = await seed_parameters(test_db)
        await test_db.flush()

        assert count == len(PARAMETERS)

        # Verify parameters exist
        result = await test_db.execute(select(Parameter))
        params = result.scalars().all()
        param_names = [p.name for p in params]

        assert "Wind Speed" in param_names
        assert "Wind Direction" in param_names
        assert "Temperature" in param_names

    @pytest.mark.asyncio
    async def test_seed_parameters_is_idempotent(self, test_db):
        """Test that seed_parameters can be run multiple times."""
        count1 = await seed_parameters(test_db)
        await test_db.flush()

        count2 = await seed_parameters(test_db)
        await test_db.flush()

        assert count1 == len(PARAMETERS)
        assert count2 == 0
