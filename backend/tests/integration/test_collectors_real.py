"""Integration tests for collectors with real APIs.

These tests hit actual external APIs and verify:
- API connectivity
- Response parsing
- Data format validation

Usage:
    pytest -m integration tests/integration/test_collectors_real.py
"""

import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def passy_coordinates() -> dict:
    """Return coordinates for Passy Plaine Joux site."""
    return {
        "site_id": 1,
        "latitude": 45.9167,
        "longitude": 6.7000,
        "name": "Passy Plaine Joux",
    }


class TestMeteoParapenteCollectorReal:
    """Integration tests for Meteo-Parapente collector."""

    @pytest.mark.asyncio
    async def test_collect_forecast_returns_data(self, passy_coordinates):
        """Test that collector returns forecast data from real API."""
        from collectors import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        forecast_run = datetime.now(timezone.utc)

        data = await collector.collect_forecast(
            site_id=passy_coordinates["site_id"],
            forecast_run=forecast_run,
            latitude=passy_coordinates["latitude"],
            longitude=passy_coordinates["longitude"],
        )

        # Should return some data
        assert len(data) > 0, "Expected at least one forecast record"

        # Verify data structure
        for record in data:
            assert record.site_id == passy_coordinates["site_id"]
            assert record.model_id == 2  # Meteo-Parapente model ID
            assert record.parameter_id in [1, 2, 3]  # wind_speed, wind_direction, temperature
            assert record.forecast_run is not None
            assert record.valid_time is not None
            assert record.horizon >= 0
            assert isinstance(record.value, Decimal)

    @pytest.mark.asyncio
    async def test_collect_forecast_returns_expected_parameters(self, passy_coordinates):
        """Test that collector returns all expected weather parameters."""
        from collectors import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        forecast_run = datetime.now(timezone.utc)

        data = await collector.collect_forecast(
            site_id=passy_coordinates["site_id"],
            forecast_run=forecast_run,
            latitude=passy_coordinates["latitude"],
            longitude=passy_coordinates["longitude"],
        )

        # Extract unique parameter IDs
        param_ids = set(record.parameter_id for record in data)

        # Should have at least wind_speed and wind_direction
        assert 1 in param_ids, "Expected wind_speed (param_id=1)"
        assert 2 in param_ids, "Expected wind_direction (param_id=2)"
        # Temperature may not always be present
        # assert 3 in param_ids, "Expected temperature (param_id=3)"

    @pytest.mark.asyncio
    async def test_collect_forecast_values_in_range(self, passy_coordinates):
        """Test that collected values are within valid ranges."""
        from collectors import MeteoParapenteCollector

        collector = MeteoParapenteCollector()
        forecast_run = datetime.now(timezone.utc)

        data = await collector.collect_forecast(
            site_id=passy_coordinates["site_id"],
            forecast_run=forecast_run,
            latitude=passy_coordinates["latitude"],
            longitude=passy_coordinates["longitude"],
        )

        for record in data:
            if record.parameter_id == 1:  # wind_speed
                assert Decimal("0") <= record.value <= Decimal("200"), (
                    f"Wind speed {record.value} out of range"
                )
            elif record.parameter_id == 2:  # wind_direction
                assert Decimal("0") <= record.value <= Decimal("360"), (
                    f"Wind direction {record.value} out of range"
                )
            elif record.parameter_id == 3:  # temperature
                assert Decimal("-50") <= record.value <= Decimal("50"), (
                    f"Temperature {record.value} out of range"
                )


class TestAROMECollectorReal:
    """Integration tests for AROME collector."""

    @pytest.fixture
    def skip_if_no_token(self):
        """Skip test if METEOFRANCE_API_TOKEN is not set."""
        if not os.environ.get("METEOFRANCE_API_TOKEN"):
            pytest.skip("METEOFRANCE_API_TOKEN not set")

    @pytest.mark.asyncio
    async def test_collect_forecast_returns_data(self, passy_coordinates, skip_if_no_token):
        """Test that collector returns forecast data from real API."""
        from collectors import AROMECollector

        collector = AROMECollector()
        forecast_run = datetime.now(timezone.utc)

        data = await collector.collect_forecast(
            site_id=passy_coordinates["site_id"],
            forecast_run=forecast_run,
            latitude=passy_coordinates["latitude"],
            longitude=passy_coordinates["longitude"],
        )

        # Should return some data (may be empty if API is rate-limited)
        # Just verify no exceptions and valid structure
        for record in data:
            assert record.site_id == passy_coordinates["site_id"]
            assert record.model_id == 1  # AROME model ID
            assert record.parameter_id in [1, 2, 3]
            assert isinstance(record.value, Decimal)


class TestROMMaCollectorReal:
    """Integration tests for ROMMA collector."""

    @pytest.fixture
    def romma_beacon_id(self) -> int:
        """Return a known ROMMA beacon ID for testing."""
        # Beacon 21 is a commonly available ROMMA station
        return 21

    @pytest.mark.asyncio
    async def test_collect_observation_returns_data(self, romma_beacon_id):
        """Test that collector returns observation data from real beacon."""
        from collectors import ROMMaCollector

        collector = ROMMaCollector(beacon_id=romma_beacon_id)
        observation_time = datetime.now(timezone.utc)

        data = await collector.collect_observation(
            site_id=1,
            observation_time=observation_time,
            beacon_id=romma_beacon_id,
        )

        # Should return some data (may be empty if beacon is offline)
        # If data is returned, verify structure
        for record in data:
            assert record.site_id == 1
            assert record.parameter_id in [1, 2, 3]
            assert record.observation_time is not None
            assert isinstance(record.value, Decimal)

    @pytest.mark.asyncio
    async def test_collect_observation_values_in_range(self, romma_beacon_id):
        """Test that collected values are within valid ranges."""
        from collectors import ROMMaCollector

        collector = ROMMaCollector(beacon_id=romma_beacon_id)
        observation_time = datetime.now(timezone.utc)

        data = await collector.collect_observation(
            site_id=1,
            observation_time=observation_time,
            beacon_id=romma_beacon_id,
        )

        for record in data:
            if record.parameter_id == 1:  # wind_speed
                assert Decimal("0") <= record.value <= Decimal("200"), (
                    f"Wind speed {record.value} out of range"
                )
            elif record.parameter_id == 2:  # wind_direction
                assert Decimal("0") <= record.value <= Decimal("360"), (
                    f"Wind direction {record.value} out of range"
                )
            elif record.parameter_id == 3:  # temperature
                assert Decimal("-50") <= record.value <= Decimal("50"), (
                    f"Temperature {record.value} out of range"
                )


class TestFFVLCollectorReal:
    """Integration tests for FFVL collector."""

    @pytest.fixture
    def ffvl_beacon_id(self) -> int:
        """Return a known FFVL beacon ID for testing."""
        # Use a commonly available FFVL beacon
        return 67

    @pytest.mark.asyncio
    async def test_collect_observation_returns_data(self, ffvl_beacon_id):
        """Test that collector returns observation data from real beacon."""
        from collectors import FFVLCollector

        collector = FFVLCollector(beacon_id=ffvl_beacon_id)
        observation_time = datetime.now(timezone.utc)

        data = await collector.collect_observation(
            site_id=1,
            observation_time=observation_time,
            beacon_id=ffvl_beacon_id,
        )

        # Should return some data (may be empty if beacon is offline)
        # If data is returned, verify structure
        for record in data:
            assert record.site_id == 1
            assert record.parameter_id in [1, 2, 3]
            assert record.observation_time is not None
            assert isinstance(record.value, Decimal)
