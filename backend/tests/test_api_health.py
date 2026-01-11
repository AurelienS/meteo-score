"""Tests for health check API endpoints.

Tests verify:
- Root endpoint returns healthy status
- Health endpoint returns healthy status with DB check
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, test_client: AsyncClient):
        """Test root endpoint returns healthy status."""
        response = await test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, test_client: AsyncClient):
        """Test health endpoint returns healthy status with DB info."""
        response = await test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data

    @pytest.mark.asyncio
    async def test_health_endpoint_response_schema(self, test_client: AsyncClient):
        """Test health endpoint response matches HealthResponse schema."""
        from core.schemas import HealthResponse

        response = await test_client.get("/health")

        data = response.json()
        # Should be valid HealthResponse
        health = HealthResponse(**data)
        assert health.status == "healthy"
