"""Tests for main application module.

Tests verify:
- Application starts correctly
- CORS headers are present
- Rate limiting works
- OpenAPI docs are available
"""

import pytest
from httpx import AsyncClient

from main import app, request_counts


class TestApplication:
    """Tests for FastAPI application."""

    def test_app_has_correct_title(self):
        """Test application has correct title."""
        assert app.title == "MétéoScore API"

    def test_app_has_correct_version(self):
        """Test application has correct version."""
        assert app.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_openapi_docs_available(self, test_client: AsyncClient):
        """Test OpenAPI docs are available at /docs."""
        response = await test_client.get("/docs")

        # Should return HTML page
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_redoc_available(self, test_client: AsyncClient):
        """Test ReDoc is available at /redoc."""
        response = await test_client.get("/redoc")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_openapi_json_available(self, test_client: AsyncClient):
        """Test OpenAPI JSON schema is available."""
        response = await test_client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data


class TestCORS:
    """Tests for CORS middleware."""

    @pytest.mark.asyncio
    async def test_cors_headers_on_request(self, test_client: AsyncClient):
        """Test CORS headers are present on response."""
        response = await test_client.options(
            "/api/sites",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS preflight should be handled
        assert response.status_code in [200, 204]


class TestRateLimiting:
    """Tests for rate limiting middleware."""

    @pytest.fixture(autouse=True)
    def clear_rate_limits(self):
        """Clear rate limit state before each test."""
        request_counts.clear()
        yield
        request_counts.clear()

    @pytest.mark.asyncio
    async def test_health_endpoints_bypass_rate_limit(self, test_client: AsyncClient):
        """Test that health endpoints are not rate limited."""
        # Make many requests to health endpoint
        for _ in range(110):
            response = await test_client.get("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_root_endpoint_bypasses_rate_limit(self, test_client: AsyncClient):
        """Test that root endpoint is not rate limited."""
        # Make many requests to root endpoint
        for _ in range(110):
            response = await test_client.get("/")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_api_endpoints_are_rate_limited(self, test_client: AsyncClient):
        """Test that API endpoints are rate limited after 100 requests."""
        from core.config import get_settings

        settings = get_settings()
        limit = settings.rate_limit_per_minute

        # Use trailing slash to avoid redirect (which would count as 2 requests)
        # Make requests up to the limit
        for i in range(limit):
            response = await test_client.get("/api/sites/")
            assert response.status_code == 200, f"Request {i+1} failed"

        # Next request should be rate limited
        response = await test_client.get("/api/sites/")
        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "RateLimitError"

    @pytest.mark.asyncio
    async def test_rate_limit_error_response_format(self, test_client: AsyncClient):
        """Test rate limit error response has correct format."""
        from core.config import get_settings

        settings = get_settings()
        limit = settings.rate_limit_per_minute

        # Use trailing slash to avoid redirect (which would count as 2 requests)
        # Exhaust rate limit
        for _ in range(limit):
            await test_client.get("/api/sites/")

        # Check error response format
        response = await test_client.get("/api/sites/")
        assert response.status_code == 429
        data = response.json()
        assert "error" in data
        assert "detail" in data
        assert "statusCode" in data
        assert data["statusCode"] == 429
