---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - "_bmad-output/planning-artifacts/product-brief-meteo-score-2026-01-10.md"
  - "_bmad-output/planning-artifacts/architecture-meteo-score-2026-01-10.md"
  - "_bmad-output/planning-artifacts/ux-design-specification.md"
date: "2026-01-10"
author: "boss"
project_name: "meteo-score"
totalEpics: 5
totalStories: 30
---

# meteo-score - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for meteo-score, decomposing the requirements from the Product Brief, Architecture, and UX Design Specification into implementable stories.

## Requirements Inventory

### Functional Requirements

**FR1: Automated Forecast Collection**
- The system must automatically collect weather forecast data from multiple models (AROME, Meteo-Parapente)
- Collection frequency: 4x daily (00h, 06h, 12h, 18h UTC runs)
- Parameters: Wind (speed + direction), Temperature
- Modular collectors using Strategy pattern (backend/collectors/)
- Implementation: meteo_parapente.py, arome.py using cfgrib/xarray/requests

**FR2: Automated Observation Collection**
- The system must automatically collect real-world observations from weather beacons (ROMMA, FFVL)
- Collection frequency: 6x daily during daylight hours (8h-18h)
- Parameters: Wind (speed + direction), Temperature
- Implementation: romma.py, ffvl.py using BeautifulSoup4 for HTML scraping
- APScheduler orchestration for scheduled collection

**FR3: Deviation Calculation Engine**
- The system must calculate deviations between forecast predictions and actual observations
- Formula: deviation = forecast_value - observed_value
- Implementation: Stateless deviation_engine.py for testability
- Matching criteria: same timestamp, site, parameter, forecast horizon
- Store ONLY deviations (not full raw forecast/observation data - 100x storage reduction)

**FR4: Historical Time-Series Storage**
- The system must store historical deviation data in a time-series database
- Implementation: TimescaleDB hypertables with 7-day chunks
- Composite primary key: (timestamp, site_id, model_id, parameter_id, horizon)
- Database migrations: Alembic for schema versioning
- Continuous aggregates: Precomputed daily/weekly MAE metrics for performance

**FR5: Web Visualization Interface**
- The system must provide a web interface to visualize model comparison results
- Implementation: Solid.js frontend with 12 custom components
- Pages: Home (site list), SiteDetail (model comparisons), About (methodology)
- Visualizations: D3.js for custom time-series deviation charts
- Responsive design: Mobile-first with Tailwind CSS, WCAG 2.1 AA accessibility

**FR6: Contextual Bias Characterization**
- The system must calculate and display systematic biases for each model
- Implementation: /bias-summary API endpoint using continuous aggregates
- Frontend display: VerdictHeader (summary verdict), BiasIndicator (visual +/-)
- Actionable insights: "AROME overestimates wind by +10 km/h at Passy at H+6"
- Statistical metrics: MAE, bias direction, confidence intervals based on sample size

### Non-Functional Requirements

**NFR1: Reliability (>90% Pipeline Uptime)**
- Automated data collection pipeline must achieve >90% uptime
- APScheduler with exponential backoff retry logic (3 attempts)
- Graceful degradation: Missing data handled without pipeline failure
- Monitoring: Python logging to stdout → Docker logs
- Optional: UptimeRobot + Healthchecks.io for alerts

**NFR2: Performance (<2s API Response, <3s Frontend Load)**
- API responses must complete in <2 seconds
- Frontend page load must complete in <3 seconds
- Implementation: TimescaleDB continuous aggregates for precomputed metrics
- Async SQLAlchemy with connection pooling
- Vite code splitting by route, esbuild minification
- No external cache needed for MVP (continuous aggregates sufficient)

**NFR3: Scalability (1 site → 50+ sites)**
- Architecture must support scaling from 1 to 50+ sites without refactoring
- Modular collectors: Add new data sources without modifying existing code
- TimescaleDB hypertables: Scale to millions of time-series rows
- Horizontal project structure: Adding sites/models via configuration, not code changes
- Future path: Vertical scaling first (bigger VPS), then Celery workers if needed

**NFR4: Data Integrity (6-Level Validation Strategy)**
- Level 1: Manual validation of initial POC samples (human review)
- Level 2: Unit tests on parsers (>80% coverage, TDD approach)
- Level 3: Automated alerts on aberrant values (wind >200 km/h, temp <-50°C, deviation >100)
- Level 4: Cross-validation between multiple observation sources (ROMMA vs FFVL when available)
- Level 5: Historical comparison (statistical outlier detection against patterns)
- Level 6: Ship-and-iterate (deploy without publicity initially, margin for error correction)

**NFR5: Maintainability (TDD, >80% Test Coverage)**
- Backend: pytest + pytest-cov with >80% coverage enforced in pytest.ini
- TDD approach: Write tests BEFORE implementing data parsers
- Code quality: ruff (linter), black (formatter), mypy (type checker)
- Frontend: ESLint + Prettier (optional Vitest tests for MVP)
- CI/CD: GitHub Actions automated tests on every commit

**NFR6: Accessibility (WCAG 2.1 Level AA)**
- Semantic HTML with proper heading hierarchy
- ARIA labels for interactive elements
- Keyboard navigation support for all features
- Screen reader compatibility
- Sufficient color contrast ratios
- Focus indicators visible and clear
- Implementation: Tailwind CSS with accessibility-focused design

**NFR7: Security (Public Data Platform)**
- No user authentication system needed (all data is public)
- Rate limiting: 100 requests/minute per IP (FastAPI middleware)
- Input validation: Pydantic schemas enforce types, ranges, date formats
- SQL injection prevention: SQLAlchemy parameterized queries
- Transport security: HTTPS via Traefik + Let's Encrypt automatic certificates
- CORS: Configured for frontend origin only
- Never expose API keys in frontend code

### Additional Requirements

**From Architecture:**

- **Starter Template:** Custom project structure (no template) - Initialize from scratch following architecture patterns
- **Infrastructure:** Docker Compose for local dev and production (dev/prod parity)
- **Reverse Proxy:** Traefik v2.10 with automatic HTTPS via Let's Encrypt
- **Database Migrations:** Alembic for schema versioning, init_hypertables.sql for TimescaleDB setup
- **Deployment:** Self-hosted on VPS (NO external services: no Auth0, PlanetScale, Datadog, CDN dependencies)
- **Monitoring:** Python logging module to stdout → Docker logs (no advanced observability for MVP)
- **API Rate Limits:** AROME has 50 req/min limit - respect it with exponential backoff
- **Modular Collectors:** ALL collectors MUST implement BaseCollector interface (Strategy pattern)
- **TimescaleDB Features:** create_hypertable() for deviations table, continuous aggregates for MAE
- **Storage Model:** Store ONLY forecast_value, observed_value, deviation (NOT full GRIB2 files or beacon datasets)
- **API Response Format:** Standardized {data, meta} wrapper with camelCase fields
- **Date Format:** ISO 8601 with timezone (TIMESTAMPTZ in DB, "2026-01-10T14:30:00Z" in JSON)

**From UX Design:**

- **Mobile-First Design:** Primary use case is field/parking lot consultation on phones
- **Responsive Breakpoints:** 320-428px (mobile), 768-1024px (tablet), 1280px+ (desktop)
- **Touch-Optimized:** Large tap targets, no complex gestures, mobile-friendly interactions
- **No Pinch-Zoom:** Tables auto-optimize for small screens (stacked cards vs wide tables)
- **Fast Loading:** Optimized for 3G/4G mobile networks
- **Typography:** Geist Sans + Geist Mono fonts for clean, modern look
- **Color Palette:** Professional, data-focused design (not bright/playful)
- **Charts:** D3.js custom visualizations in component refs (manual DOM manipulation)
- **Navigation:** Simple, clear hierarchy optimized for mobile touch
- **Error States:** User-friendly error messages with retry buttons

### FR Coverage Map

**FR1: Automated Forecast Collection** → Epic 2 (Weather Data Collection Pipeline)
**FR2: Automated Observation Collection** → Epic 2 (Weather Data Collection Pipeline)
**FR3: Deviation Calculation Engine** → Epic 3 (Forecast Accuracy Analysis Engine)
**FR4: Historical Time-Series Storage** → Epic 1 (partial - DB setup), Epic 2 (data storage), Epic 3 (continuous aggregates)
**FR5: Web Visualization Interface** → Epic 4 (Model Comparison Web Platform)
**FR6: Contextual Bias Characterization** → Epic 3 (bias calculation), Epic 4 (bias visualization)

## Epic List

### Epic 1: Platform Foundation & Infrastructure Setup

**⚠️ NOTE: SPRINT 0 / FOUNDATION SPRINT**

This epic is recognized as a **technical infrastructure sprint** that provides necessary foundational setup but delivers **no standalone user value**. This is a pragmatic compromise for greenfield projects that require initial infrastructure before functional features can be built.

**Acknowledgment:**
- Violates epic independence best practice (cannot be deployed alone)
- Accepted as necessary "Sprint 0" for greenfield project reality
- First deployable user value arrives after Epic 2 (automated data collection)
- Decision documented per Implementation Readiness Assessment (2026-01-10)

---

Establish the foundational technical infrastructure that enables the system to collect, store, and serve weather data.

**User Outcome:** The platform has a working infrastructure (Docker containers, TimescaleDB database, project structure) ready to collect and analyze weather data.

**FRs Covered:** FR4 (partial - database setup)

**Implementation Notes:**
- Custom project structure initialization (no starter template)
- Docker Compose setup (postgres/TimescaleDB, backend skeleton, frontend skeleton)
- TimescaleDB hypertable configuration for time-series data
- Alembic migrations setup
- Development environment ready for data collection implementation

---

### Epic 2: Automated Weather Data Collection Pipeline

Automatically collect weather forecast predictions and real-world observations from multiple sources to enable accuracy analysis.

**User Outcome:** The system autonomously collects forecast data (AROME, Meteo-Parapente) 4x daily and observation data (ROMMA, FFVL beacons) 6x daily, storing it for analysis.

**FRs Covered:** FR1, FR2, FR4 (storage)

**Implementation Notes:**
- Modular collector architecture (BaseCollector interface, Strategy pattern)
- AROME collector (GRIB2 parsing with cfgrib/xarray)
- Meteo-Parapente collector (JSON API)
- ROMMA/FFVL beacon collectors (HTML scraping with BeautifulSoup4)
- APScheduler orchestration (4x/day forecasts, 6x/day observations)
- TimescaleDB storage with deviation-only model (100x storage reduction)
- Error handling, retry logic, graceful degradation

---

### Epic 3: Forecast Accuracy Analysis Engine

Calculate deviations between forecasts and observations to quantify model accuracy and identify systematic biases.

**User Outcome:** The system automatically computes forecast errors, calculates statistical metrics (MAE), and identifies systematic biases for each model at each site.

**FRs Covered:** FR3, FR6 (partial - bias calculation)

**Implementation Notes:**
- Stateless deviation_engine.py (deviation = forecast_value - observed_value)
- Forecast-observation matching logic (timestamp, site, parameter, horizon)
- TimescaleDB continuous aggregates for precomputed MAE metrics
- Bias detection algorithms (systematic over/underestimation)
- 6-level data validation strategy implementation
- Automated alerts for aberrant values

---

### Epic 4: Model Comparison Web Visualization Platform

Provide paragliders with an intuitive web interface to visualize and compare forecast model accuracy for their flying sites.

**User Outcome:** Paragliders can consult a mobile-first web platform to see which forecast models are most accurate for specific sites, understand systematic biases, and make data-driven flight planning decisions.

**FRs Covered:** FR5, FR6 (visualization)

**Implementation Notes:**
- Solid.js frontend with 12 custom components
- Responsive design (mobile-first, Tailwind CSS, WCAG 2.1 AA)
- Pages: Home (site list), SiteDetail (model comparisons), About (methodology)
- D3.js custom time-series deviation charts
- API client with typed responses (frontend/src/lib/api.ts)
- VerdictHeader component (summary verdict per model)
- BiasIndicator component (visual +/- bias representation)
- ComparisonTable component (side-by-side model MAE)
- DeviationChart component (time-series visualization)
- Error states, loading states, accessibility features

---

## Epic 1: Platform Foundation & Infrastructure Setup

Establish the foundational technical infrastructure that enables the system to collect, store, and serve weather data.

### Story 1.1: Initialize Custom Project Structure

As a developer,
I want to initialize the custom project structure following the architecture specifications,
So that the codebase is organized correctly from the start and all team members follow consistent patterns.

**Acceptance Criteria:**

**Given** the architecture document specifies the project structure
**When** I initialize the project
**Then** the following directory structure is created:

```
meteo-score/
├── backend/
│   ├── collectors/
│   ├── core/
│   ├── api/routes/
│   ├── db/migrations/
│   ├── scheduler/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── lib/
│   │   └── styles/
└── [root config files]
```

**And** Python virtual environment is created with Python 3.11+
**And** Backend dependencies are installed (FastAPI, SQLAlchemy, Pydantic V2, pytest, etc.)
**And** Frontend is initialized with Solid.js TypeScript template
**And** Frontend dependencies are installed (Solid.js, @solidjs/router, Tailwind CSS 4.0, D3.js, Geist fonts)
**And** `.env.example` file is created with all required environment variables documented
**And** `.gitignore` file is created excluding venv/, node_modules/, .env, __pycache__/
**And** `README.md` is created with project overview and setup instructions
**And** All linting tools are configured (ruff, black, mypy for backend; ESLint, Prettier for frontend)

### Story 1.2: Setup Docker Compose Infrastructure

As a developer,
I want to setup Docker Compose with all required services,
So that the development environment has parity with production and all services can run locally.

**Acceptance Criteria:**

**Given** the architecture specifies self-hosted infrastructure with Docker Compose
**When** I run `docker-compose up`
**Then** all required services start successfully:

- PostgreSQL 15 container running on port 5432
- Backend FastAPI container running on port 8000
- Frontend Vite dev server container running on port 3000
- Traefik reverse proxy container running on ports 80/443
- Adminer database UI container running on port 8080

**And** Docker Compose configuration includes:
- Service definitions for all 5 containers
- Network configuration for inter-service communication
- Volume mounts for persistent data (PostgreSQL data, backend code, frontend code)
- Environment variables loaded from `.env` file
- Health checks for each service
- Restart policies (restart: unless-stopped)

**And** Traefik is configured with:
- Automatic HTTPS via Let's Encrypt (staging for dev)
- Routing rules for backend API (/api/*)
- Routing rules for frontend (/)
- Dashboard enabled for debugging

**And** `.env` file contains all required variables:
- DATABASE_URL with PostgreSQL connection string
- POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
- API_BASE_URL, FRONTEND_URL
- Environment flag (development/production)

**And** Services can communicate:
- Backend can connect to PostgreSQL
- Frontend can reach backend API
- All services resolve via Docker network

**And** Documentation is updated with Docker Compose commands (up, down, logs, exec)

### Story 1.3: Configure TimescaleDB with Hypertables

As a developer,
I want to configure TimescaleDB extension and create hypertables for time-series data,
So that the database is optimized for storing and querying historical weather deviation data.

**Acceptance Criteria:**

**Given** PostgreSQL 15 is running in Docker
**When** I initialize the database
**Then** TimescaleDB 2.13+ extension is installed and enabled

**And** the following database tables are created:

**Sites table** (reference data):
```sql
sites (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  latitude DECIMAL(9,6) NOT NULL,
  longitude DECIMAL(9,6) NOT NULL,
  altitude INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
)
```

**Models table** (reference data):
```sql
models (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  source VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
)
```

**Parameters table** (reference data):
```sql
parameters (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  unit VARCHAR(50) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
)
```

**Deviations table** (time-series hypertable):
```sql
deviations (
  timestamp TIMESTAMPTZ NOT NULL,
  site_id INTEGER NOT NULL REFERENCES sites(id),
  model_id INTEGER NOT NULL REFERENCES models(id),
  parameter_id INTEGER NOT NULL REFERENCES parameters(id),
  horizon INTEGER NOT NULL,
  forecast_value DECIMAL(10,2) NOT NULL,
  observed_value DECIMAL(10,2) NOT NULL,
  deviation DECIMAL(10,2) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (timestamp, site_id, model_id, parameter_id, horizon)
)
```

**And** `deviations` table is converted to hypertable:
```sql
SELECT create_hypertable('deviations', 'timestamp',
  chunk_time_interval => INTERVAL '7 days');
```

**And** appropriate indexes are created:
- `idx_deviations_site_model` on (site_id, model_id)
- `idx_deviations_parameter` on (parameter_id)
- `idx_deviations_timestamp` on (timestamp DESC)

**And** Alembic migrations are configured:
- `alembic init` completed in `backend/db/migrations/`
- Initial migration file created for schema
- TimescaleDB-specific SQL in separate init script

**And** Database connection is verified from backend container using asyncpg driver

**And** Initial seed data is inserted:
- 1 site (Passy Plaine Joux)
- 2 models (AROME, Meteo-Parapente)
- 3 parameters (Wind Speed, Wind Direction, Temperature)

### Story 1.4: Setup Backend API Skeleton with FastAPI

As a developer,
I want to setup the FastAPI backend skeleton with core configuration and base structure,
So that the API foundation is ready for implementing business logic and routes.

**Acceptance Criteria:**

**Given** the project structure and Docker infrastructure are initialized
**When** I setup the backend API
**Then** the following core files are created:

**`backend/main.py`** - FastAPI application entry point:
- FastAPI app instance created
- CORS middleware configured for frontend origin
- Rate limiting middleware configured (100 req/min per IP)
- Router includes configured for `/api` prefix
- Application startup/shutdown events defined
- Health check endpoint `/health` returns 200 OK

**`backend/core/config.py`** - Configuration management:
- Pydantic Settings class for environment variables
- DATABASE_URL, API_BASE_URL, FRONTEND_URL loaded
- Environment-specific settings (development/production)
- All configuration validated on startup

**`backend/core/database.py`** - Database connection:
- AsyncEngine configured with asyncpg driver
- AsyncSessionLocal factory created
- `get_db()` dependency for FastAPI routes
- Connection pool configured (min 5, max 20 connections)

**`backend/core/models.py`** - SQLAlchemy models:
- Base declarative class
- Site, Model, Parameter, Deviation ORM models
- Relationships defined between models
- Models match database schema from Story 1.3

**`backend/core/schemas.py`** - Pydantic response schemas:
- SiteResponse with Field(alias="siteId") for camelCase mapping
- ModelResponse with Field(alias="modelId")
- ParameterResponse with Field(alias="parameterId")
- DeviationResponse with all camelCase field aliases
- Config class with `populate_by_name = True`

**`backend/api/routes/`** - Initial API routes structure:
- `__init__.py` with APIRouter aggregation
- Empty route files created (sites.py, models.py, parameters.py, deviations.py, bias_summary.py)

**And** API responds correctly:
- GET `/health` returns `{"status": "healthy"}`
- GET `/api/sites` returns empty list `{"data": [], "meta": {"total": 0}}`
- All endpoints follow standardized response format `{data, meta}`

**And** Type hints are complete on all functions and classes

**And** Async patterns are used correctly:
- All route handlers are async functions
- Database queries use `await session.execute()`
- No synchronous blocking operations

**And** Backend can be started with `uvicorn main:app --reload` on port 8000

### Story 1.5: Setup Frontend Application with Solid.js

As a developer,
I want to setup the Solid.js frontend application with routing and base components,
So that the UI foundation is ready for implementing weather data visualizations.

**Acceptance Criteria:**

**Given** the project structure and Docker infrastructure are initialized
**When** I setup the frontend application
**Then** the following core files are created:

**`frontend/src/index.tsx`** - Application entry point:
- Solid.js app mounted to root element
- Router provider wrapping entire app
- Global styles imported

**`frontend/src/App.tsx`** - Root component:
- @solidjs/router Routes configured
- Route definitions for Home (/), SiteDetail (/sites/:id), About (/about)
- ErrorBoundary for global error handling
- Navigation header component included

**`frontend/src/pages/Home.tsx`** - Home page:
- Placeholder content "MétéoScore - Home"
- Basic layout structure
- Ready for site list implementation

**`frontend/src/pages/SiteDetail.tsx`** - Site detail page:
- useParams() to extract site ID from route
- Placeholder content showing site ID
- Ready for model comparison implementation

**`frontend/src/pages/About.tsx`** - About page:
- Placeholder content "About MétéoScore"
- Ready for methodology documentation

**`frontend/src/components/Navigation.tsx`** - Navigation header:
- Links to Home, About using `<A>` component from @solidjs/router
- Mobile-responsive layout with Tailwind CSS
- Logo/title "MétéoScore"

**`frontend/src/lib/api.ts`** - API client:
- Base API_URL from environment variable
- Typed fetch wrapper function
- Standard error handling
- Response type definitions matching backend schemas

**`frontend/src/lib/types.ts`** - TypeScript types:
- Site, Model, Parameter, Deviation interfaces
- All fields in camelCase matching API responses
- ApiResponse<T> generic wrapper type

**`frontend/tailwind.config.js`** - Tailwind configuration:
- Responsive breakpoints (320px, 768px, 1280px)
- Geist fonts configured
- Custom color palette defined
- Mobile-first utilities enabled

**`frontend/vite.config.ts`** - Vite configuration:
- vite-plugin-solid configured
- API proxy to backend on /api routes
- Environment variables loaded
- Build optimization settings

**And** Frontend styling is configured:
- Tailwind CSS directives in `src/styles/index.css`
- Geist Sans and Geist Mono fonts loaded
- Base responsive styles applied

**And** Frontend can be started with `npm run dev` on port 3000

**And** All pages are accessible:
- Navigation to / shows Home page
- Navigation to /about shows About page
- Navigation to /sites/1 shows SiteDetail page with ID

**And** API integration is ready:
- Frontend can call backend `/api/health` endpoint
- CORS is working between frontend and backend
- Type safety is enforced with TypeScript strict mode

---

## Epic 2: Automated Weather Data Collection Pipeline

Automatically collect weather forecast predictions and real-world observations from multiple sources to enable accuracy analysis.

### Story 2.1: Implement BaseCollector Interface and Core Data Models

As a developer,
I want to create the BaseCollector abstract interface and core data models for the collector architecture,
So that all weather data collectors follow a consistent pattern and can be orchestrated uniformly.

**Acceptance Criteria:**

**Given** the architecture specifies modular collectors using Strategy pattern
**When** I implement the base collector infrastructure
**Then** the following is created:

**`backend/collectors/base.py`** - BaseCollector abstract class:
```python
class BaseCollector(ABC):
    @abstractmethod
    async def collect_forecast(
        self,
        site_id: int,
        forecast_run: datetime
    ) -> List[ForecastData]:
        pass

    @abstractmethod
    async def collect_observation(
        self,
        site_id: int,
        observation_time: datetime
    ) -> List[ObservationData]:
        pass
```

**`backend/core/data_models.py`** - Data transfer objects:
```python
@dataclass
class ForecastData:
    site_id: int
    model_id: int
    parameter_id: int
    forecast_run: datetime
    valid_time: datetime
    horizon: int  # hours ahead
    value: Decimal

@dataclass
class ObservationData:
    site_id: int
    parameter_id: int
    observation_time: datetime
    value: Decimal
```

**And** `backend/core/deviation_engine.py` - Stateless deviation calculator:
```python
def calculate_deviation(
    forecast: ForecastData,
    observation: ObservationData
) -> Decimal:
    """Returns forecast_value - observed_value"""
    return forecast.value - observation.value
```

**And** Common collector utilities are created in `backend/collectors/utils.py`:
- Exponential backoff retry decorator with configurable max_retries
- HTTP client wrapper with timeout and error handling
- Date/time parsing utilities for various formats

**And** All functions have complete type hints

**And** Unit tests are created in `backend/tests/test_base_collector.py`:
- Test deviation calculation with various inputs
- Test retry logic with mock failures
- Test data model validation

**And** Test coverage is >80% for all new code

### Story 2.2: Implement Meteo-Parapente Forecast Collector with TDD

As a developer,
I want to implement the Meteo-Parapente forecast collector using TDD approach,
So that the system can automatically retrieve forecast data from Meteo-Parapente API with validated parsing logic.

**Acceptance Criteria:**

**Given** the BaseCollector interface is defined
**When** I implement the Meteo-Parapente collector using TDD
**Then** unit tests are written FIRST in `backend/tests/test_collectors.py`:

- Test parsing valid JSON response from Meteo-Parapente API
- Test extracting wind speed, wind direction, temperature
- Test handling missing data fields gracefully
- Test handling malformed JSON responses
- Test API rate limiting (50 req/min respected)
- Test forecast horizon calculation (H+0, H+6, H+12, etc.)

**And** `backend/collectors/meteo_parapente.py` is implemented:
```python
class MeteoParapenteCollector(BaseCollector):
    API_ENDPOINT = "https://api.meteo-parapente.com/..."
    MAX_RETRIES = 3

    async def collect_forecast(
        self,
        site_id: int,
        forecast_run: datetime
    ) -> List[ForecastData]:
        # Implementation with requests library
        # Parse JSON response
        # Extract wind speed, direction, temperature
        # Return List[ForecastData]
```

**And** the collector handles API responses correctly:
- Parses JSON forecast data
- Extracts parameters: wind speed (km/h), wind direction (degrees), temperature (°C)
- Calculates forecast horizons (0h, 6h, 12h, 18h, 24h, etc.)
- Maps site coordinates to Meteo-Parapente location IDs

**And** error handling is implemented:
- HTTP errors return empty list and log warning
- JSON parsing errors are caught and logged
- Invalid data values are skipped with warning
- Retry logic with exponential backoff (3 attempts max)

**And** the collector respects API constraints:
- Rate limiting: Maximum 50 requests per minute
- Timeout: 10 seconds per request
- User-Agent header identifies MétéoScore

**And** all tests pass with >80% coverage

**And** manual validation is performed:
- Collect forecast for Passy site
- Verify values are reasonable (wind 0-200 km/h, temp -50 to 50°C)
- Log sample data for human review (Level 1 validation strategy)

### Story 2.3: Implement AROME Forecast Collector (GRIB2 Parsing)

As a developer,
I want to implement the AROME forecast collector with GRIB2 file parsing,
So that the system can automatically retrieve and parse AROME forecast data from Météo-France.

**Acceptance Criteria:**

**Given** the BaseCollector interface is defined
**When** I implement the AROME collector with TDD
**Then** unit tests are written FIRST in `backend/tests/test_collectors.py`:

- Test GRIB2 file download from Météo-France API
- Test parsing GRIB2 with cfgrib and xarray
- Test extracting wind U/V components and converting to speed/direction
- Test extracting temperature at specific altitude
- Test handling missing GRIB2 fields
- Test coordinate interpolation to site location

**And** `backend/collectors/arome.py` is implemented:
```python
class AROMECollector(BaseCollector):
    API_ENDPOINT = "https://public-api.meteofrance.fr/..."
    MAX_RETRIES = 3

    async def collect_forecast(
        self,
        site_id: int,
        forecast_run: datetime
    ) -> List[ForecastData]:
        # Download GRIB2 file
        # Parse with cfgrib + xarray
        # Extract wind U/V components, temperature
        # Interpolate to site coordinates
        # Return List[ForecastData]
```

**And** GRIB2 parsing is implemented correctly:
- Uses cfgrib library to read GRIB2 binary format
- Uses xarray for data manipulation
- Extracts wind U and V components from GRIB2
- Converts U/V to wind speed and direction:
  - `speed = sqrt(u² + v²)`
  - `direction = atan2(u, v) * 180/π`
- Extracts temperature at site altitude level
- Interpolates grid data to site coordinates (latitude, longitude)

**And** API integration follows specifications:
- Uses Météo-France public API (free since 2024)
- Respects rate limit: 50 requests per minute
- Downloads GRIB2 files for forecast runs (00h, 06h, 12h, 18h UTC)
- Extracts forecast horizons: H+0 to H+48 (every 1-3 hours)

**And** error handling is implemented:
- GRIB2 download failures retry with exponential backoff
- Corrupted GRIB2 files are detected and logged
- Missing parameters skip gracefully with warning
- Invalid coordinate interpolation returns null with warning

**And** data validation is performed:
- Wind speed: 0-200 km/h (values outside flagged as aberrant)
- Wind direction: 0-360 degrees
- Temperature: -50 to +50°C (values outside flagged as aberrant)
- All aberrant values logged for Level 3 validation

**And** all tests pass with >80% coverage

**And** manual validation is performed:
- Download and parse real AROME GRIB2 file
- Extract data for Passy coordinates
- Verify values match expected AROME output
- Compare with Météo-France website for sanity check

### Story 2.4: Implement ROMMA Observation Collector (Beacon Scraping)

As a developer,
I want to implement the ROMMA observation collector with HTML scraping,
So that the system can automatically retrieve real-world weather observations from ROMMA beacons.

**Acceptance Criteria:**

**Given** the BaseCollector interface is defined
**When** I implement the ROMMA collector with TDD
**Then** unit tests are written FIRST in `backend/tests/test_collectors.py`:

- Test HTML parsing from ROMMA beacon pages
- Test extracting wind speed, wind direction, temperature
- Test handling missing HTML elements gracefully
- Test handling malformed HTML
- Test identifying correct beacon for site coordinates
- Test handling beacon offline/unavailable scenarios

**And** `backend/collectors/romma.py` is implemented:
```python
class ROMMaCollector(BaseCollector):
    BASE_URL = "http://romma.fr/..."
    MAX_RETRIES = 3

    async def collect_observation(
        self,
        site_id: int,
        observation_time: datetime
    ) -> List[ObservationData]:
        # Scrape ROMMA beacon HTML
        # Parse with BeautifulSoup4
        # Extract wind speed, direction, temperature
        # Return List[ObservationData]
```

**And** HTML scraping is implemented correctly:
- Uses requests library to fetch beacon HTML page
- Uses BeautifulSoup4 to parse HTML structure
- Identifies correct beacon station for site (by proximity to coordinates)
- Extracts current observations from HTML table/divs:
  - Wind speed (km/h)
  - Wind direction (degrees or cardinal N/S/E/W)
  - Temperature (°C)
- Parses observation timestamp from HTML

**And** data parsing handles variations:
- Cardinal directions converted to degrees (N=0, E=90, S=180, W=270)
- Various HTML table formats handled
- Missing data fields return None (not crash)
- Non-numeric values are detected and logged as errors

**And** error handling is implemented:
- HTTP 404/500 errors logged and return empty list
- HTML parsing errors caught and logged
- Beacon offline detection (no recent data) logged as warning
- Retry logic with exponential backoff (3 attempts max)

**And** scraping respects beacon servers:
- Polite delays between requests (minimum 2 seconds)
- User-Agent header identifies MétéoScore
- No excessive requests (6x daily maximum per beacon)
- Caching to avoid duplicate requests within 10 minutes

**And** data validation is performed:
- Wind speed: 0-200 km/h (aberrant values flagged)
- Wind direction: 0-360 degrees
- Temperature: -50 to +50°C (aberrant values flagged)
- Observation timestamp within last 2 hours (else considered stale)

**And** all tests pass with >80% coverage

**And** manual validation is performed:
- Scrape live ROMMA beacon for Passy area
- Verify extracted values match website display
- Compare with multiple beacons if available (Level 4 cross-validation)
- Log sample data for human review

### Story 2.5: Implement FFVL Observation Collector (Beacon Scraping)

As a developer,
I want to implement the FFVL observation collector with HTML scraping,
So that the system can automatically retrieve real-world weather observations from FFVL beacons for cross-validation.

**Acceptance Criteria:**

**Given** the BaseCollector interface is defined
**When** I implement the FFVL collector with TDD
**Then** unit tests are written FIRST in `backend/tests/test_collectors.py`:

- Test HTML parsing from FFVL beacon pages
- Test extracting wind speed, wind direction, temperature
- Test handling different FFVL beacon HTML structures
- Test handling missing HTML elements gracefully
- Test identifying correct FFVL beacon for site
- Test handling beacon offline/unavailable scenarios

**And** `backend/collectors/ffvl.py` is implemented:
```python
class FFVLCollector(BaseCollector):
    BASE_URL = "https://data.ffvl.fr/..."
    MAX_RETRIES = 3

    async def collect_observation(
        self,
        site_id: int,
        observation_time: datetime
    ) -> List[ObservationData]:
        # Scrape FFVL beacon HTML
        # Parse with BeautifulSoup4
        # Extract wind speed, direction, temperature
        # Return List[ObservationData]
```

**And** HTML scraping is implemented correctly:
- Uses requests library to fetch FFVL beacon HTML page
- Uses BeautifulSoup4 to parse HTML structure
- Identifies correct FFVL beacon for site (by name or proximity)
- Extracts current observations from HTML:
  - Wind speed (km/h or m/s - convert to km/h if needed)
  - Wind direction (degrees or cardinal)
  - Temperature (°C)
- Parses observation timestamp from page

**And** data parsing handles FFVL variations:
- Multiple HTML table formats supported (FFVL structure varies by beacon)
- Cardinal directions converted to degrees
- Units conversion: m/s to km/h (multiply by 3.6)
- Missing data fields return None gracefully
- Non-numeric values detected and logged

**And** error handling is implemented:
- HTTP errors logged and return empty list
- HTML parsing errors caught and logged
- Beacon offline/no recent data logged as warning
- Retry logic with exponential backoff (3 attempts max)

**And** scraping respects FFVL servers:
- Polite delays between requests (minimum 2 seconds)
- User-Agent header identifies MétéoScore
- Maximum 6x daily requests per beacon
- Caching to avoid duplicate requests within 10 minutes

**And** data validation is performed:
- Wind speed: 0-200 km/h (aberrant values flagged)
- Wind direction: 0-360 degrees
- Temperature: -50 to +50°C (aberrant values flagged)
- Observation timestamp within last 2 hours (else considered stale)

**And** cross-validation with ROMMA is logged:
- When both ROMMA and FFVL data available for same site
- Log differences between sources
- Flag significant discrepancies (>20% difference) for review
- Implements Level 4 validation strategy (cross-validation)

**And** all tests pass with >80% coverage

**And** manual validation is performed:
- Scrape live FFVL beacon for Passy area
- Verify extracted values match FFVL website display
- Compare FFVL vs ROMMA observations if both available
- Log sample data for human review

### Story 2.6: Setup APScheduler for Automated Collection

As a developer,
I want to setup APScheduler to orchestrate automated data collection from all sources,
So that forecasts and observations are collected automatically without manual intervention.

**Acceptance Criteria:**

**Given** all collectors are implemented (Meteo-Parapente, AROME, ROMMA, FFVL)
**When** I setup the scheduler
**Then** `backend/scheduler/jobs.py` is created with scheduled jobs:

**Forecast collection jobs (4x daily):**
- Job runs at 00:00, 06:00, 12:00, 18:00 UTC (CronTrigger)
- Collects from Meteo-Parapente for all configured sites
- Collects from AROME for all configured sites
- Stores forecast data in database (deviations table with forecast_value, observed_value as NULL initially)

**Observation collection jobs (6x daily):**
- Job runs at 08:00, 10:00, 12:00, 14:00, 16:00, 18:00 local time (CronTrigger)
- Collects from ROMMA beacons for all configured sites
- Collects from FFVL beacons for all configured sites
- Stores observation data in database

**Deviation calculation job:**
- Triggered after observation collection
- Matches observations with forecasts by (timestamp, site_id, parameter_id, horizon)
- Calls `deviation_engine.calculate_deviation()` for each match
- Updates deviations table with observed_value and deviation

**And** `backend/scheduler/scheduler.py` is created:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Add forecast collection jobs
scheduler.add_job(
    collect_all_forecasts,
    CronTrigger(hour='0,6,12,18'),
    id='collect_forecasts'
)

# Add observation collection jobs
scheduler.add_job(
    collect_all_observations,
    CronTrigger(hour='8,10,12,14,16,18'),
    id='collect_observations'
)

# Add deviation calculation job
scheduler.add_job(
    calculate_all_deviations,
    CronTrigger(hour='8,10,12,14,16,18', minute=30),
    id='calculate_deviations'
)
```

**And** scheduler is integrated with FastAPI in `backend/main.py`:
- Scheduler starts on FastAPI startup event
- Scheduler shuts down gracefully on FastAPI shutdown event
- Scheduler runs in background without blocking API

**And** job execution is logged:
- Start time, end time, duration logged for each job
- Success/failure status logged
- Number of records collected/processed logged
- Errors during collection logged with full traceback

**And** idempotency is ensured:
- Duplicate forecast/observation data is detected (same timestamp, site, model, parameter)
- Duplicates are skipped (not inserted twice)
- Database primary key constraint prevents duplicates

**And** job configuration is flexible:
- Schedule intervals configurable via environment variables
- Sites to collect for configurable in database
- Jobs can be manually triggered for testing

**And** scheduler health monitoring:
- `/api/scheduler/status` endpoint returns last job execution times
- `/api/scheduler/jobs` endpoint lists all scheduled jobs
- Missed jobs are logged and can trigger alerts

**And** manual testing is performed:
- Run forecast collection job manually and verify database inserts
- Run observation collection job manually and verify database inserts
- Run deviation calculation job and verify deviations are computed
- Verify scheduler runs jobs at correct times (test with shorter intervals)

### Story 2.7: Implement Error Handling, Retry Logic, and Data Validation

As a developer,
I want to implement comprehensive error handling, retry logic, and data validation across all collectors,
So that the data collection pipeline is resilient to failures and data quality is maintained.

**Acceptance Criteria:**

**Given** all collectors and scheduler are implemented
**When** I implement error handling and validation
**Then** the following error handling is in place:

**Retry logic with exponential backoff:**
- Decorator in `backend/collectors/utils.py`:
  ```python
  @retry_with_backoff(max_retries=3, base_delay=1.0)
  async def fetch_with_retry(...):
      # Attempts: 1s, 2s, 4s delays between retries
  ```
- Applied to all external API calls and HTTP requests
- Logs each retry attempt with reason for failure
- After max retries, raises exception and logs error

**Graceful degradation:**
- Collection failure for one source doesn't crash entire pipeline
- Other collectors continue running if one fails
- Missing data handled without blocking downstream processes
- Partial data is better than no data (collect what's available)

**Automated alerts for aberrant values (Level 3 validation):**
- `backend/core/validation.py` with validation rules:
  - Wind speed: Flag if >200 km/h or <0 km/h
  - Temperature: Flag if >50°C or <-50°C
  - Deviation: Flag if >100 (forecast drastically wrong)
- Aberrant values are logged with WARNING level
- Aberrant values are still stored but marked with `is_aberrant` flag
- Daily summary email sent if aberrant values exceed threshold

**Circuit breaker pattern for external APIs:**
- If API fails 5 times consecutively, circuit opens (stops requests)
- Circuit stays open for 5 minutes (cooldown period)
- After cooldown, circuit half-opens (test with single request)
- If test succeeds, circuit closes (resume normal operation)
- Prevents hammering failing APIs

**Data validation pipeline:**
```python
class DataValidator:
    @staticmethod
    def validate_forecast(data: ForecastData) -> ValidationResult:
        # Check value ranges
        # Check timestamp validity
        # Check required fields present

    @staticmethod
    def validate_observation(data: ObservationData) -> ValidationResult:
        # Check value ranges
        # Check timestamp recency
        # Check required fields present
```

**And** logging is comprehensive:
- Python logging module with structured logs
- Log levels: INFO (normal operations), WARNING (retries, aberrant values), ERROR (failures), CRITICAL (pipeline crash)
- Logs include: timestamp, collector name, site_id, error details, retry count
- Logs output to stdout → Docker logs for monitoring

**And** monitoring metrics are exposed:
- Collection success rate per collector
- Average collection duration per collector
- Number of aberrant values detected per day
- API rate limit status per source
- Database write success rate

**And** the 6-level validation strategy is documented:
1. **Manual validation** - Human review of initial samples ✓
2. **Unit tests** - TDD approach with >80% coverage ✓
3. **Automated alerts** - Aberrant value flagging ✓ (this story)
4. **Cross-validation** - ROMMA vs FFVL comparison ✓ (Story 2.5)
5. **Historical comparison** - Statistical outlier detection (deferred to Epic 3)
6. **Ship-and-iterate** - Deploy cautiously, allow error correction (ongoing)

**And** error recovery is tested:
- Simulate API downtime and verify retry logic works
- Simulate malformed responses and verify graceful handling
- Simulate database connection loss and verify recovery
- Verify pipeline continues after individual collector failure

**And** all tests pass with >80% coverage for error handling code

---

## Epic 3: Forecast Accuracy Analysis Engine

**Goal:** Calculate forecast deviations and quantify model accuracy with statistical metrics

**User Outcome:** System automatically computes forecast accuracy metrics (MAE, bias) from collected data, enabling objective model comparisons

**FRs Covered:**
- FR3: Deviation Calculation Engine ✅
- FR6: Contextual Bias Characterization (partial - bias calculation) ✅

**Dependencies:**
- Epic 1 (database setup) ✅
- Epic 2 (data collection pipeline) ✅

**Stories:** 6

---

### Story 3.1: Forecast-Observation Matching Engine

**As a** data analyst,
**I want** to automatically match forecast predictions with actual observations,
**So that** I can calculate deviations between predicted and observed weather parameters.

#### Acceptance Criteria:

**Given** forecasts and observations are stored in the database
**When** the matching engine runs
**Then** forecast-observation pairs are created with the following matching rules:

**Matching Logic:**
- **Temporal matching**: Observation timestamp within ±30 minutes of forecast valid_time
- **Spatial matching**: Exact site_id match
- **Parameter matching**: Exact parameter_id match (wind_speed, wind_direction, temperature)
- **Horizon matching**: Calculate horizon = forecast.valid_time - forecast.forecast_run

**And** matched pairs are stored in staging table:

```sql
CREATE TABLE forecast_observation_pairs (
  id SERIAL PRIMARY KEY,
  forecast_id INTEGER NOT NULL REFERENCES forecasts(id),
  observation_id INTEGER NOT NULL REFERENCES observations(id),
  site_id INTEGER NOT NULL REFERENCES sites(id),
  model_id INTEGER NOT NULL REFERENCES models(id),
  parameter_id INTEGER NOT NULL REFERENCES parameters(id),
  forecast_run TIMESTAMPTZ NOT NULL,
  valid_time TIMESTAMPTZ NOT NULL,
  horizon INTEGER NOT NULL, -- hours between forecast_run and valid_time
  forecast_value DECIMAL(10,2) NOT NULL,
  observed_value DECIMAL(10,2) NOT NULL,
  time_diff_minutes INTEGER NOT NULL, -- actual time difference for quality tracking
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(forecast_id, observation_id)
);

CREATE INDEX idx_pairs_site_model_param ON forecast_observation_pairs(site_id, model_id, parameter_id);
CREATE INDEX idx_pairs_valid_time ON forecast_observation_pairs(valid_time);
CREATE INDEX idx_pairs_horizon ON forecast_observation_pairs(horizon);
```

**And** matching service implements this async method:

```python
# backend/app/services/matching_service.py
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Forecast, Observation, ForecastObservationPair

class MatchingService:
    TIME_TOLERANCE_MINUTES = 30

    async def match_forecasts_to_observations(
        self,
        db: AsyncSession,
        site_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[ForecastObservationPair]:
        """
        Match forecasts with observations within time tolerance.

        Returns list of created forecast-observation pairs.
        """
        # Query forecasts in date range
        # Query observations in date range ± TIME_TOLERANCE_MINUTES
        # Match by site_id, parameter_id, valid_time ± tolerance
        # Calculate horizon = valid_time - forecast_run (in hours)
        # Create ForecastObservationPair records
        # Return list of pairs
        pass
```

**And** unit tests cover:
- ✅ Exact time match (observation at forecast.valid_time)
- ✅ Time tolerance boundaries (±29 min = match, ±31 min = no match)
- ✅ Multiple observations within tolerance (select closest)
- ✅ Missing observation (no pair created)
- ✅ Multiple forecasts for same valid_time (all matched)
- ✅ Horizon calculation accuracy (6h, 12h, 24h, 48h forecasts)

**And** test coverage >80%

**Technical Notes:**
- Use SQLAlchemy async queries with JOIN operations
- Implement efficient batch processing (process 1000 pairs at a time)
- Log unmatched forecasts/observations for monitoring
- Idempotent: re-running matching doesn't create duplicates (UNIQUE constraint)

**Definition of Done:**
- [ ] Migration creates `forecast_observation_pairs` table
- [ ] `MatchingService` class implements matching logic
- [ ] Unit tests written FIRST (TDD) with >80% coverage
- [ ] All tests passing
- [ ] Manual test: Run matching on sample data, verify pairs created correctly

---

### Story 3.2: Deviation Calculation Logic

**As a** data analyst,
**I want** to calculate deviations between forecast and observed values,
**So that** I can quantify forecast errors and store them for analysis.

#### Acceptance Criteria:

**Given** forecast-observation pairs exist in the staging table
**When** the deviation calculation service runs
**Then** deviations are calculated and stored in the hypertable

**Deviation Calculation:**

```python
deviation = observed_value - forecast_value
```

**Sign Convention:**
- Positive deviation: forecast underestimated (observed > forecast)
- Negative deviation: forecast overestimated (observed < forecast)

**And** results are stored in the `deviations` hypertable:

```python
# backend/app/services/deviation_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ForecastObservationPair, Deviation

class DeviationService:
    async def calculate_deviations(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """
        Calculate deviations from forecast-observation pairs.

        Returns count of deviations created.
        """
        # Query unprocessed pairs from staging table
        # For each pair:
        #   deviation = observed_value - forecast_value
        #   Create Deviation record
        # Bulk insert into deviations hypertable
        # Mark pairs as processed (or delete from staging)
        # Return count
        pass
```

**And** the deviation record includes all context:

```python
# app/models/deviation.py
from sqlalchemy import Column, Integer, DECIMAL, TIMESTAMP, ForeignKey
from app.db.base import Base

class Deviation(Base):
    __tablename__ = 'deviations'

    timestamp = Column(TIMESTAMP(timezone=True), primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), primary_key=True)
    model_id = Column(Integer, ForeignKey('models.id'), primary_key=True)
    parameter_id = Column(Integer, ForeignKey('parameters.id'), primary_key=True)
    horizon = Column(Integer, primary_key=True)  # forecast horizon in hours
    forecast_value = Column(DECIMAL(10, 2), nullable=False)
    observed_value = Column(DECIMAL(10, 2), nullable=False)
    deviation = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default='NOW()')
```

**And** edge cases are handled:

1. **Outlier Detection:**
   - Wind speed deviation > 50 km/h → flag as potential outlier (log warning)
   - Temperature deviation > 15°C → flag as potential outlier
   - Wind direction deviation > 180° → calculate shortest angular distance

2. **Wind Direction Special Case:**
   ```python
   def calculate_wind_direction_deviation(forecast_deg: float, observed_deg: float) -> float:
       """Calculate shortest angular distance for wind direction."""
       diff = observed_deg - forecast_deg
       # Normalize to [-180, 180]
       if diff > 180:
           diff -= 360
       elif diff < -180:
           diff += 360
       return diff
   ```

3. **Missing Data Handling:**
   - If forecast_value or observed_value is NULL → skip pair, log warning
   - If pair already processed → skip (idempotent)

**And** unit tests cover:
- ✅ Basic deviation calculation (forecast=20, observed=25 → deviation=+5)
- ✅ Overestimation (forecast=30, observed=20 → deviation=-10)
- ✅ Wind direction angular distance (forecast=350°, observed=10° → deviation=+20°, not +20° or -340°)
- ✅ Outlier detection (deviation > threshold → logged)
- ✅ Bulk insert performance (1000+ deviations in <2 seconds)
- ✅ Idempotency (re-running doesn't duplicate deviations)

**And** test coverage >80%

**Definition of Done:**
- [ ] `DeviationService` class implements calculation logic
- [ ] Wind direction angular distance calculation correct
- [ ] Unit tests written FIRST (TDD) with >80% coverage
- [ ] All tests passing
- [ ] Manual test: Calculate deviations from sample pairs, verify results in database

---

### Story 3.3: Statistical Metrics Calculator (MAE, Bias)

**As a** data analyst,
**I want** to calculate statistical accuracy metrics (MAE, bias, confidence intervals),
**So that** I can objectively compare forecast model performance.

#### Acceptance Criteria:

**Given** deviations are stored in the hypertable
**When** the metrics calculator runs
**Then** MAE and bias are calculated per model/site/parameter/horizon combination

**Mean Absolute Error (MAE):**

```python
MAE = mean(abs(deviation))
```

**Bias (Systematic Error):**

```python
bias = mean(deviation)
```

**Bias Interpretation:**
- Positive bias: model systematically underestimates
- Negative bias: model systematically overestimates

**And** metrics service implements these calculations:

```python
# backend/app/services/metrics_service.py
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass

@dataclass
class AccuracyMetrics:
    model_id: int
    site_id: int
    parameter_id: int
    horizon: int
    mae: float
    bias: float
    sample_size: int
    confidence_level: str  # 'insufficient', 'preliminary', 'validated'
    std_dev: float
    min_deviation: float
    max_deviation: float

class MetricsService:
    PRELIMINARY_THRESHOLD = 30  # days
    VALIDATED_THRESHOLD = 90    # days

    async def calculate_accuracy_metrics(
        self,
        db: AsyncSession,
        model_id: int,
        site_id: int,
        parameter_id: int,
        horizon: int
    ) -> AccuracyMetrics:
        """
        Calculate MAE, bias, and confidence metrics.

        Returns AccuracyMetrics dataclass.
        """
        # Query deviations for model/site/parameter/horizon
        # Calculate: MAE = AVG(ABS(deviation))
        # Calculate: bias = AVG(deviation)
        # Calculate: std_dev = STDDEV(deviation)
        # Calculate: sample_size = COUNT(*)
        # Calculate: min/max deviations
        # Determine confidence_level based on sample_size
        # Return AccuracyMetrics
        pass

    def determine_confidence_level(self, sample_size: int) -> str:
        """Determine data confidence based on sample size."""
        if sample_size < self.PRELIMINARY_THRESHOLD:
            return 'insufficient'
        elif sample_size < self.VALIDATED_THRESHOLD:
            return 'preliminary'
        else:
            return 'validated'
```

**And** metrics are stored for efficient retrieval:

```sql
CREATE TABLE accuracy_metrics (
  id SERIAL PRIMARY KEY,
  model_id INTEGER NOT NULL REFERENCES models(id),
  site_id INTEGER NOT NULL REFERENCES sites(id),
  parameter_id INTEGER NOT NULL REFERENCES parameters(id),
  horizon INTEGER NOT NULL,
  mae DECIMAL(10, 2) NOT NULL,
  bias DECIMAL(10, 2) NOT NULL,
  std_dev DECIMAL(10, 2) NOT NULL,
  sample_size INTEGER NOT NULL,
  confidence_level VARCHAR(20) NOT NULL, -- 'insufficient', 'preliminary', 'validated'
  min_deviation DECIMAL(10, 2) NOT NULL,
  max_deviation DECIMAL(10, 2) NOT NULL,
  calculated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(model_id, site_id, parameter_id, horizon)
);

CREATE INDEX idx_metrics_site_param ON accuracy_metrics(site_id, parameter_id);
CREATE INDEX idx_metrics_confidence ON accuracy_metrics(confidence_level);
```

**And** statistical significance is calculated:

```python
def calculate_confidence_interval(
    bias: float,
    std_dev: float,
    sample_size: int,
    confidence: float = 0.95
) -> tuple[float, float]:
    """
    Calculate confidence interval for bias using t-distribution.

    Returns (lower_bound, upper_bound).
    """
    from scipy import stats

    # t-statistic for 95% confidence
    t_stat = stats.t.ppf((1 + confidence) / 2, sample_size - 1)

    # Standard error
    se = std_dev / (sample_size ** 0.5)

    # Confidence interval
    margin = t_stat * se
    return (bias - margin, bias + margin)
```

**And** unit tests cover:
- ✅ MAE calculation accuracy (sample deviations → correct MAE)
- ✅ Bias calculation (positive bias for underestimation, negative for overestimation)
- ✅ Confidence level thresholds (29 samples = insufficient, 31 = preliminary, 91 = validated)
- ✅ Confidence interval calculation (scipy t-distribution)
- ✅ Edge case: single sample (no std_dev calculation)
- ✅ Edge case: all deviations identical (std_dev = 0)

**And** test coverage >80%

**Definition of Done:**
- [ ] `MetricsService` class implements MAE, bias, confidence calculations
- [ ] Migration creates `accuracy_metrics` table
- [ ] Confidence interval calculation using scipy.stats
- [ ] Unit tests written FIRST (TDD) with >80% coverage
- [ ] All tests passing
- [ ] Manual test: Calculate metrics from sample deviations, verify against Excel/Python calculations

---

### Story 3.4: TimescaleDB Continuous Aggregates

**As a** developer,
**I want** to pre-compute rolling statistics using TimescaleDB continuous aggregates,
**So that** API queries return results instantly without scanning millions of deviation records.

#### Acceptance Criteria:

**Given** deviations are stored in the hypertable
**When** continuous aggregates are configured
**Then** daily, weekly, and monthly MAE/bias are automatically pre-computed

**Daily Aggregate:**

```sql
CREATE MATERIALIZED VIEW daily_accuracy_metrics
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 day', timestamp) AS bucket,
  site_id,
  model_id,
  parameter_id,
  horizon,
  AVG(ABS(deviation)) AS mae,
  AVG(deviation) AS bias,
  STDDEV(deviation) AS std_dev,
  COUNT(*) AS sample_size,
  MIN(deviation) AS min_deviation,
  MAX(deviation) AS max_deviation
FROM deviations
GROUP BY bucket, site_id, model_id, parameter_id, horizon
WITH NO DATA;

-- Refresh policy: update daily at 2 AM
SELECT add_continuous_aggregate_policy('daily_accuracy_metrics',
  start_offset => INTERVAL '3 days',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 day');
```

**Weekly Aggregate:**

```sql
CREATE MATERIALIZED VIEW weekly_accuracy_metrics
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('7 days', timestamp) AS bucket,
  site_id,
  model_id,
  parameter_id,
  horizon,
  AVG(ABS(deviation)) AS mae,
  AVG(deviation) AS bias,
  STDDEV(deviation) AS std_dev,
  COUNT(*) AS sample_size
FROM deviations
GROUP BY bucket, site_id, model_id, parameter_id, horizon
WITH NO DATA;

-- Refresh policy: update weekly on Sunday at 3 AM
SELECT add_continuous_aggregate_policy('weekly_accuracy_metrics',
  start_offset => INTERVAL '3 weeks',
  end_offset => INTERVAL '1 day',
  schedule_interval => INTERVAL '1 week');
```

**Monthly Aggregate:**

```sql
CREATE MATERIALIZED VIEW monthly_accuracy_metrics
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('30 days', timestamp) AS bucket,
  site_id,
  model_id,
  parameter_id,
  horizon,
  AVG(ABS(deviation)) AS mae,
  AVG(deviation) AS bias,
  STDDEV(deviation) AS std_dev,
  COUNT(*) AS sample_size
FROM deviations
GROUP BY bucket, site_id, model_id, parameter_id, horizon
WITH NO DATA;

-- Refresh policy: update monthly on 1st at 4 AM
SELECT add_continuous_aggregate_policy('monthly_accuracy_metrics',
  start_offset => INTERVAL '3 months',
  end_offset => INTERVAL '1 day',
  schedule_interval => INTERVAL '1 month');
```

**And** retention policies manage data growth:

```sql
-- Retain raw deviations for 1 year
SELECT add_retention_policy('deviations', INTERVAL '1 year');

-- Retain daily aggregates for 2 years
SELECT add_retention_policy('daily_accuracy_metrics', INTERVAL '2 years');

-- Retain weekly aggregates for 5 years
SELECT add_retention_policy('weekly_accuracy_metrics', INTERVAL '5 years');

-- Retain monthly aggregates indefinitely (no retention policy)
```

**And** aggregates are queryable via SQLAlchemy models:

```python
# app/models/aggregates.py
from sqlalchemy import Column, Integer, DECIMAL, TIMESTAMP
from app.db.base import Base

class DailyAccuracyMetric(Base):
    __tablename__ = 'daily_accuracy_metrics'

    bucket = Column(TIMESTAMP(timezone=True), primary_key=True)
    site_id = Column(Integer, primary_key=True)
    model_id = Column(Integer, primary_key=True)
    parameter_id = Column(Integer, primary_key=True)
    horizon = Column(Integer, primary_key=True)
    mae = Column(DECIMAL(10, 2))
    bias = Column(DECIMAL(10, 2))
    std_dev = Column(DECIMAL(10, 2))
    sample_size = Column(Integer)
    min_deviation = Column(DECIMAL(10, 2))
    max_deviation = Column(DECIMAL(10, 2))

# Similar models for WeeklyAccuracyMetric, MonthlyAccuracyMetric
```

**And** service methods use aggregates for fast queries:

```python
# backend/app/services/metrics_service.py
async def get_daily_metrics(
    self,
    db: AsyncSession,
    site_id: int,
    model_id: int,
    parameter_id: int,
    start_date: datetime,
    end_date: datetime
) -> List[DailyAccuracyMetric]:
    """Query pre-computed daily metrics (fast)."""
    # SELECT * FROM daily_accuracy_metrics
    # WHERE site_id = ? AND model_id = ? AND parameter_id = ?
    #   AND bucket BETWEEN start_date AND end_date
    # ORDER BY bucket
    pass
```

**And** performance benchmarks are met:
- Query 90 days of daily metrics: <100ms
- Query 12 months of weekly metrics: <50ms
- Query 3 years of monthly metrics: <30ms

**And** unit tests cover:
- ✅ Continuous aggregate refresh policies execute correctly
- ✅ Daily aggregate calculates MAE/bias matching raw query
- ✅ Retention policies don't delete recent data
- ✅ Query performance meets benchmarks

**And** test coverage >80%

**Definition of Done:**
- [ ] Migration creates continuous aggregates with refresh policies
- [ ] Retention policies configured
- [ ] SQLAlchemy models for aggregates
- [ ] Service methods query aggregates
- [ ] Unit tests written FIRST (TDD) with >80% coverage
- [ ] Performance benchmarks met
- [ ] All tests passing

---

### Story 3.5: Minimum Data Threshold Logic

**As a** user,
**I want** to see data confidence indicators based on sample size,
**So that** I know when accuracy metrics are reliable vs. preliminary.

#### Acceptance Criteria:

**Given** accuracy metrics are calculated
**When** the system evaluates sample size
**Then** confidence levels are assigned according to thresholds

**Confidence Level Rules:**

| Sample Size | Confidence Level | Label | UI Indicator |
|-------------|------------------|-------|--------------|
| < 30 days | `insufficient` | ⚠️ Insufficient Data | Red badge |
| 30-89 days | `preliminary` | 🔶 Preliminary | Orange badge |
| ≥ 90 days | `validated` | ✅ Validated | Green badge |

**And** confidence logic is implemented:

```python
# backend/app/services/confidence_service.py
from enum import Enum
from dataclasses import dataclass

class ConfidenceLevel(str, Enum):
    INSUFFICIENT = 'insufficient'
    PRELIMINARY = 'preliminary'
    VALIDATED = 'validated'

@dataclass
class ConfidenceMetadata:
    level: ConfidenceLevel
    sample_size: int
    days_of_data: int
    label: str
    ui_color: str
    show_warning: bool

class ConfidenceService:
    PRELIMINARY_THRESHOLD = 30  # days
    VALIDATED_THRESHOLD = 90    # days

    def evaluate_confidence(
        self,
        sample_size: int,
        earliest_timestamp: datetime,
        latest_timestamp: datetime
    ) -> ConfidenceMetadata:
        """
        Evaluate data confidence based on sample size and time range.

        Returns ConfidenceMetadata with level, label, and UI hints.
        """
        days_of_data = (latest_timestamp - earliest_timestamp).days

        if days_of_data < self.PRELIMINARY_THRESHOLD:
            return ConfidenceMetadata(
                level=ConfidenceLevel.INSUFFICIENT,
                sample_size=sample_size,
                days_of_data=days_of_data,
                label='⚠️ Insufficient Data',
                ui_color='red',
                show_warning=True
            )
        elif days_of_data < self.VALIDATED_THRESHOLD:
            return ConfidenceMetadata(
                level=ConfidenceLevel.PRELIMINARY,
                sample_size=sample_size,
                days_of_data=days_of_data,
                label='🔶 Preliminary',
                ui_color='orange',
                show_warning=True
            )
        else:
            return ConfidenceMetadata(
                level=ConfidenceLevel.VALIDATED,
                sample_size=sample_size,
                days_of_data=days_of_data,
                label='✅ Validated',
                ui_color='green',
                show_warning=False
            )
```

**And** API responses include confidence metadata:

```json
{
  "site_id": 1,
  "site_name": "Passy Plaine Joux",
  "model_id": 1,
  "model_name": "AROME",
  "parameter_id": 1,
  "parameter_name": "wind_speed",
  "horizon": 6,
  "metrics": {
    "mae": 4.2,
    "bias": -1.5,
    "std_dev": 3.8,
    "sample_size": 45
  },
  "confidence": {
    "level": "preliminary",
    "days_of_data": 45,
    "label": "🔶 Preliminary",
    "ui_color": "orange",
    "show_warning": true,
    "message": "Results based on 45 days of data. Metrics will stabilize after 90 days."
  }
}
```

**And** warning messages are contextual:

```python
def get_confidence_message(self, metadata: ConfidenceMetadata) -> str:
    """Generate user-friendly confidence warning."""
    if metadata.level == ConfidenceLevel.INSUFFICIENT:
        days_remaining = self.PRELIMINARY_THRESHOLD - metadata.days_of_data
        return (
            f"Insufficient data ({metadata.days_of_data} days). "
            f"Collect {days_remaining} more days to reach preliminary status."
        )
    elif metadata.level == ConfidenceLevel.PRELIMINARY:
        days_remaining = self.VALIDATED_THRESHOLD - metadata.days_of_data
        return (
            f"Results based on {metadata.days_of_data} days of data. "
            f"Metrics will stabilize after {days_remaining} more days."
        )
    else:
        return (
            f"Validated with {metadata.days_of_data} days of data. "
            f"These metrics are statistically reliable."
        )
```

**And** insufficient data prevents misleading conclusions:

```python
async def get_accuracy_metrics_with_confidence(
    self,
    db: AsyncSession,
    site_id: int,
    model_id: int,
    parameter_id: int,
    horizon: int
) -> Optional[Dict[str, Any]]:
    """
    Get accuracy metrics only if confidence threshold met.

    Returns None if insufficient data.
    """
    metrics = await self.calculate_accuracy_metrics(...)
    confidence = self.evaluate_confidence(...)

    # Option 1: Return None for insufficient data
    if confidence.level == ConfidenceLevel.INSUFFICIENT:
        return None

    # Option 2: Return with warning (preferred for transparency)
    return {
        'metrics': metrics,
        'confidence': confidence
    }
```

**And** unit tests cover:
- ✅ 29 days → insufficient
- ✅ 30 days → preliminary
- ✅ 89 days → preliminary
- ✅ 90 days → validated
- ✅ Warning message generation
- ✅ API response includes confidence metadata

**And** test coverage >80%

**Definition of Done:**
- [ ] `ConfidenceService` implements threshold logic
- [ ] Confidence metadata included in API responses
- [ ] Warning messages contextual and helpful
- [ ] Unit tests written FIRST (TDD) with >80% coverage
- [ ] All tests passing
- [ ] Manual test: Verify UI shows correct badges for different sample sizes

---

### Story 3.6: Analysis API Endpoints

**As a** frontend developer,
**I want** FastAPI endpoints to retrieve accuracy metrics and bias characterization,
**So that** I can display model comparisons in the web interface.

#### Acceptance Criteria:

**Given** accuracy metrics are calculated and stored
**When** I query the analysis API
**Then** I receive JSON responses with model performance data

**Endpoint 1: Site Accuracy Metrics**

```python
# backend/app/api/v1/endpoints/analysis.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.services.metrics_service import MetricsService
from app.schemas.analysis import SiteAccuracyResponse

router = APIRouter()

@router.get("/sites/{site_id}/accuracy", response_model=SiteAccuracyResponse)
async def get_site_accuracy(
    site_id: int,
    parameter_id: int,
    horizon: int = 6,
    db: AsyncSession = Depends(get_db)
):
    """
    Get accuracy metrics for all models at a specific site.

    Compare model performance for given parameter and forecast horizon.
    """
    service = MetricsService()

    # Query metrics for all models at this site
    metrics = await service.get_site_model_comparison(
        db=db,
        site_id=site_id,
        parameter_id=parameter_id,
        horizon=horizon
    )

    if not metrics:
        raise HTTPException(
            status_code=404,
            detail=f"No metrics found for site {site_id}"
        )

    return SiteAccuracyResponse(
        site_id=site_id,
        parameter_id=parameter_id,
        horizon=horizon,
        models=metrics
    )
```

**Response Schema:**

```python
# app/schemas/analysis.py
from pydantic import BaseModel, Field
from typing import List

class ModelAccuracyMetrics(BaseModel):
    model_id: int = Field(..., alias="modelId")
    model_name: str = Field(..., alias="modelName")
    mae: float
    bias: float
    std_dev: float = Field(..., alias="stdDev")
    sample_size: int = Field(..., alias="sampleSize")
    confidence_level: str = Field(..., alias="confidenceLevel")
    confidence_message: str = Field(..., alias="confidenceMessage")

    class Config:
        populate_by_name = True

class SiteAccuracyResponse(BaseModel):
    site_id: int = Field(..., alias="siteId")
    site_name: str = Field(..., alias="siteName")
    parameter_id: int = Field(..., alias="parameterId")
    parameter_name: str = Field(..., alias="parameterName")
    horizon: int
    models: List[ModelAccuracyMetrics]

    class Config:
        populate_by_name = True
```

**Example Response:**

```json
{
  "siteId": 1,
  "siteName": "Passy Plaine Joux",
  "parameterId": 1,
  "parameterName": "wind_speed",
  "horizon": 6,
  "models": [
    {
      "modelId": 1,
      "modelName": "AROME",
      "mae": 4.2,
      "bias": -1.5,
      "stdDev": 3.8,
      "sampleSize": 120,
      "confidenceLevel": "validated",
      "confidenceMessage": "Validated with 120 days of data. These metrics are statistically reliable."
    },
    {
      "modelId": 2,
      "modelName": "Meteo-Parapente",
      "mae": 5.7,
      "bias": 0.8,
      "stdDev": 4.2,
      "sampleSize": 115,
      "confidenceLevel": "validated",
      "confidenceMessage": "Validated with 115 days of data. These metrics are statistically reliable."
    }
  ]
}
```

**Endpoint 2: Model Bias Characterization**

```python
@router.get("/models/{model_id}/bias", response_model=ModelBiasResponse)
async def get_model_bias(
    model_id: int,
    site_id: int,
    parameter_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get bias characterization for a model across forecast horizons.

    Shows how model bias changes with forecast horizon (6h, 12h, 24h, 48h).
    """
    service = MetricsService()

    bias_data = await service.get_model_bias_by_horizon(
        db=db,
        model_id=model_id,
        site_id=site_id,
        parameter_id=parameter_id
    )

    if not bias_data:
        raise HTTPException(
            status_code=404,
            detail=f"No bias data found for model {model_id}"
        )

    return ModelBiasResponse(
        model_id=model_id,
        site_id=site_id,
        parameter_id=parameter_id,
        horizons=bias_data
    )
```

**Endpoint 3: Time Series Accuracy**

```python
@router.get("/sites/{site_id}/accuracy/timeseries", response_model=TimeSeriesAccuracyResponse)
async def get_accuracy_timeseries(
    site_id: int,
    model_id: int,
    parameter_id: int,
    granularity: str = "daily",  # daily, weekly, monthly
    start_date: datetime = None,
    end_date: datetime = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get accuracy metrics over time (daily/weekly/monthly granularity).

    Uses TimescaleDB continuous aggregates for fast queries.
    """
    service = MetricsService()

    if granularity == "daily":
        data = await service.get_daily_metrics(
            db=db,
            site_id=site_id,
            model_id=model_id,
            parameter_id=parameter_id,
            start_date=start_date or datetime.now() - timedelta(days=90),
            end_date=end_date or datetime.now()
        )
    elif granularity == "weekly":
        data = await service.get_weekly_metrics(...)
    elif granularity == "monthly":
        data = await service.get_monthly_metrics(...)
    else:
        raise HTTPException(status_code=400, detail="Invalid granularity")

    return TimeSeriesAccuracyResponse(
        site_id=site_id,
        model_id=model_id,
        parameter_id=parameter_id,
        granularity=granularity,
        data_points=data
    )
```

**And** endpoints are registered in main router:

```python
# backend/app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import analysis

api_router = APIRouter()
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
```

**And** CORS is configured for frontend:

```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**And** unit tests cover:
- ✅ GET /sites/{site_id}/accuracy returns metrics for all models
- ✅ GET /models/{model_id}/bias returns horizon-based bias data
- ✅ GET /sites/{site_id}/accuracy/timeseries returns daily/weekly/monthly data
- ✅ 404 error when site/model not found
- ✅ 400 error for invalid granularity
- ✅ Field aliases convert snake_case → camelCase in JSON

**And** test coverage >80%

**And** API documentation is auto-generated:
- FastAPI auto-generates OpenAPI docs at `/docs`
- Schemas include descriptions and examples

**Definition of Done:**
- [ ] 3 API endpoints implemented (`/sites/{site_id}/accuracy`, `/models/{model_id}/bias`, `/accuracy/timeseries`)
- [ ] Pydantic schemas with Field aliases for camelCase
- [ ] CORS middleware configured
- [ ] Unit tests written FIRST (TDD) with >80% coverage
- [ ] All tests passing
- [ ] Manual test: Query endpoints with curl/Postman, verify JSON responses
- [ ] OpenAPI docs accessible at `/docs`

---

## Epic 4: Model Comparison Web Visualization Platform

**Goal:** Provide a web interface for users to view and compare forecast model accuracy

**User Outcome:** Pilots can consult MétéoScore to objectively determine which forecast model is most reliable for their flying site

**FRs Covered:**
- FR5: Web Visualization Interface ✅
- FR6: Contextual Bias Characterization (visualization) ✅

**Dependencies:**
- Epic 1 (database setup) ✅
- Epic 2 (data collection pipeline) ✅
- Epic 3 (analysis engine) ✅

**Stories:** 10

---

### Story 4.1: Solid.js Frontend Project Setup

**As a** developer,
**I want** to initialize a Solid.js frontend project with TypeScript and Tailwind CSS,
**So that** I have a production-ready foundation for building the web interface.

#### Acceptance Criteria:

**Given** no frontend project exists
**When** I initialize the project
**Then** a Vite + Solid.js + TypeScript project is created with proper configuration

**Project Structure:**

```
frontend/
├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   ├── types/
│   ├── App.tsx
│   └── index.tsx
├── public/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

**And** dependencies are installed:

```json
{
  "dependencies": {
    "solid-js": "^1.8.0",
    "@solidjs/router": "^0.13.0",
    "d3": "^7.8.0",
    "@fontsource/geist-sans": "^5.0.0",
    "@fontsource/geist-mono": "^5.0.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "vite-plugin-solid": "^2.10.0",
    "typescript": "^5.3.0",
    "tailwindcss": "^4.0.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

**And** Tailwind CSS 4.0 is configured:

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist Sans', 'system-ui', 'sans-serif'],
        mono: ['Geist Mono', 'monospace'],
      },
      colors: {
        // MétéoScore brand colors
        primary: {
          50: '#f0f9ff',
          500: '#0ea5e9',
          900: '#0c4a6e',
        },
      },
    },
  },
  plugins: [],
}
```

**And** Vite config includes Solid plugin:

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import solidPlugin from 'vite-plugin-solid';

export default defineConfig({
  plugins: [solidPlugin()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    target: 'esnext',
  },
});
```

**And** TypeScript is configured with strict mode:

```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "esModuleInterop": true,
    "jsx": "preserve",
    "jsxImportSource": "solid-js",
    "types": ["vite/client"],
    "strict": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "resolveJsonModule": true,
    "baseUrl": ".",
    "paths": {
      "~/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

**And** basic routing is configured:

```tsx
// src/App.tsx
import { Router, Route } from '@solidjs/router';
import { Component } from 'solid-js';

const App: Component = () => {
  return (
    <Router>
      <Route path="/" component={() => <div>MétéoScore</div>} />
    </Router>
  );
};

export default App;
```

**And** development server runs successfully:
- `npm run dev` starts Vite dev server on port 5173
- Hot module replacement (HMR) works
- TypeScript compilation has no errors

**Definition of Done:**
- [ ] Vite + Solid.js project initialized
- [ ] Tailwind CSS 4.0 configured and working
- [ ] TypeScript strict mode enabled
- [ ] @solidjs/router configured
- [ ] Geist fonts installed and configured
- [ ] Dev server runs without errors
- [ ] Basic "Hello MétéoScore" page renders

---

### Story 4.2: Site Selection & Parameter Controls

**As a** user,
**I want** to select a flying site and weather parameters,
**So that** I can view accuracy metrics for my specific use case.

#### Acceptance Criteria:

**Given** the homepage loads
**When** I view the controls section
**Then** I see site, parameter, and horizon selectors

**Site Selector (Dropdown):**

```tsx
// src/components/SiteSelector.tsx
import { Component, createSignal, For } from 'solid-js';

interface Site {
  id: number;
  name: string;
  region: string;
}

interface SiteSelectorProps {
  sites: Site[];
  selectedSiteId: number;
  onSiteChange: (siteId: number) => void;
}

const SiteSelector: Component<SiteSelectorProps> = (props) => {
  return (
    <div class="mb-6">
      <label class="block text-sm font-medium text-gray-700 mb-2">
        Flying Site
      </label>
      <select
        class="block w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        value={props.selectedSiteId}
        onChange={(e) => props.onSiteChange(Number(e.currentTarget.value))}
      >
        <For each={props.sites}>
          {(site) => (
            <option value={site.id}>
              {site.name} - {site.region}
            </option>
          )}
        </For>
      </select>
    </div>
  );
};

export default SiteSelector;
```

**Parameter Selector (Radio Buttons):**

```tsx
// src/components/ParameterSelector.tsx
import { Component, For } from 'solid-js';

interface Parameter {
  id: number;
  name: string;
  displayName: string;
  unit: string;
}

interface ParameterSelectorProps {
  parameters: Parameter[];
  selectedParameterId: number;
  onParameterChange: (parameterId: number) => void;
}

const ParameterSelector: Component<ParameterSelectorProps> = (props) => {
  return (
    <div class="mb-6">
      <label class="block text-sm font-medium text-gray-700 mb-2">
        Weather Parameter
      </label>
      <div class="flex gap-4">
        <For each={props.parameters}>
          {(param) => (
            <label class="flex items-center cursor-pointer">
              <input
                type="radio"
                name="parameter"
                value={param.id}
                checked={props.selectedParameterId === param.id}
                onChange={() => props.onParameterChange(param.id)}
                class="w-4 h-4 text-primary-500 focus:ring-primary-500"
              />
              <span class="ml-2 text-sm text-gray-700">
                {param.displayName} ({param.unit})
              </span>
            </label>
          )}
        </For>
      </div>
    </div>
  );
};

export default ParameterSelector;
```

**Horizon Selector (Buttons):**

```tsx
// src/components/HorizonSelector.tsx
import { Component, For } from 'solid-js';

interface HorizonSelectorProps {
  horizons: number[];
  selectedHorizon: number;
  onHorizonChange: (horizon: number) => void;
}

const HorizonSelector: Component<HorizonSelectorProps> = (props) => {
  return (
    <div class="mb-6">
      <label class="block text-sm font-medium text-gray-700 mb-2">
        Forecast Horizon
      </label>
      <div class="flex gap-2">
        <For each={props.horizons}>
          {(horizon) => (
            <button
              class={`px-4 py-2 rounded-lg font-medium transition ${
                props.selectedHorizon === horizon
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
              onClick={() => props.onHorizonChange(horizon)}
            >
              +{horizon}h
            </button>
          )}
        </For>
      </div>
    </div>
  );
};

export default HorizonSelector;
```

**And** state management uses Solid.js signals:

```tsx
// src/pages/HomePage.tsx
import { Component, createSignal } from 'solid-js';
import SiteSelector from '~/components/SiteSelector';
import ParameterSelector from '~/components/ParameterSelector';
import HorizonSelector from '~/components/HorizonSelector';

const HomePage: Component = () => {
  const [selectedSiteId, setSelectedSiteId] = createSignal(1); // Passy Plaine Joux
  const [selectedParameterId, setSelectedParameterId] = createSignal(1); // wind_speed
  const [selectedHorizon, setSelectedHorizon] = createSignal(6); // 6h

  const sites = [
    { id: 1, name: 'Passy Plaine Joux', region: 'Haute-Savoie' },
  ];

  const parameters = [
    { id: 1, name: 'wind_speed', displayName: 'Wind Speed', unit: 'km/h' },
    { id: 2, name: 'wind_direction', displayName: 'Wind Direction', unit: '°' },
    { id: 3, name: 'temperature', displayName: 'Temperature', unit: '°C' },
  ];

  const horizons = [6, 12, 24, 48];

  return (
    <div class="container mx-auto px-4 py-8">
      <h1 class="text-3xl font-bold mb-8">MétéoScore</h1>

      <SiteSelector
        sites={sites}
        selectedSiteId={selectedSiteId()}
        onSiteChange={setSelectedSiteId}
      />

      <ParameterSelector
        parameters={parameters}
        selectedParameterId={selectedParameterId()}
        onParameterChange={setSelectedParameterId}
      />

      <HorizonSelector
        horizons={horizons}
        selectedHorizon={selectedHorizon()}
        onHorizonChange={setSelectedHorizon}
      />
    </div>
  );
};

export default HomePage;
```

**And** components follow Solid.js best practices:
- ✅ Props accessed via `props.propName` (never destructured)
- ✅ Signals used for reactive state
- ✅ `<For>` component for lists (not `.map()`)
- ✅ Event handlers use proper typing

**And** styling is responsive:
- Mobile: vertical layout, full-width controls
- Desktop: horizontal layout with grid

**Definition of Done:**
- [ ] SiteSelector component created
- [ ] ParameterSelector component created
- [ ] HorizonSelector component created
- [ ] State management with Solid.js signals
- [ ] Responsive design (mobile + desktop)
- [ ] No TypeScript errors
- [ ] Manual test: Changing selectors updates state correctly

---

### Story 4.3: Model Comparison Table Component

**As a** user,
**I want** to see a comparison table of model accuracy metrics,
**So that** I can identify which model performs best for my selected site and parameter.

#### Acceptance Criteria:

**Given** site, parameter, and horizon are selected
**When** I view the comparison table
**Then** I see MAE, bias, and confidence indicators for all models

**Table Component:**

```tsx
// src/components/ModelComparisonTable.tsx
import { Component, For, Show } from 'solid-js';

interface ModelMetrics {
  modelId: number;
  modelName: string;
  mae: number;
  bias: number;
  stdDev: number;
  sampleSize: number;
  confidenceLevel: 'insufficient' | 'preliminary' | 'validated';
  confidenceMessage: string;
}

interface ModelComparisonTableProps {
  models: ModelMetrics[];
  parameterUnit: string;
}

const ModelComparisonTable: Component<ModelComparisonTableProps> = (props) => {
  const getConfidenceBadge = (level: string) => {
    switch (level) {
      case 'validated':
        return { text: '✅ Validated', color: 'bg-green-100 text-green-800' };
      case 'preliminary':
        return { text: '🔶 Preliminary', color: 'bg-orange-100 text-orange-800' };
      case 'insufficient':
        return { text: '⚠️ Insufficient Data', color: 'bg-red-100 text-red-800' };
      default:
        return { text: 'Unknown', color: 'bg-gray-100 text-gray-800' };
    }
  };

  const getBiasText = (bias: number, unit: string) => {
    if (bias > 0) {
      return `Underestimates by ${bias.toFixed(1)} ${unit}`;
    } else if (bias < 0) {
      return `Overestimates by ${Math.abs(bias).toFixed(1)} ${unit}`;
    } else {
      return 'No systematic bias';
    }
  };

  return (
    <div class="overflow-x-auto">
      <table class="min-w-full bg-white border border-gray-200 rounded-lg">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Model
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              MAE ({props.parameterUnit})
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Bias
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Sample Size
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Confidence
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
          <For each={props.models}>
            {(model, index) => {
              const badge = getConfidenceBadge(model.confidenceLevel);
              const isBest = index() === 0; // Assumes sorted by MAE (best first)

              return (
                <tr class={isBest ? 'bg-green-50' : ''}>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                      <span class="font-medium text-gray-900">{model.modelName}</span>
                      <Show when={isBest}>
                        <span class="ml-2 px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded">
                          Best
                        </span>
                      </Show>
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {model.mae.toFixed(1)}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {getBiasText(model.bias, props.parameterUnit)}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {model.sampleSize} measurements
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span class={`px-2 py-1 text-xs font-medium rounded ${badge.color}`}>
                      {badge.text}
                    </span>
                  </td>
                </tr>
              );
            }}
          </For>
        </tbody>
      </table>

      <Show when={props.models.length === 0}>
        <div class="text-center py-8 text-gray-500">
          No data available for this configuration
        </div>
      </Show>
    </div>
  );
};

export default ModelComparisonTable;
```

**And** models are automatically sorted by MAE (best first):

```tsx
// src/pages/HomePage.tsx
const sortedModels = () => {
  return [...models()].sort((a, b) => a.mae - b.mae);
};
```

**And** table is responsive:
- Mobile: horizontal scroll for full table
- Desktop: full-width table with proper spacing

**And** best model is highlighted:
- Green background row
- "Best" badge next to model name

**Definition of Done:**
- [ ] ModelComparisonTable component created
- [ ] MAE, bias, sample size, confidence displayed
- [ ] Models sorted by MAE (best first)
- [ ] Best model highlighted with green background
- [ ] Confidence badges color-coded (red/orange/green)
- [ ] Responsive table design
- [ ] No TypeScript errors
- [ ] Manual test: Table displays correctly with sample data

---

### Story 4.4: Bias Characterization Card

**As a** user,
**I want** to see a clear explanation of each model's systematic bias,
**So that** I can mentally adjust forecasts when using that model.

#### Acceptance Criteria:

**Given** a model has validated metrics
**When** I view the bias characterization card
**Then** I see a user-friendly explanation of the model's tendency to over/underestimate

**Bias Card Component:**

```tsx
// src/components/BiasCharacterizationCard.tsx
import { Component, Show } from 'solid-js';

interface BiasCharacterizationCardProps {
  modelName: string;
  bias: number;
  parameterName: string;
  parameterUnit: string;
  confidenceLevel: string;
}

const BiasCharacterizationCard: Component<BiasCharacterizationCardProps> = (props) => {
  const getBiasInterpretation = () => {
    const absBias = Math.abs(props.bias);

    if (absBias < 1) {
      return {
        title: 'Excellent Calibration',
        description: `${props.modelName} has minimal systematic bias for ${props.parameterName}.`,
        icon: '🎯',
        color: 'border-green-500',
      };
    } else if (props.bias > 0) {
      return {
        title: 'Systematic Underestimation',
        description: `${props.modelName} typically underestimates ${props.parameterName} by ${absBias.toFixed(1)} ${props.parameterUnit} on average. Expect conditions to be slightly stronger than predicted.`,
        icon: '⬆️',
        color: 'border-blue-500',
      };
    } else {
      return {
        title: 'Systematic Overestimation',
        description: `${props.modelName} typically overestimates ${props.parameterName} by ${absBias.toFixed(1)} ${props.parameterUnit} on average. Expect conditions to be slightly weaker than predicted.`,
        icon: '⬇️',
        color: 'border-orange-500',
      };
    }
  };

  const interpretation = getBiasInterpretation();

  return (
    <div class={`border-l-4 ${interpretation.color} bg-white p-6 rounded-lg shadow-sm`}>
      <div class="flex items-start">
        <div class="text-3xl mr-4">{interpretation.icon}</div>
        <div class="flex-1">
          <h3 class="text-lg font-semibold text-gray-900 mb-2">
            {interpretation.title}
          </h3>
          <p class="text-gray-700 mb-3">
            {interpretation.description}
          </p>
          <Show when={props.confidenceLevel === 'preliminary'}>
            <p class="text-sm text-orange-600">
              ⚠️ This bias characterization is preliminary. Results will stabilize with more data.
            </p>
          </Show>
          <Show when={props.confidenceLevel === 'insufficient'}>
            <p class="text-sm text-red-600">
              ⚠️ Insufficient data to reliably characterize bias.
            </p>
          </Show>
        </div>
      </div>
    </div>
  );
};

export default BiasCharacterizationCard;
```

**And** practical usage examples are shown:

```tsx
// Extended version with example
<div class="mt-4 p-4 bg-gray-50 rounded">
  <p class="text-sm font-medium text-gray-700 mb-2">Practical Example:</p>
  <p class="text-sm text-gray-600">
    If {props.modelName} forecasts wind at 25 km/h, expect actual conditions around{' '}
    <span class="font-semibold">
      {(25 - props.bias).toFixed(0)} km/h
    </span>
    {' '}based on historical bias.
  </p>
</div>
```

**And** multiple bias cards can be displayed (one per model):

```tsx
// src/pages/HomePage.tsx
<For each={sortedModels()}>
  {(model) => (
    <BiasCharacterizationCard
      modelName={model.modelName}
      bias={model.bias}
      parameterName={parameterDisplayName()}
      parameterUnit={parameterUnit()}
      confidenceLevel={model.confidenceLevel}
    />
  )}
</For>
```

**Definition of Done:**
- [ ] BiasCharacterizationCard component created
- [ ] Bias interpretation logic (underestimation/overestimation/minimal)
- [ ] Color-coded borders (green/blue/orange)
- [ ] Practical example calculation
- [ ] Warning messages for preliminary/insufficient data
- [ ] No TypeScript errors
- [ ] Manual test: Card displays correctly for different bias values

---

### Story 4.5: Accuracy Time Series Chart (D3.js)

**As a** user,
**I want** to see how model accuracy evolves over time,
**So that** I can understand if recent performance differs from historical trends.

#### Acceptance Criteria:

**Given** daily accuracy metrics are available
**When** I view the time series chart
**Then** I see MAE evolution for all models over the past 90 days

**Chart Component:**

```tsx
// src/components/AccuracyTimeSeriesChart.tsx
import { Component, onMount, createEffect, onCleanup } from 'solid-js';
import * as d3 from 'd3';

interface DataPoint {
  date: Date;
  mae: number;
}

interface ModelTimeSeries {
  modelId: number;
  modelName: string;
  data: DataPoint[];
  color: string;
}

interface AccuracyTimeSeriesChartProps {
  models: ModelTimeSeries[];
  parameterUnit: string;
}

const AccuracyTimeSeriesChart: Component<AccuracyTimeSeriesChartProps> = (props) => {
  let svgRef: SVGSVGElement | undefined;

  const drawChart = () => {
    if (!svgRef) return;

    // Clear previous chart
    d3.select(svgRef).selectAll('*').remove();

    const margin = { top: 20, right: 120, bottom: 40, left: 60 };
    const width = svgRef.clientWidth - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    const svg = d3.select(svgRef)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Scales
    const xScale = d3.scaleTime()
      .domain(d3.extent(props.models[0].data, d => d.date) as [Date, Date])
      .range([0, width]);

    const yScale = d3.scaleLinear()
      .domain([0, d3.max(props.models.flatMap(m => m.data), d => d.mae) || 10])
      .nice()
      .range([height, 0]);

    // Axes
    const xAxis = d3.axisBottom(xScale)
      .ticks(6)
      .tickFormat(d3.timeFormat('%b %d') as any);

    const yAxis = d3.axisLeft(yScale)
      .ticks(6);

    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(xAxis)
      .attr('class', 'text-gray-600');

    svg.append('g')
      .call(yAxis)
      .attr('class', 'text-gray-600');

    // Y-axis label
    svg.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', 0 - margin.left)
      .attr('x', 0 - (height / 2))
      .attr('dy', '1em')
      .style('text-anchor', 'middle')
      .attr('class', 'text-sm text-gray-700')
      .text(`MAE (${props.parameterUnit})`);

    // Line generator
    const line = d3.line<DataPoint>()
      .x(d => xScale(d.date))
      .y(d => yScale(d.mae))
      .curve(d3.curveMonotoneX);

    // Draw lines for each model
    props.models.forEach(model => {
      svg.append('path')
        .datum(model.data)
        .attr('fill', 'none')
        .attr('stroke', model.color)
        .attr('stroke-width', 2)
        .attr('d', line);

      // Add legend
      const lastPoint = model.data[model.data.length - 1];
      svg.append('text')
        .attr('x', width + 10)
        .attr('y', yScale(lastPoint.mae))
        .attr('dy', '0.35em')
        .attr('class', 'text-sm font-medium')
        .style('fill', model.color)
        .text(model.modelName);
    });

    // Tooltip
    const tooltip = d3.select('body')
      .append('div')
      .attr('class', 'absolute bg-white border border-gray-300 rounded px-3 py-2 text-sm shadow-lg pointer-events-none opacity-0')
      .style('z-index', '1000');

    // Interactive overlay
    svg.append('rect')
      .attr('width', width)
      .attr('height', height)
      .attr('fill', 'transparent')
      .on('mousemove', function(event) {
        const [mx] = d3.pointer(event);
        const date = xScale.invert(mx);

        tooltip
          .style('opacity', 1)
          .style('left', `${event.pageX + 10}px`)
          .style('top', `${event.pageY - 10}px`)
          .html(`
            <div class="font-semibold">${d3.timeFormat('%b %d, %Y')(date)}</div>
            ${props.models.map(m => {
              const closest = m.data.reduce((prev, curr) =>
                Math.abs(curr.date.getTime() - date.getTime()) < Math.abs(prev.date.getTime() - date.getTime()) ? curr : prev
              );
              return `<div style="color: ${m.color}">${m.modelName}: ${closest.mae.toFixed(1)} ${props.parameterUnit}</div>`;
            }).join('')}
          `);
      })
      .on('mouseout', () => {
        tooltip.style('opacity', 0);
      });

    onCleanup(() => {
      tooltip.remove();
    });
  };

  onMount(() => {
    drawChart();
  });

  createEffect(() => {
    // Redraw when props change
    props.models;
    drawChart();
  });

  return (
    <div class="bg-white p-6 rounded-lg shadow-sm">
      <h3 class="text-lg font-semibold text-gray-900 mb-4">
        Accuracy Evolution (Last 90 Days)
      </h3>
      <svg ref={svgRef!} class="w-full h-[400px]"></svg>
    </div>
  );
};

export default AccuracyTimeSeriesChart;
```

**And** chart is responsive:
- Resizes on window resize
- Mobile: reduced margins, smaller font sizes
- Desktop: full-featured chart with legend

**And** interactions are smooth:
- Hover tooltip shows exact values
- Smooth line interpolation (monotoneX curve)

**Definition of Done:**
- [ ] AccuracyTimeSeriesChart component created using D3.js
- [ ] Multi-line chart with color-coded models
- [ ] Interactive tooltip on hover
- [ ] Responsive design
- [ ] Proper axis labels and formatting
- [ ] No TypeScript errors
- [ ] Manual test: Chart renders with sample time series data

---

### Story 4.6: Data Freshness & Sample Size Indicators

**As a** user,
**I want** to see when data was last updated and how much data is available,
**So that** I can judge the reliability and currency of the metrics.

#### Acceptance Criteria:

**Given** metrics are displayed
**When** I view the data freshness section
**Then** I see last update timestamp, sample size, and date range

**Freshness Indicator Component:**

```tsx
// src/components/DataFreshnessIndicator.tsx
import { Component } from 'solid-js';

interface DataFreshnessIndicatorProps {
  lastUpdate: Date;
  sampleSize: number;
  dateRange: {
    start: Date;
    end: Date;
  };
  confidenceLevel: 'insufficient' | 'preliminary' | 'validated';
}

const DataFreshnessIndicator: Component<DataFreshnessIndicatorProps> = (props) => {
  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(date);
  };

  const formatRelativeTime = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffHours < 24) return `${diffHours} hours ago`;
    return `${diffDays} days ago`;
  };

  const getDaysOfData = () => {
    return Math.floor(
      (props.dateRange.end.getTime() - props.dateRange.start.getTime()) / 86400000
    );
  };

  return (
    <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
      <h4 class="text-sm font-semibold text-gray-700 mb-3">Data Information</h4>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <p class="text-xs text-gray-500 mb-1">Last Updated</p>
          <p class="text-sm font-medium text-gray-900">
            {formatRelativeTime(props.lastUpdate)}
          </p>
          <p class="text-xs text-gray-500">
            {formatDate(props.lastUpdate)}
          </p>
        </div>

        <div>
          <p class="text-xs text-gray-500 mb-1">Sample Size</p>
          <p class="text-sm font-medium text-gray-900">
            {props.sampleSize.toLocaleString()} measurements
          </p>
          <p class="text-xs text-gray-500">
            {getDaysOfData()} days of data
          </p>
        </div>

        <div>
          <p class="text-xs text-gray-500 mb-1">Data Range</p>
          <p class="text-sm font-medium text-gray-900">
            {formatDate(props.dateRange.start)}
          </p>
          <p class="text-xs text-gray-500">
            to {formatDate(props.dateRange.end)}
          </p>
        </div>
      </div>

      <div class="mt-4 pt-4 border-t border-gray-200">
        <div class={`flex items-center gap-2 ${
          props.confidenceLevel === 'validated' ? 'text-green-700' :
          props.confidenceLevel === 'preliminary' ? 'text-orange-700' :
          'text-red-700'
        }`}>
          <div class="text-lg">
            {props.confidenceLevel === 'validated' ? '✅' :
             props.confidenceLevel === 'preliminary' ? '🔶' : '⚠️'}
          </div>
          <div>
            <p class="text-sm font-medium">
              {props.confidenceLevel === 'validated' ? 'Validated Data' :
               props.confidenceLevel === 'preliminary' ? 'Preliminary Data' :
               'Insufficient Data'}
            </p>
            <p class="text-xs">
              {props.confidenceLevel === 'validated'
                ? 'Metrics are statistically reliable (90+ days)'
                : props.confidenceLevel === 'preliminary'
                ? 'Results will stabilize with more data (30-89 days)'
                : 'Collect more data for reliable metrics (<30 days)'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataFreshnessIndicator;
```

**And** relative timestamps update automatically:

```tsx
// Auto-refresh relative time every minute
const [now, setNow] = createSignal(new Date());

onMount(() => {
  const interval = setInterval(() => {
    setNow(new Date());
  }, 60000); // Update every minute

  onCleanup(() => clearInterval(interval));
});
```

**Definition of Done:**
- [ ] DataFreshnessIndicator component created
- [ ] Last update timestamp (relative + absolute)
- [ ] Sample size display
- [ ] Date range display
- [ ] Confidence level indicator
- [ ] Relative time auto-updates
- [ ] No TypeScript errors
- [ ] Manual test: Freshness indicator displays correctly

---

### Story 4.7: Responsive Layout & Mobile Optimization

**As a** user,
**I want** the web interface to work seamlessly on mobile devices,
**So that** I can check MétéoScore from the field before flying.

#### Acceptance Criteria:

**Given** I access MétéoScore on a mobile device
**When** I view any page
**Then** the layout adapts to the screen size with touch-friendly controls

**Responsive Layout Structure:**

```tsx
// src/components/Layout.tsx
import { Component, JSX } from 'solid-js';

interface LayoutProps {
  children: JSX.Element;
}

const Layout: Component<LayoutProps> = (props) => {
  return (
    <div class="min-h-screen bg-gray-50">
      {/* Header */}
      <header class="bg-white border-b border-gray-200">
        <div class="container mx-auto px-4 py-4">
          <div class="flex items-center justify-between">
            <h1 class="text-2xl md:text-3xl font-bold text-gray-900">
              MétéoScore
            </h1>
            <nav class="flex gap-4">
              <a href="/methodology" class="text-sm text-gray-600 hover:text-gray-900">
                Methodology
              </a>
              <a href="https://github.com/..." class="text-sm text-gray-600 hover:text-gray-900">
                GitHub
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main class="container mx-auto px-4 py-6 md:py-8">
        {props.children}
      </main>

      {/* Footer */}
      <footer class="bg-white border-t border-gray-200 mt-12">
        <div class="container mx-auto px-4 py-6">
          <p class="text-sm text-gray-500 text-center">
            MétéoScore - Open Source Weather Forecast Accuracy Platform
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
```

**Mobile Optimization Requirements:**

1. **Touch-Friendly Controls:**
   - Buttons: minimum 44x44px tap targets
   - Dropdowns: large enough for easy selection
   - Radio buttons: increased spacing (16px gap)

2. **Responsive Grid:**
   ```tsx
   <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
     {/* Components */}
   </div>
   ```

3. **Typography Scale:**
   - Mobile: base text-sm, headings text-xl
   - Desktop: base text-base, headings text-3xl

4. **Table Behavior:**
   ```tsx
   <div class="overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0">
     <table class="min-w-full">
       {/* Table content */}
     </table>
   </div>
   ```

5. **Chart Responsiveness:**
   - Mobile: reduced margins, vertical legend
   - Desktop: horizontal legend, larger margins

**And** viewport meta tag is configured:

```html
<!-- index.html -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
```

**And** touch gestures work smoothly:
- Smooth scrolling enabled
- No 300ms tap delay
- Proper touch event handling

**Definition of Done:**
- [ ] Layout component with responsive header/footer
- [ ] Mobile-first grid system (1 col mobile, 2-3 cols desktop)
- [ ] Touch-friendly controls (44x44px minimum)
- [ ] Responsive typography
- [ ] Table horizontal scroll on mobile
- [ ] Chart adapts to screen size
- [ ] Manual test: Test on iPhone, Android, tablet

---

### Story 4.8: API Integration with Error Handling

**As a** developer,
**I want** to fetch data from the FastAPI backend with proper error handling,
**So that** users see helpful messages when data is unavailable or errors occur.

#### Acceptance Criteria:

**Given** the frontend needs data from the API
**When** I make API requests
**Then** loading states, errors, and successful responses are handled gracefully

**API Service:**

```tsx
// src/services/api.ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface SiteAccuracyResponse {
  siteId: number;
  siteName: string;
  parameterId: number;
  parameterName: string;
  horizon: number;
  models: ModelAccuracyMetrics[];
}

export interface ModelAccuracyMetrics {
  modelId: number;
  modelName: string;
  mae: number;
  bias: number;
  stdDev: number;
  sampleSize: number;
  confidenceLevel: string;
  confidenceMessage: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function getSiteAccuracy(
  siteId: number,
  parameterId: number,
  horizon: number
): Promise<SiteAccuracyResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/analysis/sites/${siteId}/accuracy?parameter_id=${parameterId}&horizon=${horizon}`
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new ApiError(404, 'No data available for this configuration');
    }
    throw new ApiError(response.status, 'Failed to fetch accuracy data');
  }

  return response.json();
}

export async function getAccuracyTimeSeries(
  siteId: number,
  modelId: number,
  parameterId: number,
  granularity: 'daily' | 'weekly' | 'monthly' = 'daily'
): Promise<any> {
  const response = await fetch(
    `${API_BASE_URL}/api/analysis/sites/${siteId}/accuracy/timeseries?model_id=${modelId}&parameter_id=${parameterId}&granularity=${granularity}`
  );

  if (!response.ok) {
    throw new ApiError(response.status, 'Failed to fetch time series data');
  }

  return response.json();
}
```

**Resource Pattern with Solid.js:**

```tsx
// src/pages/HomePage.tsx
import { createResource, Show, Suspense } from 'solid-js';
import { getSiteAccuracy } from '~/services/api';

const HomePage: Component = () => {
  const [selectedSiteId, setSelectedSiteId] = createSignal(1);
  const [selectedParameterId, setSelectedParameterId] = createSignal(1);
  const [selectedHorizon, setSelectedHorizon] = createSignal(6);

  // Reactive resource - automatically refetches when dependencies change
  const [accuracyData, { refetch }] = createResource(
    () => ({
      siteId: selectedSiteId(),
      parameterId: selectedParameterId(),
      horizon: selectedHorizon(),
    }),
    async (params) => {
      return await getSiteAccuracy(params.siteId, params.parameterId, params.horizon);
    }
  );

  return (
    <Layout>
      <div class="space-y-6">
        {/* Controls */}
        <SiteSelector /* ... */ />
        <ParameterSelector /* ... */ />
        <HorizonSelector /* ... */ />

        {/* Data Display with Loading/Error States */}
        <Suspense fallback={<LoadingSpinner />}>
          <Show
            when={!accuracyData.error}
            fallback={<ErrorMessage error={accuracyData.error} onRetry={refetch} />}
          >
            <Show when={accuracyData()}>
              {(data) => (
                <>
                  <DataFreshnessIndicator /* ... */ />
                  <ModelComparisonTable models={data().models} /* ... */ />
                  <For each={data().models}>
                    {(model) => (
                      <BiasCharacterizationCard /* ... */ />
                    )}
                  </For>
                </>
              )}
            </Show>
          </Show>
        </Suspense>
      </div>
    </Layout>
  );
};
```

**Loading Spinner Component:**

```tsx
// src/components/LoadingSpinner.tsx
import { Component } from 'solid-js';

const LoadingSpinner: Component = () => {
  return (
    <div class="flex items-center justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      <p class="ml-4 text-gray-600">Loading accuracy data...</p>
    </div>
  );
};

export default LoadingSpinner;
```

**Error Message Component:**

```tsx
// src/components/ErrorMessage.tsx
import { Component } from 'solid-js';
import { ApiError } from '~/services/api';

interface ErrorMessageProps {
  error: Error | ApiError;
  onRetry: () => void;
}

const ErrorMessage: Component<ErrorMessageProps> = (props) => {
  const getMessage = () => {
    if (props.error instanceof ApiError) {
      return props.error.message;
    }
    return 'An unexpected error occurred. Please try again.';
  };

  return (
    <div class="bg-red-50 border border-red-200 rounded-lg p-6">
      <div class="flex items-start">
        <div class="text-2xl mr-3">⚠️</div>
        <div class="flex-1">
          <h3 class="text-lg font-semibold text-red-900 mb-2">
            Error Loading Data
          </h3>
          <p class="text-red-700 mb-4">
            {getMessage()}
          </p>
          <button
            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
            onClick={() => props.onRetry()}
          >
            Retry
          </button>
        </div>
      </div>
    </div>
  );
};

export default ErrorMessage;
```

**And** environment variables are configured:

```env
# .env.development
VITE_API_BASE_URL=http://localhost:8000

# .env.production
VITE_API_BASE_URL=https://meteoscore.com
```

**Definition of Done:**
- [ ] API service with typed functions
- [ ] ApiError class for structured errors
- [ ] createResource for reactive data fetching
- [ ] LoadingSpinner component
- [ ] ErrorMessage component with retry
- [ ] Environment variable configuration
- [ ] No TypeScript errors
- [ ] Manual test: Test loading, success, error, and retry scenarios

---

### Story 4.9: Methodology & Transparency Page

**As a** user,
**I want** to understand how accuracy metrics are calculated,
**So that** I can trust the results and understand their limitations.

#### Acceptance Criteria:

**Given** I navigate to the methodology page
**When** the page loads
**Then** I see clear explanations of MAE, bias, data sources, and calculations

**Methodology Page:**

```tsx
// src/pages/MethodologyPage.tsx
import { Component } from 'solid-js';
import Layout from '~/components/Layout';

const MethodologyPage: Component = () => {
  return (
    <Layout>
      <div class="max-w-4xl mx-auto prose prose-sm md:prose-base">
        <h1>Methodology</h1>

        <h2>How MétéoScore Works</h2>
        <p>
          MétéoScore objectively evaluates weather forecast model accuracy by comparing
          forecast predictions against real-world observations from weather beacons and stations.
        </p>

        <h2>Metrics Explained</h2>

        <h3>Mean Absolute Error (MAE)</h3>
        <div class="bg-gray-50 p-4 rounded-lg my-4">
          <p class="font-mono text-sm">
            MAE = Average(|Forecast - Observation|)
          </p>
        </div>
        <p>
          MAE measures the average magnitude of forecast errors. Lower is better.
          For example, an MAE of 4.2 km/h for wind speed means the model is typically
          off by ±4.2 km/h.
        </p>

        <h3>Bias (Systematic Error)</h3>
        <div class="bg-gray-50 p-4 rounded-lg my-4">
          <p class="font-mono text-sm">
            Bias = Average(Forecast - Observation)
          </p>
        </div>
        <ul>
          <li><strong>Negative bias:</strong> Model systematically overestimates</li>
          <li><strong>Positive bias:</strong> Model systematically underestimates</li>
          <li><strong>Zero bias:</strong> No systematic tendency</li>
        </ul>

        <h2>Data Sources</h2>

        <h3>Forecast Models</h3>
        <ul>
          <li><strong>AROME</strong> - Météo-France high-resolution model (via free API)</li>
          <li><strong>Meteo-Parapente</strong> - Community-specialized paragliding forecasts</li>
        </ul>

        <h3>Observations</h3>
        <ul>
          <li><strong>ROMMA</strong> - Network of automated weather beacons</li>
          <li><strong>FFVL</strong> - French paragliding federation weather stations</li>
        </ul>

        <h2>Data Collection Process</h2>
        <ol>
          <li>Forecasts retrieved 4x daily (00h, 06h, 12h, 18h UTC runs)</li>
          <li>Observations collected 6x daily from beacons</li>
          <li>Forecasts matched with observations within ±30 minutes</li>
          <li>Deviation calculated: Observation - Forecast</li>
          <li>Metrics computed from 90+ days of historical deviations</li>
        </ol>

        <h2>Confidence Levels</h2>
        <table class="min-w-full border">
          <thead>
            <tr class="bg-gray-50">
              <th class="border px-4 py-2">Level</th>
              <th class="border px-4 py-2">Days of Data</th>
              <th class="border px-4 py-2">Interpretation</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="border px-4 py-2">✅ Validated</td>
              <td class="border px-4 py-2">90+ days</td>
              <td class="border px-4 py-2">Statistically reliable metrics</td>
            </tr>
            <tr>
              <td class="border px-4 py-2">🔶 Preliminary</td>
              <td class="border px-4 py-2">30-89 days</td>
              <td class="border px-4 py-2">Results will stabilize with more data</td>
            </tr>
            <tr>
              <td class="border px-4 py-2">⚠️ Insufficient</td>
              <td class="border px-4 py-2">&lt;30 days</td>
              <td class="border px-4 py-2">Not enough data for reliable conclusions</td>
            </tr>
          </tbody>
        </table>

        <h2>Limitations</h2>
        <ul>
          <li>Metrics reflect past performance, not future accuracy</li>
          <li>Site-specific results may not generalize to other locations</li>
          <li>Extreme weather events may skew statistics if rare</li>
          <li>Observation beacons have their own measurement errors (±0.5 km/h wind, ±0.3°C temp)</li>
        </ul>

        <h2>Transparency & Open Source</h2>
        <p>
          MétéoScore is fully open source. All code, methodology, and data sources are
          publicly verifiable:
        </p>
        <ul>
          <li>
            <a href="https://github.com/..." class="text-primary-500 hover:underline">
              GitHub Repository
            </a>
          </li>
          <li>
            <a href="https://github.com/.../blob/main/docs/METHODOLOGY.md" class="text-primary-500 hover:underline">
              Detailed Technical Documentation
            </a>
          </li>
        </ul>

        <h2>Questions or Feedback?</h2>
        <p>
          Open an issue on <a href="https://github.com/.../issues" class="text-primary-500 hover:underline">GitHub</a> or
          contact us at [email].
        </p>
      </div>
    </Layout>
  );
};

export default MethodologyPage;
```

**And** prose styling is configured in Tailwind:

```javascript
// tailwind.config.js
module.exports = {
  plugins: [
    require('@tailwindcss/typography'),
  ],
};
```

**And** page is linked from header navigation:

```tsx
<a href="/methodology" class="text-sm text-gray-600 hover:text-gray-900">
  Methodology
</a>
```

**Definition of Done:**
- [ ] MethodologyPage component created
- [ ] MAE and bias calculations explained
- [ ] Data sources disclosed
- [ ] Confidence levels table
- [ ] Limitations section
- [ ] Links to GitHub and documentation
- [ ] Prose typography styling
- [ ] Navigation link in header
- [ ] No TypeScript errors

---

### Story 4.10: Production Build & Docker Integration

**As a** developer,
**I want** to create an optimized production build and integrate it with Docker Compose,
**So that** the frontend is efficiently served in production alongside the backend.

#### Acceptance Criteria:

**Given** the frontend is ready for production
**When** I build and deploy
**Then** static files are optimized and served via Nginx in Docker

**Production Build Configuration:**

```typescript
// vite.config.ts (production optimizations)
import { defineConfig } from 'vite';
import solidPlugin from 'vite-plugin-solid';

export default defineConfig({
  plugins: [solidPlugin()],
  build: {
    target: 'esnext',
    minify: 'esbuild',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['solid-js', '@solidjs/router'],
          d3: ['d3'],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
});
```

**Nginx Configuration:**

```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback - serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Dockerfile for Frontend:**

```dockerfile
# frontend/Dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Docker Compose Integration:**

```yaml
# docker-compose.yml (updated with frontend service)
version: '3.8'

services:
  db:
    image: timescale/timescaledb:latest-pg15
    # ... (existing config)

  backend:
    build: ./backend
    # ... (existing config)

  frontend:
    build: ./frontend
    container_name: meteoscore-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
    networks:
      - meteoscore-network

networks:
  meteoscore-network:
    driver: bridge
```

**Build Scripts:**

```json
// package.json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit"
  }
}
```

**And** production build is optimized:
- JavaScript minified and tree-shaken
- CSS purged (unused Tailwind classes removed)
- Assets fingerprinted for cache busting
- Vendor chunks separated for better caching
- Gzip compression enabled

**And** build size is validated:
- Total bundle size < 500 KB (gzipped)
- Initial load < 200 KB
- Lighthouse performance score > 90

**And** deployment process is documented:

```bash
# Build and deploy
docker-compose build frontend
docker-compose up -d frontend

# Verify deployment
curl http://localhost/
```

**Definition of Done:**
- [ ] Vite production build configured
- [ ] Nginx configuration with gzip and caching
- [ ] Multi-stage Dockerfile for frontend
- [ ] Docker Compose integration
- [ ] Build scripts in package.json
- [ ] Bundle size < 500 KB gzipped
- [ ] Lighthouse performance > 90
- [ ] Manual test: Production build serves correctly
- [ ] SPA routing works with Nginx try_files
---

## Epic 5: Admin Dashboard & Collection Monitoring

### Epic Overview

**Goal:** Provide admin-only access to monitor and control the data collection pipeline, including viewing collection history, triggering manual collections, and toggling the automatic scheduler.

**Value:** Enables the admin to monitor system health, debug collection issues, and manually intervene when needed without direct server access.

**Dependencies:** Epics 1-4 complete (scheduler and collection infrastructure exists)

**Authentication:** Basic Auth on /api/admin/* and /admin/* routes

---

### Story 5.1: Backend Admin API with Basic Auth

**As an** admin,
**I want** protected API endpoints for scheduler control and collection history,
**So that** only I can access sensitive system information and trigger collections.

#### Acceptance Criteria:

**Given** an unauthenticated request to /api/admin/*
**When** no Basic Auth header is provided
**Then** return 401 Unauthorized

**Given** valid Basic Auth credentials
**When** requesting /api/admin/scheduler/status
**Then** return current scheduler status, jobs, and recent execution history

**Given** valid Basic Auth credentials
**When** POST to /api/admin/scheduler/toggle
**Then** start or stop the scheduler at runtime

**Given** valid Basic Auth credentials
**When** POST to /api/admin/collect/forecasts or /api/admin/collect/observations
**Then** trigger immediate collection and return results

**Implementation Notes:**
- Use FastAPI HTTPBasic dependency
- Credentials from environment: ADMIN_USERNAME, ADMIN_PASSWORD
- Extend existing scheduler routes under /api/admin prefix
- Track execution history (last N executions, not just last one)

**Definition of Done:**
- [ ] Basic Auth middleware on /api/admin/* routes
- [ ] GET /api/admin/scheduler/status - extended status with history
- [ ] GET /api/admin/scheduler/jobs - list scheduled jobs
- [ ] POST /api/admin/scheduler/toggle - start/stop scheduler
- [ ] POST /api/admin/collect/forecasts - trigger forecast collection
- [ ] POST /api/admin/collect/observations - trigger observation collection
- [ ] Environment variables for credentials
- [ ] Unit tests for auth and endpoints

---

### Story 5.2: Frontend Admin Dashboard Page

**As an** admin,
**I want** a web interface to view collection status and control the scheduler,
**So that** I can monitor and manage the system without using CLI tools.

#### Acceptance Criteria:

**Given** I navigate to /admin
**When** not authenticated
**Then** browser shows Basic Auth prompt

**Given** valid credentials
**When** viewing /admin page
**Then** I see:
- Scheduler status (running/stopped)
- Next scheduled collection times
- Recent collection history (last 10 executions per job type)
- Manual trigger buttons
- Scheduler on/off toggle

**Given** I click "Trigger Forecasts"
**When** collection runs
**Then** show loading state, then updated status

**Implementation Notes:**
- Basic Auth handled by browser natively
- Use existing Solid.js patterns
- Fetch from /api/admin/* endpoints
- Simple, functional UI (no need for fancy design)

**Definition of Done:**
- [ ] /admin route in Solid.js router
- [ ] AdminPage component with scheduler status
- [ ] Collection history table
- [ ] Manual trigger buttons with loading states
- [ ] Scheduler toggle switch
- [ ] Auto-refresh status every 30s
- [ ] Error handling for failed requests
- [ ] Nginx config allows /admin route (SPA fallback)

