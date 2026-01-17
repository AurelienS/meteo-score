"""Seed mock deviation data for development.

This script generates realistic mock deviation data for testing the frontend.
It creates deviation records for all combinations of sites, models, parameters,
and horizons over the past 60 days.

Usage:
    docker exec meteo-backend python db/seed_mock_data.py
"""

import asyncio
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import Deviation, Model, Parameter, Site


def get_database_url() -> str:
    """Get database URL from environment."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# Model characteristics for realistic data
MODEL_PROFILES = {
    "AROME": {
        "wind_speed_bias": -1.5,  # Tends to underestimate wind
        "wind_speed_mae": 3.0,
        "wind_direction_bias": 5.0,
        "wind_direction_mae": 15.0,
        "temperature_bias": 0.5,
        "temperature_mae": 1.5,
    },
    "Meteo-Parapente": {
        "wind_speed_bias": 0.8,  # Tends to slightly overestimate
        "wind_speed_mae": 2.5,
        "wind_direction_bias": -3.0,
        "wind_direction_mae": 12.0,
        "temperature_bias": -0.3,
        "temperature_mae": 1.2,
    },
}

# Horizons to generate data for
HORIZONS = [6, 12, 24, 48]


def generate_deviation(
    model_name: str,
    param_name: str,
    horizon: int,
) -> tuple[Decimal, Decimal, Decimal]:
    """Generate realistic forecast, observed, and deviation values.

    Args:
        model_name: Name of the weather model.
        param_name: Name of the weather parameter.
        horizon: Forecast horizon in hours.

    Returns:
        Tuple of (forecast_value, observed_value, deviation).
    """
    profile = MODEL_PROFILES.get(model_name, MODEL_PROFILES["AROME"])

    # Normalize parameter name for lookup
    param_key = param_name.lower().replace(" ", "_")

    # Get base characteristics
    if "wind_speed" in param_key or param_key == "wind speed":
        base_value = random.uniform(5, 35)  # km/h
        bias = profile["wind_speed_bias"]
        mae = profile["wind_speed_mae"]
    elif "wind_direction" in param_key or param_key == "wind direction":
        base_value = random.uniform(0, 360)  # degrees
        bias = profile["wind_direction_bias"]
        mae = profile["wind_direction_mae"]
    else:  # temperature
        base_value = random.uniform(-5, 30)  # °C
        bias = profile["temperature_bias"]
        mae = profile["temperature_mae"]

    # Increase error with horizon (forecasts get worse over time)
    horizon_factor = 1 + (horizon / 48) * 0.5

    # Generate deviation with some randomness
    deviation = bias + random.gauss(0, mae * horizon_factor * 0.5)
    deviation = Decimal(str(round(deviation, 2)))

    observed_value = Decimal(str(round(base_value, 2)))
    forecast_value = observed_value + deviation

    return forecast_value, observed_value, deviation


async def seed_deviations(session: AsyncSession, days: int = 60) -> int:
    """Generate mock deviation data.

    Args:
        session: Database session.
        days: Number of days of historical data to generate.

    Returns:
        Number of deviations inserted.
    """
    # Get all sites, models, parameters
    sites = (await session.execute(select(Site))).scalars().all()
    models = (await session.execute(select(Model))).scalars().all()
    parameters = (await session.execute(select(Parameter))).scalars().all()

    if not sites or not models or not parameters:
        print("Error: Missing base data. Run seed.py first.")
        return 0

    print(f"Found {len(sites)} sites, {len(models)} models, {len(parameters)} parameters")

    now = datetime.now(timezone.utc)
    inserted = 0
    batch = []
    batch_size = 500

    # Generate data points
    for day_offset in range(days, 0, -1):
        # 4 data points per day (every 6 hours)
        for hour in [0, 6, 12, 18]:
            timestamp = (now - timedelta(days=day_offset)).replace(
                hour=hour, minute=0, second=0, microsecond=0
            )

            for site in sites:
                for model in models:
                    for param in parameters:
                        for horizon in HORIZONS:
                            forecast_val, observed_val, deviation = generate_deviation(
                                model.name, param.name, horizon
                            )

                            batch.append(Deviation(
                                timestamp=timestamp,
                                site_id=site.id,
                                model_id=model.id,
                                parameter_id=param.id,
                                horizon=horizon,
                                forecast_value=forecast_val,
                                observed_value=observed_val,
                                deviation=deviation,
                            ))

                            if len(batch) >= batch_size:
                                session.add_all(batch)
                                await session.flush()
                                inserted += len(batch)
                                print(f"  Inserted {inserted} deviations...")
                                batch = []

    # Insert remaining
    if batch:
        session.add_all(batch)
        await session.flush()
        inserted += len(batch)

    return inserted


async def run_seed() -> None:
    """Run the mock data seed script."""
    print("=" * 60)
    print("MétéoScore Mock Data Seed Script")
    print("=" * 60)

    engine = create_async_engine(get_database_url(), echo=False)
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        try:
            print("\nGenerating mock deviation data (60 days)...")
            count = await seed_deviations(session)

            await session.commit()

            print("\n" + "=" * 60)
            print(f"Mock Data Seed Complete!")
            print(f"  Deviations inserted: {count}")
            print("=" * 60)

        except Exception as e:
            await session.rollback()
            print(f"\nError during seeding: {e}")
            raise

    await engine.dispose()


def main() -> None:
    """Entry point."""
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
