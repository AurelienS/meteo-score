"""Smoke test module for data collection pipeline validation.

This module provides quick end-to-end validation of the entire data collection
pipeline by testing each collector with real APIs.

Usage:
    # From CLI (recommended)
    python -m cli smoke-test

    # Programmatic usage
    from tests.smoke_test import run_smoke_test
    result = await run_smoke_test()

Features:
    - Tests each collector individually with real APIs
    - Verifies data is actually persisted to database
    - Reports success/failure with clear output
    - Shows collected record counts
    - Tests both forecasts and observations
    - Validates configuration (beacon IDs, API tokens)
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TestStatus(Enum):
    """Status of a smoke test."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CollectorTestResult:
    """Result of testing a single collector."""

    collector_name: str
    status: TestStatus = TestStatus.PENDING
    records_collected: int = 0
    records_persisted: int = 0
    steps: list[tuple[bool, str]] = field(default_factory=list)
    error: str | None = None
    duration_seconds: float = 0.0

    def add_step(self, success: bool, message: str) -> None:
        """Add a step result."""
        self.steps.append((success, message))

    @property
    def success(self) -> bool:
        """Check if all steps succeeded."""
        return self.status == TestStatus.SUCCESS


@dataclass
class SmokeTestResult:
    """Overall smoke test result."""

    collectors: list[CollectorTestResult] = field(default_factory=list)
    total_forecasts_collected: int = 0
    total_forecasts_persisted: int = 0
    total_observations_collected: int = 0
    total_observations_persisted: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    status: str = "pending"

    @property
    def duration_seconds(self) -> float:
        """Total duration in seconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()

    @property
    def success_count(self) -> int:
        """Number of successful collectors."""
        return sum(1 for c in self.collectors if c.success)

    @property
    def failed_count(self) -> int:
        """Number of failed collectors."""
        return sum(1 for c in self.collectors if c.status == TestStatus.FAILED)


async def test_meteo_parapente_collector(
    site_config: dict[str, Any],
    dry_run: bool = False,
    verbose: bool = False,
) -> CollectorTestResult:
    """Test Meteo-Parapente forecast collector.

    Args:
        site_config: Site configuration with coordinates.
        dry_run: If True, don't persist to database.
        verbose: If True, log detailed information.

    Returns:
        CollectorTestResult with test outcome.
    """
    from collectors import MeteoParapenteCollector
    from services.storage_service import save_forecasts

    result = CollectorTestResult(collector_name="Meteo-Parapente")
    start_time = datetime.now(timezone.utc)

    try:
        result.status = TestStatus.RUNNING

        # Initialize collector
        collector = MeteoParapenteCollector()
        result.add_step(True, "Initialized collector")

        # Collect forecasts
        forecast_run = datetime.now(timezone.utc)
        data = await collector.collect_forecast(
            site_id=site_config["site_id"],
            forecast_run=forecast_run,
            latitude=site_config["latitude"],
            longitude=site_config["longitude"],
        )

        if not data:
            result.add_step(False, "No forecast data returned")
            result.status = TestStatus.FAILED
            result.error = "API returned no data"
            return result

        result.add_step(True, "Connected to API")
        result.records_collected = len(data)
        result.add_step(
            True,
            f"Collected {len(data)} forecast records for site \"{site_config['name']}\"",
        )

        # Persist to database
        if not dry_run:
            _, persisted = await save_forecasts(data, "Meteo-Parapente")
            result.records_persisted = persisted
            result.add_step(True, f"Persisted {persisted} records to database")
        else:
            result.add_step(True, "Skipped persistence (dry run)")

        result.status = TestStatus.SUCCESS

    except Exception as e:
        result.status = TestStatus.FAILED
        result.error = str(e)
        result.add_step(False, f"Failed: {e}")

    result.duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
    return result


async def test_arome_collector(
    site_config: dict[str, Any],
    dry_run: bool = False,
    verbose: bool = False,
) -> CollectorTestResult:
    """Test AROME forecast collector.

    Args:
        site_config: Site configuration with coordinates.
        dry_run: If True, don't persist to database.
        verbose: If True, log detailed information.

    Returns:
        CollectorTestResult with test outcome.
    """
    from collectors import AROMECollector
    from services.storage_service import save_forecasts

    result = CollectorTestResult(collector_name="AROME")
    start_time = datetime.now(timezone.utc)

    try:
        result.status = TestStatus.RUNNING

        # Check API token
        api_token = os.environ.get("METEOFRANCE_API_TOKEN")
        if not api_token:
            result.add_step(False, "METEOFRANCE_API_TOKEN not set")
            result.status = TestStatus.SKIPPED
            result.error = "Missing METEOFRANCE_API_TOKEN environment variable"
            return result

        result.add_step(True, "API token configured")

        # Initialize collector
        collector = AROMECollector()
        result.add_step(True, "Initialized collector")

        # Collect forecasts
        forecast_run = datetime.now(timezone.utc)
        data = await collector.collect_forecast(
            site_id=site_config["site_id"],
            forecast_run=forecast_run,
            latitude=site_config["latitude"],
            longitude=site_config["longitude"],
        )

        if not data:
            result.add_step(False, "No forecast data returned (API may be rate-limited)")
            result.status = TestStatus.FAILED
            result.error = "API returned no data"
            return result

        result.add_step(True, "Downloaded GRIB2 data")
        result.records_collected = len(data)
        result.add_step(True, f"Collected {len(data)} forecast records")

        # Persist to database
        if not dry_run:
            _, persisted = await save_forecasts(data, "AROME")
            result.records_persisted = persisted
            result.add_step(True, f"Persisted {persisted} records to database")
        else:
            result.add_step(True, "Skipped persistence (dry run)")

        result.status = TestStatus.SUCCESS

    except Exception as e:
        result.status = TestStatus.FAILED
        result.error = str(e)
        result.add_step(False, f"Failed: {e}")

    result.duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
    return result


async def test_romma_collector(
    site_config: dict[str, Any],
    dry_run: bool = False,
    verbose: bool = False,
) -> CollectorTestResult:
    """Test ROMMA observation collector.

    Args:
        site_config: Site configuration with beacon IDs.
        dry_run: If True, don't persist to database.
        verbose: If True, log detailed information.

    Returns:
        CollectorTestResult with test outcome.
    """
    from collectors import ROMMaCollector
    from services.storage_service import save_observations

    result = CollectorTestResult(collector_name="ROMMA")
    start_time = datetime.now(timezone.utc)

    try:
        result.status = TestStatus.RUNNING

        # Check beacon ID configuration
        beacon_id = site_config.get("romma_beacon_id")
        backup_beacon_id = site_config.get("romma_beacon_id_backup")

        if not beacon_id and not backup_beacon_id:
            result.add_step(False, "No ROMMA beacon ID configured for site")
            result.status = TestStatus.SKIPPED
            result.error = "No ROMMA beacon ID configured"
            return result

        target_beacon = beacon_id or backup_beacon_id
        result.add_step(True, f"Using beacon ID: {target_beacon}")

        # Initialize collector
        collector = ROMMaCollector(beacon_id=target_beacon)
        result.add_step(True, "Initialized collector")

        # Collect observations
        observation_time = datetime.now(timezone.utc)
        data = await collector.collect_observation(
            site_id=site_config["site_id"],
            observation_time=observation_time,
            beacon_id=target_beacon,
        )

        if not data:
            result.add_step(False, "No observation data returned (page may be down)")
            result.status = TestStatus.FAILED
            result.error = "Beacon returned no data"
            return result

        result.add_step(True, "Scraped weather station page")
        result.records_collected = len(data)

        # List the parameters collected
        param_names = []
        for obs in data:
            if obs.parameter_id == 1:
                param_names.append("wind_speed")
            elif obs.parameter_id == 2:
                param_names.append("wind_direction")
            elif obs.parameter_id == 3:
                param_names.append("temperature")

        result.add_step(
            True,
            f"Collected {len(data)} observation records ({', '.join(param_names)})",
        )

        # Persist to database
        if not dry_run:
            _, persisted = await save_observations(data, "ROMMA")
            result.records_persisted = persisted
            result.add_step(True, f"Persisted {persisted} records to database")
        else:
            result.add_step(True, "Skipped persistence (dry run)")

        result.status = TestStatus.SUCCESS

    except Exception as e:
        result.status = TestStatus.FAILED
        result.error = str(e)
        result.add_step(False, f"Failed: {e}")

    result.duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
    return result


async def test_ffvl_collector(
    site_config: dict[str, Any],
    dry_run: bool = False,
    verbose: bool = False,
) -> CollectorTestResult:
    """Test FFVL observation collector.

    Args:
        site_config: Site configuration with beacon IDs.
        dry_run: If True, don't persist to database.
        verbose: If True, log detailed information.

    Returns:
        CollectorTestResult with test outcome.
    """
    from collectors import FFVLCollector
    from services.storage_service import save_observations

    result = CollectorTestResult(collector_name="FFVL")
    start_time = datetime.now(timezone.utc)

    try:
        result.status = TestStatus.RUNNING

        # Check beacon ID configuration
        beacon_id = site_config.get("ffvl_beacon_id")
        backup_beacon_id = site_config.get("ffvl_beacon_id_backup")

        if not beacon_id and not backup_beacon_id:
            result.add_step(False, "No FFVL beacon ID configured for site")
            result.status = TestStatus.SKIPPED
            result.error = "No FFVL beacon ID configured"
            return result

        target_beacon = beacon_id or backup_beacon_id
        result.add_step(True, f"Using beacon ID: {target_beacon}")

        # Initialize collector
        collector = FFVLCollector(beacon_id=target_beacon)
        result.add_step(True, "Initialized collector")

        # Collect observations
        observation_time = datetime.now(timezone.utc)
        data = await collector.collect_observation(
            site_id=site_config["site_id"],
            observation_time=observation_time,
            beacon_id=target_beacon,
        )

        if not data:
            result.add_step(False, "No observation data returned (beacon may be down)")
            result.status = TestStatus.FAILED
            result.error = "Beacon returned no data"
            return result

        result.add_step(True, "Scraped weather station page")
        result.records_collected = len(data)

        # List the parameters collected
        param_names = []
        for obs in data:
            if obs.parameter_id == 1:
                param_names.append("wind_speed")
            elif obs.parameter_id == 2:
                param_names.append("wind_direction")
            elif obs.parameter_id == 3:
                param_names.append("temperature")

        result.add_step(
            True,
            f"Collected {len(data)} observation records ({', '.join(param_names)})",
        )

        # Persist to database
        if not dry_run:
            _, persisted = await save_observations(data, "FFVL")
            result.records_persisted = persisted
            result.add_step(True, f"Persisted {persisted} records to database")
        else:
            result.add_step(True, "Skipped persistence (dry run)")

        result.status = TestStatus.SUCCESS

    except Exception as e:
        result.status = TestStatus.FAILED
        result.error = str(e)
        result.add_step(False, f"Failed: {e}")

    result.duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
    return result


async def get_site_config_for_test(site_name: str | None = None) -> dict[str, Any] | None:
    """Get site configuration for testing.

    Args:
        site_name: Optional site name filter.

    Returns:
        Site configuration dict or None if not found.
    """
    from scheduler.jobs import get_site_configs_async

    sites = await get_site_configs_async()

    if not sites:
        return None

    if site_name:
        for site in sites:
            if site["name"].lower() == site_name.lower():
                return site
        return None

    # Return first site by default
    return sites[0]


async def run_smoke_test(
    dry_run: bool = False,
    verbose: bool = False,
    site_name: str | None = None,
) -> SmokeTestResult:
    """Run full smoke test of data collection pipeline.

    Args:
        dry_run: If True, don't persist to database.
        verbose: If True, show detailed output.
        site_name: Optional site name to test (tests first site if not specified).

    Returns:
        SmokeTestResult with all test outcomes.
    """
    result = SmokeTestResult()
    result.start_time = datetime.now(timezone.utc)

    # Get site configuration
    site_config = await get_site_config_for_test(site_name)

    if not site_config:
        # No sites configured, can't run tests
        result.status = "failed"
        result.end_time = datetime.now(timezone.utc)
        return result

    # Test collectors
    collectors_to_test = [
        ("Meteo-Parapente", test_meteo_parapente_collector, True),
        ("AROME", test_arome_collector, True),
        ("ROMMA", test_romma_collector, False),
        ("FFVL", test_ffvl_collector, False),
    ]

    for name, test_func, is_forecast in collectors_to_test:
        collector_result = await test_func(
            site_config=site_config,
            dry_run=dry_run,
            verbose=verbose,
        )
        result.collectors.append(collector_result)

        # Update totals
        if is_forecast:
            result.total_forecasts_collected += collector_result.records_collected
            result.total_forecasts_persisted += collector_result.records_persisted
        else:
            result.total_observations_collected += collector_result.records_collected
            result.total_observations_persisted += collector_result.records_persisted

    # Determine overall status
    result.end_time = datetime.now(timezone.utc)

    if result.failed_count == 0:
        result.status = "success"
    elif result.success_count > 0:
        result.status = "partial"
    else:
        result.status = "failed"

    return result


def format_smoke_test_output(
    result: SmokeTestResult,
    site_name: str,
    verbose: bool = False,
) -> str:
    """Format smoke test result for CLI output.

    Args:
        result: Smoke test result.
        site_name: Name of the tested site.
        verbose: If True, show detailed output.

    Returns:
        Formatted string output.
    """
    lines = []
    lines.append("")
    lines.append("=== Smoke Test: Data Collection Pipeline ===")
    lines.append(f"Site: {site_name}")
    lines.append("")

    for i, collector in enumerate(result.collectors, 1):
        lines.append(f"[{i}/{len(result.collectors)}] Testing {collector.collector_name} collector...")

        for success, message in collector.steps:
            icon = "+" if success else "x"
            lines.append(f"  {icon} {message}")

        if collector.status == TestStatus.SKIPPED:
            lines.append(f"  - SKIPPED: {collector.error}")

        lines.append("")

    # Summary
    lines.append("=== Summary ===")
    lines.append(
        f"Forecasts: {result.total_forecasts_collected} collected, "
        f"{result.total_forecasts_persisted} persisted"
    )
    lines.append(
        f"Observations: {result.total_observations_collected} collected, "
        f"{result.total_observations_persisted} persisted"
    )

    status_msg = result.status.upper()
    if result.failed_count > 0:
        status_msg += f" ({result.failed_count} collector(s) failed)"

    lines.append(f"Status: {status_msg}")
    lines.append(f"Duration: {result.duration_seconds:.2f}s")
    lines.append("")

    return "\n".join(lines)
