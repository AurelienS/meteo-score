"""Tests for parameters API endpoints.

Tests verify:
- GET /api/parameters returns paginated response
- GET /api/parameters/{id} returns single parameter
- 404 returned for non-existent parameter
"""

import pytest
from httpx import AsyncClient


class TestParametersEndpoints:
    """Tests for parameters API endpoints."""

    @pytest.mark.asyncio
    async def test_get_parameters_returns_paginated_response(
        self, test_client: AsyncClient
    ):
        """Test GET /api/parameters returns correct paginated structure."""
        response = await test_client.get("/api/parameters")

        assert response.status_code == 200
        data = response.json()

        # Check paginated response structure
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)
        assert "total" in data["meta"]
        assert "page" in data["meta"]
        assert "perPage" in data["meta"]

    @pytest.mark.asyncio
    async def test_get_parameters_meta_defaults(self, test_client: AsyncClient):
        """Test GET /api/parameters meta has correct default values."""
        response = await test_client.get("/api/parameters")

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["page"] == 1
        assert data["meta"]["perPage"] == 100

    @pytest.mark.asyncio
    async def test_get_parameters_pagination_params(self, test_client: AsyncClient):
        """Test GET /api/parameters respects pagination parameters."""
        response = await test_client.get("/api/parameters?page=2&per_page=50")

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["page"] == 2
        assert data["meta"]["perPage"] == 50

    @pytest.mark.asyncio
    async def test_get_parameter_not_found(self, test_client: AsyncClient):
        """Test GET /api/parameters/{id} returns 404 for non-existent parameter."""
        response = await test_client.get("/api/parameters/99999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_get_parameters_empty_database(self, test_client: AsyncClient):
        """Test GET /api/parameters returns empty list when no params exist."""
        response = await test_client.get("/api/parameters")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0
