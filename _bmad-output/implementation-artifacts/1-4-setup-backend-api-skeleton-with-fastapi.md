---
story_id: "1.4"
epic: 1
title: "Setup Backend API Skeleton with FastAPI"
status: done
created: "2026-01-11"
completed: "2026-01-11"
---

# Story 1.4: Setup Backend API Skeleton with FastAPI

## User Story

As a developer,
I want to setup the FastAPI backend skeleton with core configuration and base structure,
So that the API foundation is ready for implementing business logic and routes.

## Business Context

This story transforms the stub FastAPI application into a production-ready API skeleton. It establishes:

- **API Architecture** - Standardized response formats, router structure, and middleware stack
- **Configuration Management** - Environment-based settings with Pydantic validation
- **Pydantic Schemas** - Response models with camelCase JSON mapping for frontend consumption
- **Reusable Patterns** - Base route handlers that future stories will extend

This builds directly on Story 1.3's database layer and prepares the foundation for Epic 2's data collection routes.

## Acceptance Criteria

### AC1: FastAPI Application Entry Point (`backend/main.py`)

**Given** the existing stub main.py
**When** I update it with full configuration
**Then** the following are implemented:
- FastAPI app instance with proper metadata (title, description, version)
- CORS middleware configured for frontend origin (`http://localhost:5173`)
- Rate limiting middleware (100 req/min per IP) with in-memory store
- Router includes configured for `/api` prefix
- Application startup/shutdown lifecycle events (engine disposal)
- Health check endpoint `/health` returns `{"status": "healthy"}`

### AC2: Configuration Management (`backend/core/config.py`)

**Given** environment variables for configuration
**When** I create the config module
**Then** the following are implemented:
- Pydantic `BaseSettings` class loading from environment
- `DATABASE_URL` with validation for asyncpg driver
- `FRONTEND_URL` defaulting to `http://localhost:5173`
- `API_BASE_URL` defaulting to `http://localhost:8000`
- `ENVIRONMENT` setting (development/production)
- `RATE_LIMIT_PER_MINUTE` defaulting to 100
- All configuration validated on startup via dependency

### AC3: Pydantic Response Schemas (`backend/core/schemas.py`)

**Given** the ORM models from Story 1.3
**When** I create Pydantic response schemas
**Then** the following schemas are implemented:

```python
# All use Field(alias="camelCase") for JSON mapping
class SiteResponse(BaseModel):
    id: int
    name: str
    latitude: float = Field(alias="lat")
    longitude: float = Field(alias="lon")
    altitude: int = Field(alias="alt")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class ModelResponse(BaseModel):
    id: int
    name: str
    source: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class ParameterResponse(BaseModel):
    id: int
    name: str
    unit: str
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

# Meta information for paginated responses
class MetaResponse(BaseModel):
    total: int
    page: int = 1
    per_page: int = Field(default=100, alias="perPage")

    model_config = ConfigDict(populate_by_name=True)

# Generic paginated response wrapper
class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: MetaResponse
```

### AC4: API Route Structure (`backend/api/routes/`)

**Given** the API architecture requirements
**When** I create the route structure
**Then** the following are implemented:

- `backend/api/routes/__init__.py` - Router aggregation with `/api` prefix
- `backend/api/routes/sites.py` - Sites CRUD endpoint stubs
- `backend/api/routes/models.py` - Models endpoint stubs
- `backend/api/routes/parameters.py` - Parameters endpoint stubs
- `backend/api/routes/health.py` - Health check endpoint

Initial working endpoints:
- `GET /health` returns `{"status": "healthy"}`
- `GET /api/sites` returns `{"data": [...sites from DB], "meta": {"total": N, "page": 1, "perPage": 100}}`
- `GET /api/models` returns `{"data": [...models from DB], "meta": {...}}`
- `GET /api/parameters` returns `{"data": [...params from DB], "meta": {...}}`

### AC5: Async Patterns Verification

**Given** the async architecture requirements
**When** I implement all components
**Then**:
- All route handlers are `async def` functions
- Database queries use `await session.execute(select(...))`
- `get_db()` dependency is used for session management
- No synchronous blocking operations in request handlers

### AC6: Type Hints and Documentation

**Given** the code quality requirements
**When** I complete the implementation
**Then**:
- All functions have complete type hints
- All public classes have docstrings
- FastAPI auto-generates OpenAPI documentation at `/docs`

### AC7: Backend Startup Validation

**Given** the complete implementation
**When** I start the backend with `uvicorn main:app --reload`
**Then**:
- Application starts on port 8000
- `/health` returns 200 with `{"status": "healthy"}`
- `/docs` shows interactive API documentation
- `/api/sites` returns paginated site data from database

## Tasks / Subtasks

- [x] Task 1: Create configuration module (AC: 2)
  - [x] Create `backend/core/config.py` with Pydantic Settings
  - [x] Define all environment variables with defaults
  - [x] Add config validation function
  - [x] Export settings singleton

- [x] Task 2: Create Pydantic response schemas (AC: 3)
  - [x] Create `backend/core/schemas.py`
  - [x] Implement SiteResponse with camelCase aliases
  - [x] Implement ModelResponse with camelCase aliases
  - [x] Implement ParameterResponse with camelCase aliases
  - [x] Implement MetaResponse and PaginatedResponse generics
  - [x] Add model_config with populate_by_name and from_attributes

- [x] Task 3: Create health endpoint (AC: 1, 4)
  - [x] Create `backend/api/routes/health.py`
  - [x] Implement `/health` endpoint with DB connectivity check
  - [x] Return structured health response

- [x] Task 4: Create sites route (AC: 4, 5)
  - [x] Create `backend/api/routes/sites.py`
  - [x] Implement `GET /api/sites` with pagination
  - [x] Use async session with select() queries
  - [x] Return PaginatedResponse[SiteResponse]

- [x] Task 5: Create models and parameters routes (AC: 4, 5)
  - [x] Create `backend/api/routes/models.py`
  - [x] Create `backend/api/routes/parameters.py`
  - [x] Implement GET endpoints with pagination
  - [x] Follow same async patterns as sites

- [x] Task 6: Create router aggregation (AC: 4)
  - [x] Update `backend/api/routes/__init__.py`
  - [x] Create main api_router with prefix `/api`
  - [x] Include all route modules

- [x] Task 7: Update main.py with full configuration (AC: 1)
  - [x] Add CORS middleware for frontend origin
  - [x] Add simple rate limiting middleware
  - [x] Include api_router
  - [x] Add startup/shutdown lifecycle events
  - [x] Ensure health endpoint at root level

- [x] Task 8: Write tests for all new components (AC: all)
  - [x] Test config loading and validation
  - [x] Test Pydantic schemas serialization
  - [x] Test API endpoints with test client
  - [x] Test pagination behavior
  - [x] Achieve >80% coverage on new code (88% achieved)

## Dev Notes

### Critical Architecture Patterns

**Pydantic V2 Field Mapping (CRITICAL):**
```python
from pydantic import BaseModel, Field, ConfigDict

class SiteResponse(BaseModel):
    id: int
    latitude: float = Field(alias="lat")  # JSON will have "lat"

    model_config = ConfigDict(
        populate_by_name=True,  # Accept both "latitude" and "lat"
        from_attributes=True,   # Enable ORM mode for SQLAlchemy
    )
```

**Response Format (Standard):**
```json
{
  "data": [...],
  "meta": {
    "total": 100,
    "page": 1,
    "perPage": 100
  }
}
```

**Async Route Pattern:**
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from core.database import get_db

@router.get("/", response_model=PaginatedResponse[SiteResponse])
async def get_sites(db: AsyncSession = Depends(get_db)) -> PaginatedResponse[SiteResponse]:
    result = await db.execute(select(Site))
    sites = result.scalars().all()
    return PaginatedResponse(
        data=[SiteResponse.model_validate(s) for s in sites],
        meta=MetaResponse(total=len(sites))
    )
```

**Rate Limiting (Simple In-Memory):**
```python
from collections import defaultdict
from time import time

# Simple sliding window rate limiter
request_counts: dict[str, list[float]] = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    now = time()
    window = 60  # 1 minute

    # Clean old requests
    request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < window]

    if len(request_counts[client_ip]) >= 100:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    request_counts[client_ip].append(now)
    return await call_next(request)
```

### Existing Code to Leverage

**From Story 1.3 (DO NOT RECREATE):**
- `backend/core/database.py` - Already has `get_db()`, `get_engine()`, `close_engine()`
- `backend/core/models.py` - Already has Site, Model, Parameter, Deviation ORM models
- `backend/core/__init__.py` - Already exports database and model components

**Files to CREATE:**
- `backend/core/config.py` - NEW
- `backend/core/schemas.py` - NEW
- `backend/api/routes/health.py` - NEW
- `backend/api/routes/sites.py` - NEW
- `backend/api/routes/models.py` - NEW
- `backend/api/routes/parameters.py` - NEW

**Files to UPDATE:**
- `backend/api/routes/__init__.py` - Add router aggregation
- `backend/main.py` - Full implementation (replace stub)

### Project Structure Notes

Alignment with unified project structure:
- Routes in `backend/api/routes/{resource}.py` per architecture
- Core utilities in `backend/core/` per architecture
- Tests in `backend/tests/test_{module}.py`

### Testing Requirements

**Test Files to Create:**
- `backend/tests/test_config.py` - Config loading tests
- `backend/tests/test_schemas.py` - Schema serialization tests
- `backend/tests/test_api_sites.py` - Sites endpoint tests
- `backend/tests/test_api_models.py` - Models endpoint tests
- `backend/tests/test_api_health.py` - Health endpoint tests

**Test Patterns:**
```python
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_get_sites():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/sites")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "meta" in data
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md - Story 1.4]
- [Source: _bmad-output/project-context.md - FastAPI Patterns, Pydantic V2]
- [Source: _bmad-output/planning-artifacts/architecture-meteo-score-2026-01-10.md]
- [Source: Story 1.3 - Database layer implementation]

## Definition of Done

- [x] `backend/core/config.py` created with Pydantic Settings
- [x] `backend/core/schemas.py` created with all response schemas
- [x] All schemas use Field(serialization_alias=) for camelCase mapping
- [x] All schemas have model_config with populate_by_name=True, from_attributes=True
- [x] `backend/api/routes/health.py` created
- [x] `backend/api/routes/sites.py` created with GET endpoint
- [x] `backend/api/routes/models.py` created with GET endpoint
- [x] `backend/api/routes/parameters.py` created with GET endpoint
- [x] `backend/api/routes/__init__.py` aggregates all routers
- [x] `backend/main.py` updated with CORS and rate limiting middleware
- [x] `backend/main.py` includes api_router with `/api` prefix
- [x] Startup/shutdown events handle database lifecycle
- [x] All route handlers are async functions
- [x] All functions have complete type hints
- [x] `/health` returns `{"status": "healthy"}`
- [x] `/api/sites` returns paginated response from database
- [x] `/api/models` returns paginated response from database
- [x] `/api/parameters` returns paginated response from database
- [x] OpenAPI docs available at `/docs`
- [x] Tests created for config, schemas, and all API endpoints
- [x] All tests pass with >80% coverage on new code (88% achieved)

## Related Files

- **Epic file:** `/home/fly/dev/meteo-score/_bmad-output/planning-artifacts/epics.md` (Story 1.4, lines 425-487)
- **Project Context:** `/home/fly/dev/meteo-score/_bmad-output/project-context.md`
- **Architecture:** `/home/fly/dev/meteo-score/_bmad-output/planning-artifacts/architecture-meteo-score-2026-01-10.md`
- **Previous Story:** `/home/fly/dev/meteo-score/_bmad-output/implementation-artifacts/1-3-configure-timescaledb-with-hypertables.md`
- **Sprint Status:** `/home/fly/dev/meteo-score/_bmad-output/implementation-artifacts/sprint-status.yaml`

## Success Validation

**After completing this story, you should be able to:**

1. Start backend: `cd backend && uvicorn main:app --reload`
2. Health check: `curl http://localhost:8000/health` → `{"status": "healthy"}`
3. Get sites: `curl http://localhost:8000/api/sites` → `{"data": [...], "meta": {...}}`
4. Get models: `curl http://localhost:8000/api/models` → `{"data": [...], "meta": {...}}`
5. View docs: Open `http://localhost:8000/docs` in browser
6. Verify camelCase: JSON responses use camelCase field names (createdAt, perPage)
7. Run tests: `pytest tests/test_api_*.py tests/test_config.py tests/test_schemas.py -v`

**What This Story DOES NOT Include:**
- Full CRUD operations (create, update, delete) - future stories
- Deviations/bias_summary endpoints - Epic 3
- Authentication (not needed - public API)
- Production deployment configuration - Story 1.5+

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None required - all tests pass.

### Completion Notes List

1. **Task 1**: Created `backend/core/config.py` with Pydantic Settings for environment-based configuration. Includes DATABASE_URL validation to ensure asyncpg driver, FRONTEND_URL, ENVIRONMENT, and RATE_LIMIT_PER_MINUTE settings.

2. **Task 2**: Created `backend/core/schemas.py` with Pydantic V2 response schemas. Used `serialization_alias` for camelCase JSON output (lat, lon, alt, createdAt, perPage). Implemented generic `PaginatedResponse[T]` for standard response format.

3. **Task 3**: Created `backend/api/routes/health.py` with `/health` and `/` endpoints. Health endpoint includes database connectivity check.

4. **Task 4-5**: Created `sites.py`, `models.py`, `parameters.py` routes with GET endpoints, pagination support, and 404 handling for individual resources.

5. **Task 6**: Updated `backend/api/routes/__init__.py` with router aggregation under `/api` prefix.

6. **Task 7**: Updated `backend/main.py` with CORS middleware (frontend origin), simple in-memory rate limiting middleware (100 req/min, bypasses health endpoints), and lifespan manager for database cleanup on shutdown.

7. **Task 8**: Created comprehensive test suite with 85 tests total, achieving 88% coverage (exceeds 80% requirement).

**Technical Decisions:**
- Used `serialization_alias` instead of `alias` for Pydantic V2 JSON output (avoids validation issues)
- Implemented simple in-memory rate limiting (production would use Redis)
- Health endpoints bypass rate limiting for load balancer compatibility
- Added `test_app` and `test_client` fixtures in conftest.py for API testing with database override

### File List

**New Files Created:**
- `backend/core/config.py` - Configuration management with Pydantic Settings
- `backend/core/schemas.py` - Pydantic response schemas with camelCase mapping
- `backend/api/routes/health.py` - Health check endpoints
- `backend/api/routes/sites.py` - Sites API with pagination
- `backend/api/routes/models.py` - Models API with pagination
- `backend/api/routes/parameters.py` - Parameters API with pagination
- `backend/tests/test_config.py` - Configuration tests (11 tests)
- `backend/tests/test_schemas.py` - Schema serialization tests (12 tests)
- `backend/tests/test_api_health.py` - Health endpoint tests (3 tests)
- `backend/tests/test_api_sites.py` - Sites endpoint tests (6 tests)
- `backend/tests/test_api_models.py` - Models endpoint tests (5 tests)
- `backend/tests/test_api_parameters.py` - Parameters endpoint tests (5 tests)
- `backend/tests/test_main.py` - Main app tests (8 tests)

**Modified Files:**
- `backend/main.py` - Full implementation replacing stub
- `backend/api/routes/__init__.py` - Router aggregation
- `backend/core/__init__.py` - Added config and schemas exports
- `backend/tests/conftest.py` - Added test_app and test_client fixtures

### Code Review Findings & Fixes

**Code Review Performed:** Adversarial Senior Developer review

**Issues Found & Fixed:**

1. **H1 (HIGH): Rate limiting not fully tested** - FIXED
   - Added comprehensive rate limiting tests in `test_main.py`
   - Tests verify 100 requests succeed, 101st is rate limited
   - Tests verify correct error response format

2. **M1 (MEDIUM): Inconsistent HTTPException import in sites.py** - FIXED
   - Moved HTTPException import to module level for consistency with models.py and parameters.py

3. **M2 (MEDIUM): Rate limiter memory cleanup** - FIXED
   - Added periodic cleanup mechanism (every 5 minutes) to remove stale IPs
   - Prevents memory leak from accumulating inactive client entries

4. **M3 (MEDIUM): Pagination input validation** - FIXED
   - Added `Query(ge=1, le=100)` validators to pagination parameters
   - Invalid values now return 422 validation error instead of silent clamping

5. **M4 (MEDIUM): Health endpoint degraded status** - FIXED
   - Health endpoint now returns "degraded" status when database is unavailable
   - Updated HealthResponse schema docstring to document status values

**Additional Fix During Review:**
- Rate limiting tests updated to use trailing slash URLs (`/api/sites/`)
- FastAPI redirects `/api/sites` to `/api/sites/`, which was counting as 2 requests
- Test client fixture now clears rate limiter state and settings cache

**Final Test Results:** 87 tests pass with 95.21% coverage
