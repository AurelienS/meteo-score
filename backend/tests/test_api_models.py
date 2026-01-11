"""Tests for weather models API endpoints.

Tests verify:
- GET /api/models returns paginated response
- GET /api/models/{id} returns single model
- 404 returned for non-existent model
"""

import pytest
from httpx import AsyncClient


class TestModelsEndpoints:
    """Tests for weather models API endpoints."""

    @pytest.mark.asyncio
    async def test_get_models_returns_paginated_response(
        self, test_client: AsyncClient
    ):
        """Test GET /api/models returns correct paginated structure."""
        response = await test_client.get("/api/models")

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
    async def test_get_models_meta_defaults(self, test_client: AsyncClient):
        """Test GET /api/models meta has correct default values."""
        response = await test_client.get("/api/models")

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["page"] == 1
        assert data["meta"]["perPage"] == 100

    @pytest.mark.asyncio
    async def test_get_models_pagination_params(self, test_client: AsyncClient):
        """Test GET /api/models respects pagination parameters."""
        response = await test_client.get("/api/models?page=2&per_page=50")

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["page"] == 2
        assert data["meta"]["perPage"] == 50

    @pytest.mark.asyncio
    async def test_get_model_not_found(self, test_client: AsyncClient):
        """Test GET /api/models/{id} returns 404 for non-existent model."""
        response = await test_client.get("/api/models/99999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_get_models_empty_database(self, test_client: AsyncClient):
        """Test GET /api/models returns empty list when no models exist."""
        response = await test_client.get("/api/models")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0
