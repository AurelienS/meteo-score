"""Tests for sites API endpoints.

Tests verify:
- GET /api/sites returns paginated response
- GET /api/sites/{id} returns single site
- Pagination parameters work correctly
- 404 returned for non-existent site
- Response uses camelCase field names
"""

import pytest
from httpx import AsyncClient


class TestSitesEndpoints:
    """Tests for sites API endpoints."""

    @pytest.mark.asyncio
    async def test_get_sites_returns_paginated_response(self, test_client: AsyncClient):
        """Test GET /api/sites returns correct paginated structure."""
        response = await test_client.get("/api/sites")

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
    async def test_get_sites_meta_defaults(self, test_client: AsyncClient):
        """Test GET /api/sites meta has correct default values."""
        response = await test_client.get("/api/sites")

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["page"] == 1
        assert data["meta"]["perPage"] == 100

    @pytest.mark.asyncio
    async def test_get_sites_pagination_params(self, test_client: AsyncClient):
        """Test GET /api/sites respects pagination parameters."""
        response = await test_client.get("/api/sites?page=2&per_page=50")

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["page"] == 2
        assert data["meta"]["perPage"] == 50

    @pytest.mark.asyncio
    async def test_get_sites_per_page_max_limit(self, test_client: AsyncClient):
        """Test GET /api/sites validates per_page maximum."""
        response = await test_client.get("/api/sites?per_page=200")

        # Should reject values exceeding 100
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_get_site_not_found(self, test_client: AsyncClient):
        """Test GET /api/sites/{id} returns 404 for non-existent site."""
        response = await test_client.get("/api/sites/99999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_get_sites_empty_database(self, test_client: AsyncClient):
        """Test GET /api/sites returns empty list when no sites exist."""
        response = await test_client.get("/api/sites")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0
