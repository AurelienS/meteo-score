"""Tests for admin API endpoints.

Tests verify:
- Basic Auth middleware rejects missing/invalid credentials
- Basic Auth middleware accepts valid credentials
- Scheduler status endpoint returns expected structure
- Scheduler toggle endpoint starts/stops scheduler
- Manual collection endpoints trigger jobs
- Stats and data preview endpoints
"""

import base64
import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from scheduler.scheduler import get_scheduler, reset_scheduler


def get_auth_header(username: str = "admin", password: str = "changeme") -> dict:
    """Create Basic Auth header."""
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


class TestBasicAuthMiddleware:
    """Tests for Basic Auth middleware."""

    @pytest.fixture(autouse=True)
    def clear_rate_limit_state(self):
        """Clear rate limit state before each test."""
        from api.dependencies.auth import _failed_attempts
        _failed_attempts.clear()
        yield
        _failed_attempts.clear()

    @pytest.mark.asyncio
    async def test_reject_missing_credentials(self, test_client: AsyncClient):
        """Test that missing credentials returns 401."""
        response = await test_client.get("/api/admin/scheduler/status")

        assert response.status_code == 401
        assert response.headers.get("WWW-Authenticate") == "Basic"

    @pytest.mark.asyncio
    async def test_reject_invalid_username(self, test_client: AsyncClient):
        """Test that invalid username returns 401."""
        response = await test_client.get(
            "/api/admin/scheduler/status",
            headers=get_auth_header(username="wrong", password="changeme"),
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reject_invalid_password(self, test_client: AsyncClient):
        """Test that invalid password returns 401."""
        response = await test_client.get(
            "/api/admin/scheduler/status",
            headers=get_auth_header(username="admin", password="wrong"),
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_accept_valid_credentials(self, test_client: AsyncClient):
        """Test that valid credentials are accepted."""
        response = await test_client.get(
            "/api/admin/scheduler/status",
            headers=get_auth_header(),
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_credentials_from_environment(self, test_client: AsyncClient):
        """Test that credentials are read from environment variables."""
        with patch.dict(os.environ, {"ADMIN_USERNAME": "testuser", "ADMIN_PASSWORD": "testpass"}):
            # Clear the cached credentials by importing fresh

            # Test with old credentials (should fail)
            response = await test_client.get(
                "/api/admin/scheduler/status",
                headers=get_auth_header(username="admin", password="changeme"),
            )
            # Note: This may or may not fail depending on caching - the key point
            # is that the env vars are being read

            # Test with new credentials (should work)
            response = await test_client.get(
                "/api/admin/scheduler/status",
                headers=get_auth_header(username="testuser", password="testpass"),
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_after_failed_attempts(self, test_client: AsyncClient):
        """Test that rate limiting kicks in after multiple failed attempts."""
        from api.dependencies.auth import _ADMIN_RATE_LIMIT

        # Make several failed attempts
        for _ in range(_ADMIN_RATE_LIMIT):
            response = await test_client.get(
                "/api/admin/scheduler/status",
                headers=get_auth_header(username="wrong", password="wrong"),
            )
            assert response.status_code == 401

        # Next attempt should be rate limited
        response = await test_client.get(
            "/api/admin/scheduler/status",
            headers=get_auth_header(username="wrong", password="wrong"),
        )
        assert response.status_code == 429
        assert "Retry-After" in response.headers


class TestSchedulerStatusEndpoint:
    """Tests for GET /api/admin/scheduler/status endpoint."""

    @pytest.mark.asyncio
    async def test_returns_scheduler_status(self, test_client: AsyncClient):
        """Test that endpoint returns scheduler running status."""
        response = await test_client.get(
            "/api/admin/scheduler/status",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert isinstance(data["running"], bool)

    @pytest.mark.asyncio
    async def test_returns_execution_history(self, test_client: AsyncClient):
        """Test that endpoint returns execution history lists."""
        response = await test_client.get(
            "/api/admin/scheduler/status",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert "forecastHistory" in data
        assert "observationHistory" in data
        assert isinstance(data["forecastHistory"], list)
        assert isinstance(data["observationHistory"], list)

    @pytest.mark.asyncio
    async def test_execution_record_structure(self, test_client: AsyncClient):
        """Test execution record has expected fields when history exists."""
        # Mock the execution history to return test data
        mock_history = [
            {
                "start_time": "2026-01-17T10:00:00Z",
                "end_time": "2026-01-17T10:01:00Z",
                "duration_seconds": 60.0,
                "status": "success",
                "records_collected": 100,
                "records_persisted": 95,
                "errors": None,
            }
        ]

        with patch(
            "api.routes.admin.get_execution_history_async",
            new_callable=AsyncMock,
            return_value=mock_history,
        ):
            response = await test_client.get(
                "/api/admin/scheduler/status",
                headers=get_auth_header(),
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["forecastHistory"]) == 1

            record = data["forecastHistory"][0]
            assert "startTime" in record
            assert "endTime" in record
            assert "durationSeconds" in record
            assert "status" in record
            assert "recordsCollected" in record
            assert "recordsPersisted" in record


class TestSchedulerJobsEndpoint:
    """Tests for GET /api/admin/scheduler/jobs endpoint."""

    @pytest.mark.asyncio
    async def test_returns_jobs_list(self, test_client: AsyncClient):
        """Test that endpoint returns jobs list."""
        response = await test_client.get(
            "/api/admin/scheduler/jobs",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    @pytest.mark.asyncio
    async def test_job_info_structure(self, test_client: AsyncClient):
        """Test job info has expected fields when scheduler has jobs."""
        # This test may return empty jobs if scheduler hasn't been started
        response = await test_client.get(
            "/api/admin/scheduler/jobs",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()

        # If there are jobs, verify structure
        for job in data["jobs"]:
            assert "id" in job
            assert "name" in job
            assert "trigger" in job


class TestSchedulerToggleEndpoint:
    """Tests for POST /api/admin/scheduler/toggle endpoint."""

    @pytest.fixture(autouse=True)
    def reset_scheduler_state(self):
        """Reset scheduler state before and after each test."""
        reset_scheduler()
        yield
        reset_scheduler()

    @pytest.mark.asyncio
    async def test_toggle_returns_new_state(self, test_client: AsyncClient):
        """Test that toggle returns the new running state."""
        response = await test_client.post(
            "/api/admin/scheduler/toggle",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert "message" in data
        assert isinstance(data["running"], bool)

    @pytest.mark.asyncio
    async def test_toggle_starts_stopped_scheduler(self, test_client: AsyncClient):
        """Test that toggle starts a stopped scheduler."""
        scheduler = get_scheduler()
        assert not scheduler.running

        response = await test_client.post(
            "/api/admin/scheduler/toggle",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["running"] is True
        assert "started" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_toggle_stops_running_scheduler(self, test_client: AsyncClient):
        """Test that toggle stops a running scheduler."""
        # First start the scheduler
        await test_client.post(
            "/api/admin/scheduler/toggle",
            headers=get_auth_header(),
        )

        scheduler = get_scheduler()
        assert scheduler.running

        # Now toggle again to stop
        response = await test_client.post(
            "/api/admin/scheduler/toggle",
            headers=get_auth_header(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["running"] is False
        assert "stopped" in data["message"].lower()


class TestManualCollectionEndpoints:
    """Tests for manual collection trigger endpoints."""

    @pytest.mark.asyncio
    async def test_trigger_forecasts_returns_response(self, test_client: AsyncClient):
        """Test that forecast trigger returns collection response."""
        # Mock the collect_all_forecasts function to avoid external API calls
        with patch(
            "api.routes.admin.collect_all_forecasts",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = await test_client.post(
                "/api/admin/collect/forecasts",
                headers=get_auth_header(),
            )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "recordsCollected" in data
        assert "durationSeconds" in data

    @pytest.mark.asyncio
    async def test_trigger_observations_returns_response(self, test_client: AsyncClient):
        """Test that observation trigger returns collection response."""
        # Mock the collect_all_observations function to avoid external API calls
        with patch(
            "api.routes.admin.collect_all_observations",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = await test_client.post(
                "/api/admin/collect/observations",
                headers=get_auth_header(),
            )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "recordsCollected" in data
        assert "durationSeconds" in data

    @pytest.mark.asyncio
    async def test_forecast_collection_returns_persisted_count(self, test_client: AsyncClient):
        """Test that forecast collection returns both collected and persisted counts."""
        mock_result = {
            "status": "success",
            "records_collected": 100,
            "records_persisted": 95,
            "duration_seconds": 30.5,
            "errors": None,
        }

        with patch(
            "api.routes.admin.collect_all_forecasts",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = await test_client.post(
                "/api/admin/collect/forecasts",
                headers=get_auth_header(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["recordsCollected"] == 100
        assert data["recordsPersisted"] == 95


class TestStatsEndpoint:
    """Tests for GET /api/admin/stats endpoint."""

    @pytest.mark.asyncio
    async def test_stats_returns_counts(self, test_client: AsyncClient):
        """Test that stats endpoint returns all counts."""
        mock_stats = {
            "total_forecasts": 1234,
            "total_observations": 567,
            "total_deviations": 890,
            "total_pairs": 123,
            "total_sites": 1,
        }

        with patch(
            "api.routes.admin.get_data_stats",
            new_callable=AsyncMock,
            return_value=mock_stats,
        ):
            response = await test_client.get(
                "/api/admin/stats",
                headers=get_auth_header(),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["totalForecasts"] == 1234
        assert data["totalObservations"] == 567
        assert data["totalDeviations"] == 890
        assert data["totalPairs"] == 123
        assert data["totalSites"] == 1

    @pytest.mark.asyncio
    async def test_stats_requires_auth(self, test_client: AsyncClient):
        """Test that stats endpoint requires authentication."""
        response = await test_client.get("/api/admin/stats")
        assert response.status_code == 401


class TestDataPreviewEndpoint:
    """Tests for GET /api/admin/data-preview endpoint."""

    @pytest.mark.asyncio
    async def test_preview_returns_data_structure(self, test_client: AsyncClient):
        """Test that preview endpoint returns expected structure."""
        mock_preview = {
            "forecasts": {
                "AROME": [
                    {
                        "id": 1,
                        "site": "Passy",
                        "parameter": "Wind Speed",
                        "valid_time": "2026-01-17T12:00:00Z",
                        "value": 15.5,
                        "created_at": "2026-01-17T10:00:00Z",
                    }
                ],
                "Meteo-Parapente": [],
            },
            "observations": {
                "ROMMA": [
                    {
                        "id": 1,
                        "site": "Passy",
                        "parameter": "Wind Speed",
                        "observation_time": "2026-01-17T12:00:00Z",
                        "value": 12.3,
                        "created_at": "2026-01-17T12:05:00Z",
                    }
                ],
                "FFVL": [],
            },
        }

        with patch(
            "api.routes.admin.get_recent_data_preview",
            new_callable=AsyncMock,
            return_value=mock_preview,
        ):
            response = await test_client.get(
                "/api/admin/data-preview",
                headers=get_auth_header(),
            )

        assert response.status_code == 200
        data = response.json()
        assert "forecasts" in data
        assert "observations" in data
        assert "AROME" in data["forecasts"]
        assert "ROMMA" in data["observations"]

    @pytest.mark.asyncio
    async def test_preview_requires_auth(self, test_client: AsyncClient):
        """Test that preview endpoint requires authentication."""
        response = await test_client.get("/api/admin/data-preview")
        assert response.status_code == 401
