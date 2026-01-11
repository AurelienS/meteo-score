"""Seed data script for MétéoScore database.

This script inserts initial reference data into the database:
- 1 site: Passy Plaine Joux
- 2 models: AROME, Meteo-Parapente
- 3 parameters: Wind Speed, Wind Direction, Temperature

The script is idempotent - it can be run multiple times safely.
Existing records are skipped based on unique constraints.

Usage:
    # From backend directory with DATABASE_URL set:
    python -m db.seed

    # Or from Docker:
    docker-compose exec backend python -m db.seed
"""

import asyncio
import os
import sys
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add parent directory to path for imports when running as module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import Base, Model, Parameter, Site


def get_database_url() -> str:
    """Get database URL from environment."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")

    # Ensure async driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return url


# Seed data definitions
SITES = [
    {
        "name": "Passy Plaine Joux",
        "latitude": Decimal("45.916700"),
        "longitude": Decimal("6.700000"),
        "altitude": 1360,
    },
]

MODELS = [
    {
        "name": "AROME",
        "source": "Météo-France AROME operational model",
    },
    {
        "name": "Meteo-Parapente",
        "source": "meteo-parapente.com forecast service",
    },
]

PARAMETERS = [
    {
        "name": "Wind Speed",
        "unit": "km/h",
    },
    {
        "name": "Wind Direction",
        "unit": "degrees",
    },
    {
        "name": "Temperature",
        "unit": "°C",
    },
]


async def seed_sites(session: AsyncSession) -> int:
    """Insert seed sites if they don't exist.

    Args:
        session: Database session.

    Returns:
        Number of sites inserted.
    """
    inserted = 0
    for site_data in SITES:
        # Check if site already exists by name
        result = await session.execute(
            select(Site).where(Site.name == site_data["name"])
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            site = Site(**site_data)
            session.add(site)
            inserted += 1
            print(f"  + Inserted site: {site_data['name']}")
        else:
            print(f"  - Site already exists: {site_data['name']}")

    return inserted


async def seed_models(session: AsyncSession) -> int:
    """Insert seed models if they don't exist.

    Args:
        session: Database session.

    Returns:
        Number of models inserted.
    """
    inserted = 0
    for model_data in MODELS:
        # Check if model already exists by name (unique constraint)
        result = await session.execute(
            select(Model).where(Model.name == model_data["name"])
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            model = Model(**model_data)
            session.add(model)
            inserted += 1
            print(f"  + Inserted model: {model_data['name']}")
        else:
            print(f"  - Model already exists: {model_data['name']}")

    return inserted


async def seed_parameters(session: AsyncSession) -> int:
    """Insert seed parameters if they don't exist.

    Args:
        session: Database session.

    Returns:
        Number of parameters inserted.
    """
    inserted = 0
    for param_data in PARAMETERS:
        # Check if parameter already exists by name (unique constraint)
        result = await session.execute(
            select(Parameter).where(Parameter.name == param_data["name"])
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            param = Parameter(**param_data)
            session.add(param)
            inserted += 1
            print(f"  + Inserted parameter: {param_data['name']}")
        else:
            print(f"  - Parameter already exists: {param_data['name']}")

    return inserted


async def run_seed() -> None:
    """Run the seed script."""
    print("=" * 60)
    print("MétéoScore Database Seed Script")
    print("=" * 60)

    # Create engine and session
    engine = create_async_engine(get_database_url(), echo=False)
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        try:
            print("\nSeeding sites...")
            sites_inserted = await seed_sites(session)

            print("\nSeeding models...")
            models_inserted = await seed_models(session)

            print("\nSeeding parameters...")
            params_inserted = await seed_parameters(session)

            await session.commit()

            print("\n" + "=" * 60)
            print("Seed Summary:")
            print(f"  Sites inserted: {sites_inserted}/{len(SITES)}")
            print(f"  Models inserted: {models_inserted}/{len(MODELS)}")
            print(f"  Parameters inserted: {params_inserted}/{len(PARAMETERS)}")
            print("=" * 60)

            total_inserted = sites_inserted + models_inserted + params_inserted
            if total_inserted > 0:
                print("\nSeed data inserted successfully!")
            else:
                print("\nNo new data inserted (all records already exist).")

        except Exception as e:
            await session.rollback()
            print(f"\nError during seeding: {e}")
            raise

    await engine.dispose()


def main() -> None:
    """Entry point for the seed script."""
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
