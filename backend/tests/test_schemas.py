"""Tests for Pydantic response schemas.

Tests verify:
- Schema field mapping (snake_case to camelCase)
- ORM mode (from_attributes) works with SQLAlchemy models
- Pagination response structure
- JSON serialization with aliases
"""

from datetime import datetime, timezone

import pytest


class TestSiteResponse:
    """Tests for SiteResponse schema."""

    def test_from_dict(self):
        """Test creating SiteResponse from dictionary."""
        from core.schemas import SiteResponse

        data = {
            "id": 1,
            "name": "Test Site",
            "latitude": 45.5,
            "longitude": 6.5,
            "altitude": 1000,
            "created_at": datetime(2026, 1, 11, tzinfo=timezone.utc),
        }
        site = SiteResponse(**data)

        assert site.id == 1
        assert site.name == "Test Site"
        assert site.latitude == 45.5

    def test_json_serialization_uses_aliases(self):
        """Test that JSON output uses camelCase aliases."""
        from core.schemas import SiteResponse

        site = SiteResponse(
            id=1,
            name="Test Site",
            latitude=45.5,
            longitude=6.5,
            altitude=1000,
            created_at=datetime(2026, 1, 11, tzinfo=timezone.utc),
        )

        json_data = site.model_dump(by_alias=True)

        assert "lat" in json_data
        assert "lon" in json_data
        assert "alt" in json_data
        assert "createdAt" in json_data
        # Original names should not be present when using aliases
        assert "latitude" not in json_data
        assert "longitude" not in json_data
        assert "altitude" not in json_data
        assert "created_at" not in json_data

    def test_from_attributes(self):
        """Test that from_attributes works with ORM-like objects."""
        from core.schemas import SiteResponse

        class MockSite:
            id = 1
            name = "Test Site"
            latitude = 45.5
            longitude = 6.5
            altitude = 1000
            created_at = datetime(2026, 1, 11, tzinfo=timezone.utc)

        site = SiteResponse.model_validate(MockSite())

        assert site.id == 1
        assert site.name == "Test Site"


class TestModelResponse:
    """Tests for ModelResponse schema."""

    def test_from_dict(self):
        """Test creating ModelResponse from dictionary."""
        from core.schemas import ModelResponse

        data = {
            "id": 1,
            "name": "AROME",
            "source": "Meteo-France",
            "created_at": datetime(2026, 1, 11, tzinfo=timezone.utc),
        }
        model = ModelResponse(**data)

        assert model.id == 1
        assert model.name == "AROME"
        assert model.source == "Meteo-France"

    def test_json_serialization_uses_aliases(self):
        """Test that JSON output uses camelCase aliases."""
        from core.schemas import ModelResponse

        model = ModelResponse(
            id=1,
            name="AROME",
            source="Meteo-France",
            created_at=datetime(2026, 1, 11, tzinfo=timezone.utc),
        )

        json_data = model.model_dump(by_alias=True)

        assert "createdAt" in json_data
        assert "created_at" not in json_data


class TestParameterResponse:
    """Tests for ParameterResponse schema."""

    def test_from_dict(self):
        """Test creating ParameterResponse from dictionary."""
        from core.schemas import ParameterResponse

        data = {
            "id": 1,
            "name": "Wind Speed",
            "unit": "km/h",
            "created_at": datetime(2026, 1, 11, tzinfo=timezone.utc),
        }
        param = ParameterResponse(**data)

        assert param.id == 1
        assert param.name == "Wind Speed"
        assert param.unit == "km/h"


class TestMetaResponse:
    """Tests for MetaResponse schema."""

    def test_default_values(self):
        """Test default values for pagination metadata."""
        from core.schemas import MetaResponse

        meta = MetaResponse(total=100)

        assert meta.total == 100
        assert meta.page == 1
        assert meta.per_page == 100

    def test_json_serialization_uses_aliases(self):
        """Test that JSON output uses camelCase aliases."""
        from core.schemas import MetaResponse

        meta = MetaResponse(total=100, page=2, per_page=50)

        json_data = meta.model_dump(by_alias=True)

        assert "perPage" in json_data
        assert json_data["perPage"] == 50
        assert "per_page" not in json_data


class TestPaginatedResponse:
    """Tests for PaginatedResponse schema."""

    def test_with_site_responses(self):
        """Test PaginatedResponse with SiteResponse items."""
        from core.schemas import MetaResponse, PaginatedResponse, SiteResponse

        sites = [
            SiteResponse(
                id=1,
                name="Site 1",
                latitude=45.5,
                longitude=6.5,
                altitude=1000,
                created_at=datetime(2026, 1, 11, tzinfo=timezone.utc),
            ),
            SiteResponse(
                id=2,
                name="Site 2",
                latitude=46.0,
                longitude=7.0,
                altitude=1500,
                created_at=datetime(2026, 1, 11, tzinfo=timezone.utc),
            ),
        ]

        response = PaginatedResponse[SiteResponse](
            data=sites, meta=MetaResponse(total=2)
        )

        assert len(response.data) == 2
        assert response.meta.total == 2
        assert response.data[0].name == "Site 1"

    def test_json_structure(self):
        """Test that JSON output has correct structure."""
        from core.schemas import MetaResponse, PaginatedResponse, SiteResponse

        site = SiteResponse(
            id=1,
            name="Site",
            latitude=45.5,
            longitude=6.5,
            altitude=1000,
            created_at=datetime(2026, 1, 11, tzinfo=timezone.utc),
        )

        response = PaginatedResponse[SiteResponse](
            data=[site], meta=MetaResponse(total=1)
        )

        json_data = response.model_dump(by_alias=True)

        assert "data" in json_data
        assert "meta" in json_data
        assert len(json_data["data"]) == 1
        assert json_data["meta"]["total"] == 1
        assert json_data["meta"]["perPage"] == 100


class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_healthy_response(self):
        """Test healthy status response."""
        from core.schemas import HealthResponse

        health = HealthResponse(status="healthy")

        assert health.status == "healthy"
        assert health.database is None

    def test_with_database_status(self):
        """Test response with database status."""
        from core.schemas import HealthResponse

        health = HealthResponse(status="healthy", database="connected")

        assert health.status == "healthy"
        assert health.database == "connected"
