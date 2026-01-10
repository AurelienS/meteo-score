---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - "product-brief-meteo-score-2026-01-10.md"
  - "ux-design-specification.md"
  - "research/technical-data-sources-planfoy-research-2026-01-10.md"
  - "analysis/brainstorming-session-2026-01-10.md"
workflowType: 'architecture'
project_name: 'meteo-score'
user_name: 'boss'
date: '2026-01-10'
lastStep: 8
status: 'complete'
completedAt: '2026-01-10'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context

**Project:** MétéoScore - Open-source weather forecast accuracy comparison platform for paragliding

**Vision:** Provide paragliders with actionable insights into forecast accuracy by characterizing contextual biases rather than abstract scores.

**MVP Scope:**
- **Geographic:** 1 site (Passy Plaine Joux)
- **Models:** 2 weather models (AROME, Meteo-Parapente)
- **Parameters:** Wind (speed + direction) + Temperature
- **Timeline:** 90 days data collection
- **Success Criteria:** >90% pipeline uptime

**Key Architectural Insight:**
Rather than storing complete raw forecast/observation data, the system stores only **deviations/écarts** (forecast vs observation), enabling 100x more compact storage while focusing on the user-valuable insight: characterizing how each model tends to over/underestimate by context (site, horizon, parameter).

## Input Documents Analyzed

This architecture incorporates decisions and context from:

1. **Product Brief** (323 lines) - Product vision, MVP scope, user needs
2. **UX Design Specification** (4127 lines) - UI/UX patterns, components, design system
3. **Technical Research** (1972 lines) - Data sources, APIs, technology evaluations, ADRs
4. **Brainstorming Session** (1434 lines) - 50+ architectural decisions via morphological analysis, first principles thinking, and constraint mapping

---

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

The MétéoScore platform must provide:

1. **Automated Forecast Collection**
   - Multi-source ingestion: AROME (Météo-France GRIB2), Meteo-Parapente (JSON API)
   - Schedule: 4x daily collection
   - Parameters: Wind speed (km/h) + direction (0-360°), Temperature (°C)
   - Forecast horizons: H+6, H+24, H+48
   - Geographic: Initially 1 site (Passy Plaine Joux), scalable to 4-5 sites in MVP

2. **Automated Observation Collection**
   - Beacon networks: ROMMA (ID 241 Passy), FFVL balisemeteo.com (ID 2834 Varan)
   - Schedule: 6x daily (8h-18h window)
   - Same parameters as forecasts for direct comparison
   - Scraping and/or API integration depending on source

3. **Deviation Calculation Engine**
   - Core business logic: Calculate écarts (forecast_value - observed_value)
   - Store only deviations (not full raw data) for 100x storage optimization
   - Compute per: timestamp, site, model, parameter, horizon
   - Enable contextual bias analysis: "AROME overestimates wind by +10 km/h at Passy at H+6"

4. **Historical Time-Series Storage**
   - Minimum 90 days of deviation history
   - TimescaleDB hypertables for time-partitioned efficiency
   - Continuous aggregates for precomputed metrics (daily/weekly MAE)

5. **Web Visualization Interface**
   - Compare multiple models side-by-side
   - Filter by site, model, parameter, time range, forecast horizon
   - Display contextual bias patterns (actionable insights)
   - Responsive design (mobile + desktop)
   - 12 custom Solid.js components: SiteMap, SiteSearch, VerdictHeader, ComparisonTable, DeviationChart, etc.

6. **Contextual Bias Characterization**
   - Key user value: Not abstract scores but actionable patterns
   - Example: "AROME tends to overestimate wind by 10 km/h at this site at H+6"
   - Users can mentally correct forecasts based on learned patterns

**Non-Functional Requirements:**

1. **Reliability**
   - Pipeline uptime: >90% (success criterion)
   - Automated scheduling with APScheduler (MVP) or Celery (scale)
   - Graceful handling of API failures, missing data, parsing errors

2. **Performance**
   - Forecast collection: 4x daily without rate limit violations (AROME: 50 req/min)
   - Observation collection: 6x daily (8h-18h)
   - API response time: <2s for typical queries
   - Frontend load time: <3s initial, <1s navigation

3. **Scalability**
   - POC: 1 model + 1 site + 1 beacon
   - MVP: 2 models + 4-5 sites
   - Vision: 10+ models + 50+ sites
   - Architecture must support horizontal scaling (add sites/models without refactoring)

4. **Data Integrity**
   - 6-level validation strategy:
     1. Manual validation of initial samples
     2. Unit tests on parsers (>80% coverage)
     3. Automated alerts on aberrant values (wind >200 km/h, temp <-50°C)
     4. Cross-validation between multiple observation sources
     5. Validation against historical beacon patterns
     6. Iterative improvement ("ship and iterate" approach)

5. **Maintainability**
   - Modular collector architecture (one collector per data source)
   - Comprehensive test coverage (>80% with pytest)
   - TDD approach for data parsing
   - CI/CD: GitHub Actions (automated tests + deployment)
   - Infrastructure as code: Docker + Docker Compose

6. **Accessibility**
   - WCAG 2.1 Level AA compliance (from UX spec)
   - Semantic HTML, ARIA labels, keyboard navigation
   - Screen reader support
   - Sufficient color contrast, focus indicators

7. **Security**
   - MVP: Public data sources, no authentication required
   - Rate limiting on API to prevent abuse
   - HTTPS via Let's Encrypt (Traefik reverse proxy)

**Scale & Complexity:**

- **Primary domain:** Full-stack web application (data pipeline + REST API + frontend)
- **Complexity level:** Medium (substantial but manageable with clear boundaries)
- **Estimated architectural components:** 8-10 major components
  - Forecast collectors (modular, 1 per source)
  - Observation collectors (modular, 1 per source)
  - Deviation calculation engine
  - TimescaleDB with hypertables
  - FastAPI REST API
  - Solid.js frontend with 12 custom components
  - APScheduler orchestration
  - Logging/monitoring infrastructure

### Technical Constraints & Dependencies

**External API Constraints:**

- **AROME (Météo-France):** GRIB2 format, 50 requests/min rate limit, requires cfgrib parsing library
- **Meteo-Parapente:** JSON API `https://data0.meteo-parapente.com/data.php`, simpler format
- **ROMMA Beacons:** May require scraping or direct contact for API access (station 241 Passy)
- **FFVL balisemeteo.com:** Scraping required (Varan ID 2834), HTML parsing with BeautifulSoup4

**Data Format Heterogeneity:**

- GRIB2: Binary, requires specialized parsing (cfgrib + xarray)
- JSON: Standard, easy to parse
- HTML: Requires scraping and DOM parsing
- Architecture must abstract format differences behind common interface

**Geographic & Temporal:**

- **Geographic scope:** France (Alps, Pyrénées pilot sites)
- **Time zones:** Handle UTC ↔ local conversions properly
- **Beacon coverage:** Limited to existing networks (ROMMA, FFVL, PiouPiou, Spotair)
- **MVP sites:** Passy Plaine Joux (lat: 45.947, lon: 6.7391) + 3-4 others

**Technology Stack (from Technical Research ADRs):**

- **Backend:** Python 3.11+, FastAPI (web framework), SQLAlchemy (ORM), Pydantic (validation)
- **Database:** TimescaleDB (PostgreSQL 15 extension)
- **Data processing:** pandas, xarray, cfgrib, requests, BeautifulSoup4
- **Scheduling:** APScheduler (MVP) → Celery Beat (scale)
- **Deployment:** Docker, Docker Compose, Traefik, Let's Encrypt
- **Frontend:** Solid.js, Tailwind CSS, Geist typography
- **Testing:** pytest, pytest-cov, FastAPI TestClient
- **CI/CD:** GitHub Actions

### Cross-Cutting Concerns Identified

1. **Scheduling & Orchestration**
   - Forecast collection: 4x daily (e.g., 06:00, 12:00, 18:00, 00:00 UTC)
   - Observation collection: 6x daily (8h-18h, every 2 hours)
   - APScheduler for MVP (simple cron-like), Celery for production scale
   - Idempotency: Handle retries without data duplication

2. **Error Handling & Resilience**
   - API failures: Exponential backoff, retry logic
   - Data parsing errors: Log and skip malformed data, alert on high error rates
   - Missing observations: Handle gracefully (forecasts without matching observations)
   - Circuit breaker pattern for external APIs

3. **Logging & Monitoring**
   - Structured logging (Python logging module with JSON formatter)
   - External monitoring: UptimeRobot (uptime checks), Healthchecks.io (cron monitoring)
   - Metrics: Collection success rate, API response times, deviation calculation times
   - Alerting: Email/webhook on pipeline failures, aberrant data values

4. **Data Validation & Quality**
   - **Level 1:** Manual validation of initial samples (human review)
   - **Level 2:** Unit tests on parsers (>80% coverage, TDD)
   - **Level 3:** Automated alerts on aberrant values (wind >200, temp <-50)
   - **Level 4:** Cross-validation between multiple observation sources when available
   - **Level 5:** Historical comparison (does new data fit established patterns?)
   - **Level 6:** Ship-and-iterate (publish without publicity to allow error margin)

5. **Time-Series Data Management**
   - TimescaleDB hypertables (time-partitioned tables for efficient queries)
   - Continuous aggregates (precomputed daily/weekly MAE metrics)
   - Retention policy: Initially unlimited, consider rolling window (e.g., 2 years) later
   - Index strategy: Optimize for queries by (site, model, parameter, time_range)

6. **API Design & Consistency**
   - RESTful API for frontend consumption
   - Endpoints: `/sites`, `/models`, `/parameters`, `/deviations`, `/bias-summary`
   - Pagination for large datasets
   - Query filters: site_id, model_id, parameter_id, start_date, end_date, horizon
   - JSON responses with consistent error format

7. **Deployment & Infrastructure**
   - Docker containers: `postgres` (TimescaleDB), `meteo-score` (app), `adminer` (DB admin)
   - Docker Compose for local dev + production
   - Traefik reverse proxy (automatic HTTPS, Let's Encrypt)
   - Environment-based config (dev/staging/prod)
   - Health check endpoints for monitoring

8. **Testing Strategy**
   - Unit tests: Data parsers, deviation calculator, API endpoints (>80% coverage)
   - Integration tests: End-to-end pipeline (collect → parse → store → retrieve)
   - Manual validation: Initial POC samples reviewed by domain expert (user)
   - TDD approach: Write tests before implementing data collectors
   - CI: Automated test runs on every commit (GitHub Actions)

---

## Starter Template Evaluation

### Primary Technology Domain

**Full-stack web application** with specialized data pipeline architecture for weather forecast deviation analysis.

**Key Characteristics:**
- Data pipeline with modular collectors (GRIB2, JSON, HTML scraping)
- Time-series database (TimescaleDB) with custom hypertables
- Public data platform (no authentication required)
- Self-hosted infrastructure (no external services)

### Starter Options Considered

**Backend Options Evaluated:**

1. **benavlabs/FastAPI-boilerplate** - Production-ready async FastAPI with SQLAlchemy 2.0, Pydantic V2, Docker Compose, PostgreSQL. Strong technical foundation but includes authentication/permissions systems, JWT middleware, and user management not needed for public data MVP.

2. **fastapi-template-cli** - CLI-generated FastAPI projects with flexible ORM and authentication options. Similar issue: assumes multi-tenant or authenticated API patterns.

3. **teamhide/fastapi-boilerplate** - Real-world production boilerplate with caching and permissions. Again, over-engineered for public read-only data platform.

**Frontend Options Evaluated:**

1. **Official SolidJS + Tailwind template** (`npx degit solidjs/templates/vanilla/with-tailwindcss`) - Minimal, official template with Vite + Tailwind CSS + TypeScript. Clean starting point without opinions, but doesn't include Geist typography or custom component structure.

2. **AR10Dev/solid-tailwind-ts-vite** - Community template with ESLint + Prettier pre-configured. More tooling but still generic structure.

3. **Flowbite SolidJS starter** - Includes pre-built UI component library. Too opinionated for the 12 custom components specified in UX design.

**Verdict:** All evaluated starters provide value for generic CRUD applications, but none align with MétéoScore's specialized architecture.

### Selected Approach: Custom Structure

**Rationale for Selection:**

A **custom project structure** is the optimal choice over pre-built starters for these reasons:

1. **No Authentication Required**: Public weather data platform doesn't need user management, JWT tokens, role-based access control, or session handling that all evaluated starters include by default. Removing unused auth code would take as long as building clean.

2. **No External Services**: Self-hosted infrastructure requirement eliminates value of starters that assume cloud services (S3, CloudWatch, external auth providers, SaaS monitoring). Everything runs in Docker Compose.

3. **Project-Specific Architecture**:
   - **Modular collectors** (1 per data source: AROME GRIB2, Meteo-Parapente JSON, ROMMA scraping)
   - **Deviation calculator engine** (core business logic: forecast - observation)
   - **TimescaleDB hypertables** with continuous aggregates (non-standard PostgreSQL usage)
   - **APScheduler** for 4x/6x daily collection (not typical API background jobs)

4. **Simplified Storage Model**: Brainstorming session breakthrough - "store only deviations, not raw data" (100x storage reduction). Standard boilerplates assume full data persistence with CRUD operations. This insight fundamentally changes database schema design.

5. **First Principles Alignment**: Custom structure honors the "simplify from first principles" approach that eliminated complex ETL pipelines. Boilerplate code contradicts this philosophy.

6. **12 Custom Components**: UX design specifies purpose-built components (SiteMap, VerdictHeader, ComparisonTable, BiasIndicator, DeviationChart) that don't map to generic UI component libraries.

7. **Learning & Control**: Full understanding of every line of code supports "ship and iterate" approach with 6-level validation strategy. No hidden abstractions or magic.

**Initialization Commands:**

```bash
# Project initialization
mkdir meteo-score && cd meteo-score

# Backend setup
mkdir -p backend/{collectors,core,api,db,scheduler,tests}
cd backend
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows
pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy pydantic pydantic-settings \
            psycopg2-binary pandas xarray cfgrib requests beautifulsoup4 \
            apscheduler alembic python-dotenv \
            pytest pytest-cov pytest-asyncio httpx

# Create requirements.txt
pip freeze > requirements.txt

# Frontend setup
cd ../
npx degit solidjs/templates/ts frontend
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install geist

# Docker setup
cd ../
touch docker-compose.yml .env.example .gitignore README.md
```

**Architectural Decisions Established by Custom Structure:**

**Language & Runtime:**

- **Backend:** Python 3.11+ with full type hints (Pydantic V2 for validation)
- **Frontend:** TypeScript 5.0+ with Solid.js reactive primitives
- **Async everywhere:** Backend uses `async`/`await` for I/O operations (API calls, database queries)
- Virtual environments: Python `venv` for isolation, `node_modules` for frontend

**Project Organization:**

```
meteo-score/
├── backend/
│   ├── collectors/                 # Modular data collectors (Strategy pattern)
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract Collector interface
│   │   ├── arome.py               # AROME GRIB2 collector (cfgrib + xarray)
│   │   ├── meteo_parapente.py    # Meteo-Parapente JSON API collector
│   │   ├── romma.py               # ROMMA beacon scraper (BeautifulSoup4)
│   │   └── ffvl.py                # FFVL balisemeteo scraper
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py              # SQLAlchemy models (Site, Model, Parameter, Deviation)
│   │   ├── schemas.py             # Pydantic schemas for API request/response
│   │   ├── deviation_engine.py    # Core business logic (forecast - observation)
│   │   ├── database.py            # Database session management
│   │   └── config.py              # Pydantic Settings (env vars)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI app initialization
│   │   ├── dependencies.py        # Dependency injection (DB session)
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── sites.py           # GET /sites, GET /sites/{id}
│   │       ├── models.py          # GET /models
│   │       ├── parameters.py      # GET /parameters
│   │       ├── deviations.py      # GET /deviations (with filters)
│   │       └── bias_summary.py    # GET /bias-summary (aggregated stats)
│   ├── db/
│   │   ├── migrations/            # Alembic migration scripts
│   │   │   ├── versions/
│   │   │   └── env.py
│   │   └── init_hypertables.sql   # TimescaleDB extension + hypertable setup
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── jobs.py                # APScheduler job functions
│   │   └── scheduler.py           # Scheduler initialization (4x/6x daily)
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py            # Pytest fixtures
│   │   ├── test_collectors.py     # TDD for data parsers (>80% coverage)
│   │   ├── test_deviation.py      # Unit tests for core deviation logic
│   │   └── test_api.py            # Integration tests (FastAPI TestClient)
│   ├── main.py                    # Entry point (run scheduler + API)
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/            # 12 custom Solid.js components
│   │   │   ├── SiteMap.tsx        # Interactive map (Leaflet or Mapbox)
│   │   │   ├── SiteSearch.tsx     # Search/filter sites
│   │   │   ├── VerdictHeader.tsx  # Summary verdict for model accuracy
│   │   │   ├── ComparisonTable.tsx # Side-by-side model comparison
│   │   │   ├── DeviationChart.tsx  # Time-series deviation visualization
│   │   │   ├── ModelCard.tsx       # Model info card
│   │   │   ├── BiasIndicator.tsx   # Visual bias representation
│   │   │   ├── ParameterSelector.tsx
│   │   │   ├── HorizonSelector.tsx
│   │   │   ├── DateRangePicker.tsx
│   │   │   ├── LoadingState.tsx
│   │   │   └── ErrorState.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx           # Landing page with site map
│   │   │   ├── SiteDetail.tsx     # Individual site detail + comparisons
│   │   │   └── About.tsx          # About project, methodology
│   │   ├── lib/
│   │   │   ├── api.ts             # Typed API client (fetch wrapper)
│   │   │   └── types.ts           # TypeScript interfaces
│   │   ├── styles/
│   │   │   └── index.css          # Tailwind directives + Geist fonts
│   │   ├── App.tsx                # Router + layout
│   │   └── index.tsx              # Entry point
│   ├── public/
│   │   └── favicon.ico
│   ├── tailwind.config.js         # Tailwind + Geist typography
│   ├── postcss.config.js
│   ├── vite.config.ts             # Vite with Solid plugin
│   ├── tsconfig.json
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml             # postgres (timescaledb), backend, frontend, adminer
├── .env.example                   # Environment variables template
├── .gitignore
└── README.md
```

**Styling Solution:**

- **Framework:** Tailwind CSS 4.0 (utility-first)
- **Typography:** Geist Sans (UI text) + Geist Mono (code/numbers)
- **Configuration:** Custom breakpoints (640px, 768px, 1024px) from UX spec
- **Approach:** Mobile-first responsive design, WCAG 2.1 AA contrast ratios

**Build Tooling:**

- **Backend:** No build step (interpreted Python), Docker multi-stage builds for production optimization
- **Frontend:** Vite with `vite-plugin-solid`, esbuild for fast TS transpilation, tree-shaking in production
- **Hot Reload:** `uvicorn --reload` (backend), Vite HMR (frontend)

**Testing Framework:**

- **Backend:**
  - `pytest` with `pytest-cov` (>80% coverage target)
  - `pytest-asyncio` for async test support
  - `httpx` for FastAPI TestClient
  - TDD approach: Write tests BEFORE implementing data collectors (critical for data validation)

- **Frontend:**
  - Vitest (Vite-native, fast)
  - `@solidjs/testing-library` for component tests
  - Manual validation: Initial POC samples reviewed by domain expert (user)

**Code Quality:**

- **Backend:** `ruff` (fast Python linter), `black` (formatter), `mypy` (type checking)
- **Frontend:** ESLint with TypeScript rules, Prettier for formatting
- Pre-commit hooks: Format + lint before commit

**Database Architecture:**

- **Base:** PostgreSQL 15
- **Extension:** TimescaleDB 2.13+ (`CREATE EXTENSION timescaledb;`)
- **Hypertables:** `deviations` table partitioned by `timestamp` column
- **Continuous Aggregates:** Precomputed views for daily/weekly MAE metrics
- **Migrations:** Alembic for schema version control
- **Connection:** Async SQLAlchemy with connection pooling

**Schema Example:**

```sql
-- Created via Alembic migration
CREATE TABLE deviations (
    id SERIAL,
    timestamp TIMESTAMPTZ NOT NULL,
    site_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,
    parameter_id INTEGER NOT NULL,
    horizon INTEGER NOT NULL,  -- H+6, H+24, H+48
    forecast_value DOUBLE PRECISION NOT NULL,
    observed_value DOUBLE PRECISION NOT NULL,
    deviation DOUBLE PRECISION NOT NULL,  -- forecast - observed
    PRIMARY KEY (timestamp, site_id, model_id, parameter_id, horizon)
);

-- Convert to hypertable (TimescaleDB)
SELECT create_hypertable('deviations', 'timestamp', chunk_time_interval => INTERVAL '7 days');

-- Continuous aggregate for daily MAE
CREATE MATERIALIZED VIEW daily_mae
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS day,
    site_id, model_id, parameter_id, horizon,
    AVG(ABS(deviation)) AS mae
FROM deviations
GROUP BY day, site_id, model_id, parameter_id, horizon;
```

**API Design:**

- **Style:** RESTful JSON API
- **Endpoints:**
  - `GET /sites` - List all sites
  - `GET /sites/{id}` - Site details
  - `GET /models` - List all models
  - `GET /parameters` - List all parameters
  - `GET /deviations?site_id=1&model_id=2&start_date=2025-01-01&end_date=2025-01-10` - Query deviations with filters
  - `GET /bias-summary?site_id=1&model_id=2&parameter_id=1&horizon=6` - Aggregated bias stats (MAE, bias direction)
- **Pagination:** Cursor-based for large result sets
- **Response Format:**
  ```json
  {
    "data": [...],
    "meta": {"total": 100, "page": 1}
  }
  ```
- **Error Format:**
  ```json
  {
    "error": "ValidationError",
    "detail": "Invalid date range"
  }
  ```

**Scheduling & Orchestration:**

- **Tool:** APScheduler (in-process, simple for MVP)
- **Forecast Collection:** CronTrigger 4x daily (06:00, 12:00, 18:00, 00:00 UTC)
- **Observation Collection:** CronTrigger 6x daily (08:00, 10:00, 12:00, 14:00, 16:00, 18:00 local time)
- **Idempotency:** Check if forecast/observation already exists before inserting
- **Error Handling:** Log failures, retry with exponential backoff, alert on high error rates

**Development Experience:**

- **Backend Dev Server:** `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- **Frontend Dev Server:** `npm run dev` (Vite on port 5173)
- **Docker Compose:** Mirrors production environment locally
- **Debugging:** Python debugger (pdb/ipdb), VS Code launch configs, Solid.js DevTools
- **Environment Variables:** `.env` files with `pydantic-settings` for type-safe config

**Deployment:**

```yaml
# docker-compose.yml structure
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_USER: meteoscore
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: meteoscore
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/db/init_hypertables.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    command: python main.py
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql+asyncpg://meteoscore:${DB_PASSWORD}@postgres:5432/meteoscore
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app  # Dev only

  frontend:
    build: ./frontend
    depends_on:
      - backend
    ports:
      - "3000:3000"

  traefik:
    image: traefik:v2.10
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - letsencrypt:/letsencrypt

  adminer:
    image: adminer:latest
    depends_on:
      - postgres
    ports:
      - "8080:8080"

volumes:
  postgres_data:
  letsencrypt:
```

**Self-Hosted Infrastructure:**

- ✅ No external auth providers (no Auth0, Clerk, Supabase Auth)
- ✅ No external databases (no PlanetScale, Neon, AWS RDS)
- ✅ No external monitoring (no Datadog, New Relic - use self-hosted alternatives)
- ✅ No external logging (Python logging to stdout, Docker logs)
- ✅ No CDN dependencies (static assets served by Traefik/Nginx)
- ✅ All services run in Docker Compose (local dev = production parity)

**Note:** Project initialization using these commands should be the **first implementation story**. The custom structure provides maximum flexibility for the specialized weather data pipeline while establishing clear separation of concerns and avoiding unnecessary authentication/authorization complexity.

---

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**

All critical architectural decisions have been established through prior research, brainstorming, and starter template evaluation:
- Backend stack: Python 3.11+, FastAPI, SQLAlchemy, Pydantic
- Frontend stack: TypeScript, Solid.js, Tailwind CSS, Geist fonts
- Database: TimescaleDB (PostgreSQL 15 extension)
- Architecture pattern: Monolithic with modular collectors
- Storage model: Deviations only (100x reduction vs full data)
- Deployment: Docker Compose, self-hosted infrastructure

**Important Decisions (Shape Architecture):**

Decisions made collaboratively in this session:
- No caching layer for MVP (TimescaleDB continuous aggregates sufficient)
- No formal API documentation for MVP (code as documentation)
- Frontend state: Solid Router + native Signals
- Monitoring: Python logging to stdout + Docker logs
- Visualization: D3.js for custom deviation charts
- Error handling: Exception-based (Python standard, FastAPI HTTPException)

**Deferred Decisions (Post-MVP):**

- Interactive map (SiteMap.tsx): Deferred until multi-site expansion (currently 1 site POC)
- External caching (Redis): Re-evaluate if performance issues arise
- Observability stack (Grafana/Loki/Prometheus): Add when monitoring needs grow
- API documentation: Add OpenAPI/Swagger if external consumers need it
- Advanced state management: Current signals approach scales to 12 components

### Data Architecture

**Database: TimescaleDB 2.13+ (PostgreSQL 15)**

- **Rationale:** Time-series optimized database essential for 90+ days of deviation history with efficient querying by time ranges
- **Version:** PostgreSQL 15 with TimescaleDB latest (verified via Docker image `timescale/timescaledb:latest-pg15`)
- **Key Features Used:**
  - Hypertables for automatic time-based partitioning (`deviations` table chunked by 7-day intervals)
  - Continuous aggregates for pre-computed MAE metrics (daily/weekly)
  - Native SQL compatibility (no ORM limitations)
- **Migration Strategy:** Alembic for schema versioning, SQL scripts for TimescaleDB-specific features
- **Connection:** Async SQLAlchemy with connection pooling (asyncpg driver)

**Data Modeling Approach: Minimal Storage (Deviations Only)**

- **Rationale:** Brainstorming breakthrough - store `forecast_value`, `observed_value`, `deviation` only, not full raw forecast/observation datasets (100x storage reduction)
- **Schema Design:**
  - Composite primary key: `(timestamp, site_id, model_id, parameter_id, horizon)`
  - Indexes optimized for queries: site, model, parameter, time_range filters
  - Foreign keys: sites, models, parameters reference tables
- **Data Types:** `TIMESTAMPTZ` for timezone-aware timestamps, `DOUBLE PRECISION` for weather values
- **Retention Policy:** Initially unlimited, revisit after 1 year of production data

**Caching Strategy: No External Cache for MVP**

- **Decision:** No Redis or external caching layer
- **Rationale:**
  - TimescaleDB continuous aggregates already pre-compute expensive metrics (daily/weekly MAE)
  - MVP with 1 site + 2 models = low query volume
  - "Ship and iterate" approach - add caching only if performance issues arise
  - Reduces infrastructure complexity (fewer Docker containers, no cache invalidation logic)
- **Future Consideration:** Add Redis when scaling to 10+ models × 50+ sites

**Data Validation Strategy: 6-Level Approach**

From brainstorming session, implemented progressively:

1. **Manual Validation:** Human review of initial POC samples (first week of data)
2. **Unit Tests:** pytest for data parsers, >80% coverage, TDD approach
3. **Automated Alerts:** Flag aberrant values (wind >200 km/h, temp <-50°C, deviation >100)
4. **Cross-Validation:** Compare multiple observation sources when available (ROMMA vs FFVL)
5. **Historical Comparison:** Statistical outlier detection against historical patterns
6. **Ship-and-Iterate:** Deploy without publicity initially, margin for error correction

### Authentication & Security

**Authentication: None (Public Data Platform)**

- **Decision:** No user authentication system
- **Rationale:**
  - All weather data is public (AROME, Meteo-Parapente, ROMMA beacons)
  - No user accounts, no login, no sessions
  - Read-only API for frontend consumption
  - Eliminates entire auth/authorization complexity from MVP
- **Security Focus:** API rate limiting (prevent abuse), input validation (Pydantic schemas)

**API Security Strategy: Rate Limiting + Input Validation**

- **Rate Limiting:** FastAPI middleware (e.g., `slowapi`) - 100 requests/minute per IP for MVP
- **Input Validation:** Pydantic schemas enforce types, ranges, date formats
- **SQL Injection:** Prevented by SQLAlchemy parameterized queries
- **CORS:** Configured for frontend origin only
- **HTTPS:** Traefik with Let's Encrypt automatic certificates

**Data Security: Public Data, No Encryption at Rest**

- **Rationale:** All stored data (deviations) derived from public sources
- **Transport Security:** HTTPS for all communications (Traefik TLS termination)
- **Database Access:** PostgreSQL password-protected, not exposed publicly (Docker internal network)

### API & Communication Patterns

**API Design: RESTful JSON**

- **Style:** REST with resource-oriented endpoints
- **Endpoints:**
  - `GET /sites` - List all sites with metadata
  - `GET /sites/{id}` - Single site details
  - `GET /models` - List weather models
  - `GET /parameters` - List parameters (wind speed, direction, temp)
  - `GET /deviations` - Query deviations with filters (site, model, date range, horizon)
  - `GET /bias-summary` - Aggregated statistics (MAE, bias direction, count)
- **Query Parameters:** `site_id`, `model_id`, `parameter_id`, `horizon`, `start_date`, `end_date`
- **Pagination:** Cursor-based for `/deviations` (large datasets), limit to 1000 records per request

**API Response Format:**

```json
{
  "data": [...],
  "meta": {
    "total": 1523,
    "page": 1,
    "per_page": 100
  }
}
```

**Error Handling: Exception-Based (Python Standard)**

- **Decision:** Use Python exceptions with FastAPI HTTPException
- **Rationale:**
  - Idiomatic Python approach
  - FastAPI automatically converts exceptions to HTTP responses
  - Simple and well-documented
  - No need for functional Result types (adds verbosity without benefit)
- **Error Response Format:**
  ```json
  {
    "error": "ValidationError",
    "detail": "Invalid date range: start_date must be before end_date",
    "status_code": 400
  }
  ```
- **Exception Types:**
  - `ValidationError` (400) - Invalid input parameters
  - `NotFoundError` (404) - Resource not found
  - `RateLimitError` (429) - Too many requests
  - `InternalServerError` (500) - Unexpected errors

**API Documentation: No Formal Docs for MVP**

- **Decision:** No OpenAPI/Swagger UI, no manual documentation
- **Rationale:**
  - Code as documentation (Pydantic schemas self-document)
  - Single consumer (own frontend)
  - "Ship and iterate" - add docs if external consumers need it
  - Saves maintenance overhead
- **Note:** FastAPI generates OpenAPI schema automatically, can enable `/docs` endpoint later with zero effort

### Frontend Architecture

**State Management: Solid Router + Native Signals**

- **Decision:** Use `@solidjs/router` for navigation + Solid.js native primitives (createSignal, createStore) for state
- **Rationale:**
  - Navigation needed: Home → SiteDetail → About pages
  - Solid.js signals are reactive by design, no external state library needed
  - Application state is simple: API data, filter selections, loading states
  - 12 components with minimal shared state (site selection, date ranges)
- **State Categories:**
  - **Global:** Current site selection, date range filters (createStore in App.tsx)
  - **Local:** Component-specific (loading, errors) with createSignal
  - **API Data:** Fetched and stored in signals, passed via props or context
- **Library:** `@solidjs/router` (official Solid.js router)

**Component Architecture: Composition over Inheritance**

- **Pattern:** Functional components with props, no class components
- **Structure:** 12 custom components as specified in UX design
  - `SiteSearch.tsx` - Search/filter (deferred: list view for MVP)
  - `VerdictHeader.tsx` - Summary verdict
  - `ComparisonTable.tsx` - Side-by-side model comparison
  - `DeviationChart.tsx` - D3.js time-series visualization
  - `ModelCard.tsx`, `BiasIndicator.tsx`, `ParameterSelector.tsx`, etc.
- **Props:** Explicit prop passing, TypeScript interfaces for type safety
- **Reusability:** Extract common patterns (LoadingState, ErrorState) into shared components

**Routing Strategy: File-Based Conventions**

- **Routes:**
  - `/` - Home page (site list for MVP, map later)
  - `/sites/:id` - Site detail with comparisons
  - `/about` - Methodology explanation
- **Navigation:** `<A>` component from @solidjs/router
- **Data Loading:** Fetch in page components (no route-level data loaders for MVP)

**Visualization: D3.js for Custom Charts**

- **Decision:** Use D3.js for DeviationChart.tsx
- **Rationale:**
  - Full control over visualization design (critical for UX)
  - Custom time-series charts showing deviation patterns
  - Solid.js integrates well with D3 (manual DOM manipulation in refs)
  - Chart.js too opinionated for custom contextual bias visualizations
- **Chart Types:**
  - Line charts: Deviation over time per model
  - Scatter plots: Forecast vs observed values
  - Heatmaps: Bias by hour/horizon (future)
- **Responsive:** SVG-based, resize handlers for mobile

**Map Component: Deferred to Multi-Site Phase**

- **Decision:** No interactive map (SiteMap.tsx) for MVP
- **Rationale:**
  - POC has 1 site (Passy), map provides no value
  - Simple list view sufficient for MVP (4-5 sites)
  - Add Leaflet + OpenStreetMap when expanding to 10+ sites
- **Implementation Note:** Leaflet preferred when added (open-source, no API keys, self-hosted tiles)

**Bundle Optimization: Vite Defaults**

- **Code Splitting:** Vite automatic code splitting by route
- **Tree Shaking:** Enabled by default in production builds
- **Minification:** esbuild minification
- **Assets:** Vite asset optimization (images, fonts)
- **No Advanced Optimization for MVP:** Add lazy loading, prefetching if performance issues

### Infrastructure & Deployment

**Hosting Strategy: Self-Hosted VPS**

- **Decision:** Single VPS (Virtual Private Server) running Docker Compose
- **Rationale:**
  - No external services requirement (full control)
  - Cost-effective for MVP (€5-10/month)
  - Simple deployment (docker-compose up)
  - Local dev = production parity
- **Providers:** Hetzner, DigitalOcean, OVH (user choice)
- **Specs:** 2 vCPU, 4GB RAM, 50GB SSD (sufficient for 90 days data + TimescaleDB)

**CI/CD Pipeline: GitHub Actions**

- **Trigger:** Push to `main` branch
- **Steps:**
  1. Run backend tests (pytest)
  2. Run frontend tests (vitest)
  3. Build Docker images
  4. Deploy to VPS (SSH + docker-compose pull + restart)
- **Quality Gates:** Tests must pass (>80% coverage)
- **Secrets:** GitHub Secrets for VPS SSH keys, DB passwords
- **Deployment Strategy:** Rolling restart (brief downtime acceptable for MVP)

**Environment Configuration: .env Files**

- **Approach:** `.env` files per environment (dev, production)
- **Backend:** `pydantic-settings` for type-safe config loading
- **Variables:**
  - `DATABASE_URL` - PostgreSQL connection string
  - `API_RATE_LIMIT` - Requests per minute
  - `LOG_LEVEL` - DEBUG/INFO/WARNING/ERROR
  - `AROME_API_KEY` - If needed for Météo-France
- **Security:** `.env` not committed (`.gitignore`), `.env.example` as template

**Monitoring & Logging: Python Logging + Docker Logs**

- **Decision:** Python `logging` module to stdout/stderr, captured by Docker
- **Rationale:**
  - Simple, no external services
  - `docker logs` for viewing
  - Structured logging (JSON formatter) for parsing if needed
  - Sufficient for MVP with "ship and iterate" approach
- **Log Levels:**
  - `INFO`: Collector runs, API requests
  - `WARNING`: Parsing errors, missing data
  - `ERROR`: API failures, database errors
  - `CRITICAL`: Service crashes
- **External Monitoring (Optional):** UptimeRobot (free tier) for uptime checks, Healthchecks.io for cron monitoring
- **Future:** Add Grafana + Loki + Prometheus stack when observability needs grow

**Scaling Strategy: Vertical First, Horizontal Later**

- **MVP:** Single VPS, scale up (more CPU/RAM) if needed
- **Multi-Site Expansion:** Same monolith, add more collectors
- **Performance Bottleneck:** If TimescaleDB queries slow, add read replicas or move to dedicated DB server
- **Long-Term:** Consider splitting collectors into separate worker services (Celery) if scheduling becomes complex

### Decision Impact Analysis

**Implementation Sequence:**

1. **Week 1-2: Project Setup**
   - Initialize custom structure (backend + frontend folders)
   - Docker Compose with TimescaleDB
   - Alembic migrations for base schema
   - FastAPI skeleton with health check endpoint
   - Solid.js skeleton with @solidjs/router

2. **Week 2-3: POC Data Pipeline (Meteo-Parapente Collector)**
   - Implement `collectors/base.py` (abstract interface)
   - Implement `meteo_parapente.py` (simplest: JSON API)
   - Write TDD tests for parser
   - Implement `deviation_engine.py` (core logic)
   - Store deviations in TimescaleDB
   - Manual validation of first 48 hours data

3. **Week 3-4: Backend API**
   - Implement SQLAlchemy models (Site, Model, Parameter, Deviation)
   - Implement Pydantic schemas
   - Implement API routes (`/sites`, `/models`, `/deviations`, `/bias-summary`)
   - Exception handling middleware
   - Rate limiting
   - Integration tests

4. **Week 4-5: Scheduler**
   - APScheduler setup (4x daily forecasts, 6x daily observations)
   - Idempotency checks
   - Error handling and retry logic
   - Logging

5. **Week 5-7: Frontend MVP**
   - @solidjs/router setup (Home, SiteDetail, About routes)
   - API client (`lib/api.ts` with typed responses)
   - Basic components (VerdictHeader, ComparisonTable, BiasIndicator)
   - D3.js DeviationChart.tsx
   - Tailwind + Geist styling
   - Loading/Error states

6. **Week 7-8: Expansion**
   - AROME collector (GRIB2 parsing with cfgrib)
   - ROMMA/FFVL observation collectors (scraping)
   - Continuous aggregates (daily MAE)
   - Cross-validation between sources

7. **Week 8-9: Production Deployment**
   - GitHub Actions CI/CD pipeline
   - VPS setup (Docker Compose)
   - Traefik + Let's Encrypt HTTPS
   - Monitoring (UptimeRobot, Healthchecks.io)
   - Documentation (README)

**Cross-Component Dependencies:**

- **Database → Backend:** SQLAlchemy models depend on TimescaleDB hypertables being created first
- **Backend → Frontend:** Frontend API client depends on backend routes being implemented and tested
- **Collectors → Deviation Engine:** All collectors feed into common deviation calculation logic
- **Scheduler → Collectors:** APScheduler orchestrates when collectors run
- **Router → Components:** Page components (SiteDetail) depend on router params (site ID)
- **D3.js Charts → API Data:** DeviationChart depends on `/deviations` endpoint returning time-series data
- **Continuous Aggregates → Bias Summary:** `/bias-summary` endpoint queries pre-computed MAE views

**Risk Mitigation:**

- **GRIB2 Parsing Complexity:** Start with Meteo-Parapente (JSON) to validate pipeline before tackling AROME GRIB2
- **Observation Source Reliability:** Test both ROMMA and FFVL, choose most reliable for POC
- **TimescaleDB Learning Curve:** Use PostgreSQL patterns first, add hypertables/aggregates after basic schema works
- **D3.js Complexity:** Start with simple line chart, iterate to custom visualizations

---

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 8 major areas where AI agents could make incompatible choices without explicit patterns.

These patterns ensure all AI agents (human or AI-assisted) implement code that integrates seamlessly across the monolithic architecture with modular collectors.

---

### Naming Patterns

**Database Naming Conventions:**

- **Tables:** `snake_case` plural - `deviations`, `sites`, `models`, `parameters`
- **Columns:** `snake_case` - `site_id`, `model_id`, `forecast_value`, `created_at`
- **Primary Keys:** `id` (implicit in composite keys like `(timestamp, site_id, model_id, ...)`)
- **Foreign Keys:** `{referenced_table_singular}_id` - `site_id`, `model_id`, `parameter_id`
- **Indexes:** `idx_{table}_{columns}` - `idx_deviations_site_model`, `idx_sites_name`
- **Constraints:** `{table}_{column}_{type}` - `deviations_deviation_check`, `sites_latitude_range`

**Examples:**
```sql
-- ✅ Good
CREATE TABLE deviations (
    id SERIAL,
    timestamp TIMESTAMPTZ NOT NULL,
    site_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,
    forecast_value DOUBLE PRECISION
);

CREATE INDEX idx_deviations_timestamp ON deviations(timestamp);

-- ❌ Bad
CREATE TABLE Deviation (
    ID SERIAL,
    TimeStamp TIMESTAMPTZ,
    SiteID INTEGER,
    forecastValue DOUBLE PRECISION
);
```

**API Naming Conventions:**

- **Endpoints:** RESTful plural nouns - `/sites`, `/models`, `/deviations`, `/parameters`
- **Resource IDs:** `/sites/{id}` (numeric IDs, not UUIDs for MVP)
- **Query Parameters:** `camelCase` - `siteId`, `modelId`, `startDate`, `endDate`, `forecastHorizon`
- **Actions (if needed):** Verbs at end - `/deviations/export` (prefer POST/GET verbs over URL verbs)
- **Aggregations:** Descriptive nouns - `/bias-summary` (not `/getBiasSummary`)

**Examples:**
```
✅ Good
GET /sites
GET /sites/1
GET /deviations?siteId=1&modelId=2&startDate=2026-01-01&endDate=2026-01-10
GET /bias-summary?siteId=1&modelId=2&parameterId=1&horizon=6

❌ Bad
GET /site
GET /getSite/1
GET /deviations?site_id=1&model_id=2&start_date=2026-01-01
GET /getBiasSummary?site_id=1
```

**Code Naming Conventions:**

**Backend Python:**
- **Modules:** `snake_case` - `meteo_parapente.py`, `deviation_engine.py`, `base.py`
- **Classes:** `PascalCase` - `MeteoParapenteCollector`, `DeviationEngine`, `Site`
- **Functions:** `snake_case` - `collect_forecast()`, `calculate_deviation()`, `get_sites()`
- **Variables:** `snake_case` - `forecast_value`, `observed_value`, `site_id`
- **Constants:** `UPPER_SNAKE_CASE` - `MAX_RETRIES`, `API_TIMEOUT`, `DEFAULT_HORIZON`
- **Private:** Leading underscore - `_parse_grib2()`, `_validate_coordinates()`

**Frontend TypeScript:**
- **Components:** `PascalCase.tsx` - `DeviationChart.tsx`, `VerdictHeader.tsx`, `SiteSearch.tsx`
- **Utilities:** `camelCase.ts` - `api.ts`, `types.ts`, `formatters.ts`
- **Functions:** `camelCase` - `fetchDeviations()`, `formatDate()`, `calculateMae()`
- **Variables:** `camelCase` - `forecastValue`, `observedValue`, `siteId`
- **Constants:** `UPPER_SNAKE_CASE` - `API_BASE_URL`, `DEFAULT_DATE_FORMAT`
- **Types/Interfaces:** `PascalCase` - `Deviation`, `Site`, `Model`, `ApiResponse<T>`
- **Signals:** `camelCase` with descriptive prefix - `isLoading`, `isLoadingDeviations`, `sites`, `selectedSite`

**Examples:**
```python
# ✅ Good (Python)
class MeteoParapenteCollector(BaseCollector):
    API_ENDPOINT = "https://data0.meteo-parapente.com/data.php"

    async def collect_forecast(self, site_id: int, forecast_run: datetime) -> List[ForecastData]:
        forecast_value = await self._fetch_api()
        return self._parse_response(forecast_value)

# ❌ Bad (Python)
class meteoParapenteCollector:
    apiEndpoint = "..."

    async def CollectForecast(self, SiteID):
        ForecastValue = await self.fetchAPI()
```

```typescript
// ✅ Good (TypeScript)
interface Deviation {
  timestamp: string;  // ISO 8601
  siteId: number;
  modelId: number;
  forecastValue: number;
  observedValue: number;
  deviation: number;
}

export async function fetchDeviations(params: DeviationQueryParams): Promise<Deviation[]> {
  const [isLoading, setIsLoading] = createSignal(false);
  // ...
}

// ❌ Bad (TypeScript)
interface deviation {
  TimeStamp: string;
  site_id: number;
  forecast_value: number;
}

export async function FetchDeviations(params) {
  const [loading, setLoading] = createSignal(false);
}
```

---

### Structure Patterns

**Project Organization:**

- **Tests Location:** Co-located with source in dedicated `tests/` folders
  - Backend: `backend/tests/` (separate from source)
  - Frontend: `frontend/src/**/*.test.ts` (co-located with components)
- **Test Naming:** `test_{module}.py` (Python), `{Component}.test.tsx` (TypeScript)
- **Shared Utilities:**
  - Backend: `backend/core/` for shared logic (database, config, schemas)
  - Frontend: `frontend/src/lib/` for utilities (api client, formatters, types)
- **Component Organization:** By type for MVP (12 components manageable)
  - `frontend/src/components/` - all UI components
  - `frontend/src/pages/` - route pages (Home, SiteDetail, About)
- **Collectors Organization:** `backend/collectors/` with one file per data source
  - `base.py` - Abstract interface
  - `{source_name}.py` - Concrete implementation (e.g., `meteo_parapente.py`, `arome.py`)

**File Structure Patterns:**

**Configuration Files:**
```
meteo-score/
├── .env.example                    # Environment template (committed)
├── .env                            # Actual secrets (gitignored)
├── .gitignore
├── docker-compose.yml              # Infrastructure definition
├── README.md
├── backend/
│   ├── .env.example
│   ├── alembic.ini                 # Migration config
│   ├── pytest.ini                  # Test config
│   ├── requirements.txt            # Python dependencies
│   └── Dockerfile
└── frontend/
    ├── .eslintrc.json              # Linting rules
    ├── .prettierrc                 # Formatting rules
    ├── tailwind.config.js          # Tailwind config
    ├── tsconfig.json               # TypeScript config
    ├── vite.config.ts              # Build config
    ├── package.json
    └── Dockerfile
```

**Static Assets:**
- **Fonts:** `frontend/public/fonts/` - Geist Sans/Mono woff2 files
- **Icons:** `frontend/public/icons/` - favicon, etc.
- **Images:** `frontend/public/images/` (if needed)

**Documentation:**
- **Root README.md** - Project overview, setup instructions
- **Backend README** (optional) - API overview, collector docs
- **Frontend README** (optional) - Component docs, state patterns

---

### Format Patterns

**API Response Formats:**

**Success Response:**
```json
{
  "data": [
    {
      "id": 1,
      "timestamp": "2026-01-10T14:30:00Z",
      "siteId": 1,
      "modelId": 2,
      "parameterId": 1,
      "horizon": 6,
      "forecastValue": 25.5,
      "observedValue": 23.2,
      "deviation": 2.3
    }
  ],
  "meta": {
    "total": 1523,
    "page": 1,
    "perPage": 100
  }
}
```

**Error Response:**
```json
{
  "error": "ValidationError",
  "detail": "Invalid date range: startDate must be before endDate",
  "statusCode": 400
}
```

**Single Resource (no array wrapper):**
```json
{
  "data": {
    "id": 1,
    "name": "Passy Plaine Joux",
    "latitude": 45.947,
    "longitude": 6.7391
  }
}
```

**Pydantic Schema Conventions:**

```python
# ✅ Good - Pydantic with camelCase alias
from pydantic import BaseModel, Field

class DeviationResponse(BaseModel):
    id: int
    timestamp: datetime
    site_id: int = Field(alias="siteId")
    model_id: int = Field(alias="modelId")
    forecast_value: float = Field(alias="forecastValue")
    observed_value: float = Field(alias="observedValue")
    deviation: float

    class Config:
        populate_by_name = True  # Allow both snake_case and camelCase
```

**Data Exchange Formats:**

- **JSON Field Naming:** `camelCase` - `siteId`, `forecastValue`, `observedValue`
- **Date/Time:** ISO 8601 strings with timezone - `"2026-01-10T14:30:00Z"`
- **Numbers:** JSON numbers (not strings) - `25.5` not `"25.5"`
- **Booleans:** `true`/`false` (lowercase JSON)
- **Null Handling:** Use `null` for missing optional values, omit field if truly not applicable
- **Arrays:** Always use arrays for collections, even if single item (e.g., `"data": [...]`)

**TypeScript Type Conventions:**

```typescript
// ✅ Good - Matches API response
interface Deviation {
  id: number;
  timestamp: string;  // ISO 8601
  siteId: number;
  modelId: number;
  parameterId: number;
  horizon: number;
  forecastValue: number;
  observedValue: number;
  deviation: number;
}

interface ApiResponse<T> {
  data: T;
  meta?: {
    total: number;
    page: number;
    perPage: number;
  };
}

interface ApiError {
  error: string;
  detail: string;
  statusCode: number;
}
```

---

### Communication Patterns

**State Management Patterns (Solid.js):**

- **Signal Naming:**
  - Boolean flags: `isLoading`, `isError`, `isLoadingDeviations`
  - Data: Descriptive noun - `sites`, `deviations`, `selectedSite`
  - Setters: `setIsLoading`, `setSites`, `setSelectedSite`
- **Global State:** Use `createStore` in App.tsx for shared state (site selection, date filters)
- **Local State:** Use `createSignal` in components for component-specific state (loading, errors)
- **Immutable Updates:** Always create new objects/arrays, don't mutate

```typescript
// ✅ Good - Solid.js patterns
const [sites, setSites] = createSignal<Site[]>([]);
const [isLoadingSites, setIsLoadingSites] = createSignal(false);
const [selectedSite, setSelectedSite] = createSignal<Site | null>(null);

// Update immutably
setSites([...sites(), newSite]);

// ❌ Bad
const [loading, setLoading] = createSignal(false);  // Ambiguous
const [SitesList, setSitesList] = createSignal([]);  // Non-standard casing
sites().push(newSite);  // Mutation
```

**API Client Pattern:**

```typescript
// frontend/src/lib/api.ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function fetchDeviations(params: DeviationQueryParams): Promise<Deviation[]> {
  const queryString = new URLSearchParams({
    siteId: params.siteId.toString(),
    modelId: params.modelId.toString(),
    startDate: params.startDate,
    endDate: params.endDate,
  }).toString();

  const response = await fetch(`${API_BASE_URL}/deviations?${queryString}`);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail);
  }

  const data: ApiResponse<Deviation[]> = await response.json();
  return data.data;
}
```

**Event Naming (if needed later):**
- Pattern: `{resource}.{action}` - `deviation.calculated`, `forecast.collected`
- Payload: Consistent structure with `timestamp`, `resource`, `data`

---

### Process Patterns

**Error Handling Patterns:**

**Backend (Python/FastAPI):**

```python
# ✅ Good - FastAPI HTTPException
from fastapi import HTTPException, status

async def get_site(site_id: int) -> Site:
    site = await db.get(Site, site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site with id {site_id} not found"
        )
    return site

# Custom exceptions for domain errors
class CollectorError(Exception):
    """Raised when data collection fails"""
    pass

class ParsingError(Exception):
    """Raised when data parsing fails"""
    pass

# Log errors at appropriate levels
import logging
logger = logging.getLogger(__name__)

try:
    forecast = await collector.collect_forecast(site_id)
except CollectorError as e:
    logger.error(f"Collector failed for site {site_id}: {e}")
    raise HTTPException(status_code=503, detail="Forecast service unavailable")
```

**Frontend (TypeScript/Solid.js):**

```typescript
// ✅ Good - ErrorState component
const [error, setError] = createSignal<string | null>(null);

async function loadDeviations() {
  setIsLoadingDeviations(true);
  setError(null);

  try {
    const data = await fetchDeviations(params);
    setDeviations(data);
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Failed to load deviations');
    console.error('Error loading deviations:', err);
  } finally {
    setIsLoadingDeviations(false);
  }
}

// Render error state
<Show when={error()}>
  <ErrorState message={error()!} onRetry={loadDeviations} />
</Show>
```

**Loading State Patterns:**

```typescript
// ✅ Good - Explicit loading states per resource
const [isLoadingSites, setIsLoadingSites] = createSignal(false);
const [isLoadingDeviations, setIsLoadingDeviations] = createSignal(false);

// Use Show for conditional rendering
<Show when={!isLoadingSites()} fallback={<LoadingState />}>
  <SiteList sites={sites()} />
</Show>

// ❌ Bad - Single global loading state (loses granularity)
const [loading, setLoading] = createSignal(false);
```

**Retry Logic Pattern (Backend):**

```python
# ✅ Good - Exponential backoff
import asyncio
from typing import TypeVar, Callable

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0
) -> T:
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}")
            await asyncio.sleep(delay)
```

---

### Enforcement Guidelines

**All AI Agents MUST:**

1. **Follow Language-Specific Conventions:**
   - Python: `snake_case` for modules/functions, `PascalCase` for classes
   - TypeScript: `camelCase` for variables/functions, `PascalCase` for components/types
   - JSON API: `camelCase` for all fields

2. **Use Consistent Data Formats:**
   - Dates: ISO 8601 strings (`"2026-01-10T14:30:00Z"`)
   - Database: `snake_case` plural tables, `TIMESTAMPTZ` for all timestamps
   - API responses: `{ data: ..., meta: ... }` wrapper format

3. **Maintain Naming Consistency:**
   - Database foreign keys: `{table_singular}_id`
   - API endpoints: RESTful plural nouns (`/sites`, `/deviations`)
   - Loading states: `isLoading{Resource}` pattern
   - Test files: `test_{module}.py` (Python), `{Component}.test.tsx` (TypeScript)

4. **Handle Errors Uniformly:**
   - Backend: FastAPI `HTTPException` with descriptive `detail` messages
   - Frontend: Try/catch with error signals, ErrorState component for display
   - Logging: Use appropriate levels (INFO for normal ops, WARNING for retries, ERROR for failures)

5. **Follow Project Structure:**
   - Backend tests in `backend/tests/`
   - Frontend tests co-located: `src/**/*.test.tsx`
   - Collectors in `backend/collectors/{source_name}.py`
   - Shared utilities in `backend/core/` and `frontend/src/lib/`

**Pattern Enforcement:**

- **Linting:**
  - Backend: `ruff` for Python style, `mypy` for type checking
  - Frontend: ESLint + TypeScript compiler for type safety
- **Code Review:** Check adherence to patterns in PR reviews
- **Testing:** Integration tests verify API response formats match TypeScript types
- **Documentation:** This architecture document is the source of truth

**Updating Patterns:**

- Patterns can evolve as project grows
- Changes require team consensus (or user decision if solo)
- Update this document when patterns change
- Communicate changes to all active developers/agents

---

### Pattern Examples

**Good Examples:**

**Backend Collector Implementation:**
```python
# backend/collectors/meteo_parapente.py
from collectors.base import BaseCollector
from datetime import datetime
from typing import List

class MeteoParapenteCollector(BaseCollector):
    """Collector for Meteo-Parapente JSON API."""

    API_ENDPOINT = "https://data0.meteo-parapente.com/data.php"

    async def collect_forecast(
        self,
        site_id: int,
        forecast_run: datetime
    ) -> List[ForecastData]:
        """Collect forecast from Meteo-Parapente API."""
        try:
            response = await self._fetch_json(site_id, forecast_run)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Collection failed for site {site_id}: {e}")
            raise CollectorError(f"Failed to collect data: {e}")
```

**Frontend Component with Loading/Error:**
```typescript
// frontend/src/components/DeviationChart.tsx
import { createSignal, onMount, Show } from 'solid-js';
import { fetchDeviations } from '../lib/api';
import type { Deviation } from '../lib/types';

interface DeviationChartProps {
  siteId: number;
  modelId: number;
}

export function DeviationChart(props: DeviationChartProps) {
  const [deviations, setDeviations] = createSignal<Deviation[]>([]);
  const [isLoadingDeviations, setIsLoadingDeviations] = createSignal(false);
  const [error, setError] = createSignal<string | null>(null);

  onMount(async () => {
    setIsLoadingDeviations(true);
    try {
      const data = await fetchDeviations({
        siteId: props.siteId,
        modelId: props.modelId,
      });
      setDeviations(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setIsLoadingDeviations(false);
    }
  });

  return (
    <div class="deviation-chart">
      <Show when={isLoadingDeviations()}>
        <LoadingState />
      </Show>
      <Show when={error()}>
        <ErrorState message={error()!} />
      </Show>
      <Show when={!isLoadingDeviations() && !error()}>
        {/* D3.js chart rendering */}
      </Show>
    </div>
  );
}
```

**API Route with Proper Response Format:**
```python
# backend/api/routes/deviations.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

router = APIRouter(prefix="/deviations", tags=["deviations"])

@router.get("/")
async def get_deviations(
    site_id: int = Query(..., alias="siteId"),
    model_id: int = Query(..., alias="modelId"),
    start_date: date = Query(..., alias="startDate"),
    end_date: date = Query(..., alias="endDate"),
    db: AsyncSession = Depends(get_db)
):
    """Query deviations with filters."""
    deviations = await db.query(Deviation).filter(
        Deviation.site_id == site_id,
        Deviation.model_id == model_id,
        Deviation.timestamp >= start_date,
        Deviation.timestamp <= end_date
    ).all()

    return {
        "data": [DeviationResponse.from_orm(d) for d in deviations],
        "meta": {
            "total": len(deviations),
            "perPage": 1000
        }
    }
```

**Anti-Patterns (What to Avoid):**

❌ **Mixed Naming Conventions:**
```python
# ❌ Bad - Mixing camelCase in Python
class meteoParapenteCollector:
    apiEndpoint = "..."
    def CollectForecast(self, SiteID):
        pass
```

❌ **Inconsistent JSON Formats:**
```json
// ❌ Bad - snake_case in JSON (conflicts with frontend)
{
  "site_id": 1,
  "forecast_value": 25.5,
  "created_at": "2026-01-10T14:30:00Z"
}
```

❌ **Ambiguous Loading States:**
```typescript
// ❌ Bad - Non-specific loading variable
const [loading, setLoading] = createSignal(false);  // Loading what?
```

❌ **Direct Mutation:**
```typescript
// ❌ Bad - Mutating signal value
const [sites, setSites] = createSignal<Site[]>([]);
sites().push(newSite);  // Don't mutate!

// ✅ Good - Immutable update
setSites([...sites(), newSite]);
```

❌ **Non-Standard Error Handling:**
```python
# ❌ Bad - Returning error as success
@router.get("/sites/{id}")
async def get_site(id: int):
    site = await db.get(Site, id)
    if not site:
        return {"error": "Not found"}  # Should raise HTTPException!
    return site
```

❌ **Inconsistent Date Formats:**
```json
// ❌ Bad - Unix timestamp instead of ISO 8601
{
  "timestamp": 1736518200,  // Loses timezone info
  "createdAt": "2026-01-10"  // Missing time
}

// ✅ Good
{
  "timestamp": "2026-01-10T14:30:00Z",
  "createdAt": "2026-01-10T09:15:00Z"
}
```

---

## Project Structure & Boundaries

### Complete Project Directory Structure

```
meteo-score/
├── README.md                                # Project overview, setup instructions
├── .gitignore                               # Git ignore rules
├── .env.example                             # Environment variables template
├── docker-compose.yml                       # Infrastructure (postgres, backend, frontend, traefik, adminer)
│
├── backend/                                 # Python FastAPI backend
│   ├── README.md                            # Backend-specific docs (optional)
│   ├── .env.example                         # Backend env template
│   ├── requirements.txt                     # Python dependencies
│   ├── Dockerfile                           # Backend container config
│   ├── alembic.ini                          # Alembic migration config
│   ├── pytest.ini                           # Pytest configuration
│   ├── .python-version                      # Python version (3.11+)
│   │
│   ├── collectors/                          # Modular data collectors (Strategy pattern)
│   │   ├── __init__.py
│   │   ├── base.py                          # Abstract BaseCollector interface
│   │   ├── meteo_parapente.py              # Meteo-Parapente JSON API collector
│   │   ├── arome.py                         # AROME GRIB2 collector (cfgrib + xarray)
│   │   ├── romma.py                         # ROMMA beacon scraper (BeautifulSoup4)
│   │   └── ffvl.py                          # FFVL balisemeteo scraper
│   │
│   ├── core/                                # Shared business logic & config
│   │   ├── __init__.py
│   │   ├── models.py                        # SQLAlchemy ORM models (Site, Model, Parameter, Deviation)
│   │   ├── schemas.py                       # Pydantic request/response schemas
│   │   ├── deviation_engine.py              # Core business logic (forecast - observation)
│   │   ├── database.py                      # Database session management, connection pooling
│   │   └── config.py                        # Pydantic Settings (env var loading)
│   │
│   ├── api/                                 # FastAPI REST API
│   │   ├── __init__.py
│   │   ├── main.py                          # FastAPI app initialization, CORS, middleware
│   │   ├── dependencies.py                  # Dependency injection (DB session, etc.)
│   │   └── routes/                          # API route modules
│   │       ├── __init__.py
│   │       ├── sites.py                     # GET /sites, GET /sites/{id}
│   │       ├── models.py                    # GET /models
│   │       ├── parameters.py                # GET /parameters
│   │       ├── deviations.py                # GET /deviations (with filters)
│   │       └── bias_summary.py              # GET /bias-summary (aggregated stats)
│   │
│   ├── db/                                  # Database migrations & init scripts
│   │   ├── migrations/                      # Alembic migration versions
│   │   │   ├── env.py                       # Alembic environment config
│   │   │   ├── script.py.mako              # Migration template
│   │   │   └── versions/                    # Migration version files
│   │   │       └── 001_initial_schema.py   # Example: Initial tables
│   │   └── init_hypertables.sql            # TimescaleDB extension setup (run on first start)
│   │
│   ├── scheduler/                           # APScheduler orchestration
│   │   ├── __init__.py
│   │   ├── scheduler.py                     # Scheduler initialization, job registration
│   │   └── jobs.py                          # APScheduler job functions (forecast/observation collection)
│   │
│   ├── tests/                               # Backend tests (separate from source)
│   │   ├── __init__.py
│   │   ├── conftest.py                      # Pytest fixtures (test DB, mock collectors)
│   │   ├── test_collectors.py               # TDD tests for data parsers (>80% coverage)
│   │   ├── test_deviation_engine.py         # Unit tests for deviation calculation
│   │   ├── test_api_sites.py                # API endpoint tests (FastAPI TestClient)
│   │   ├── test_api_deviations.py           # API endpoint tests
│   │   └── test_integration.py              # End-to-end pipeline tests
│   │
│   └── main.py                              # Backend entry point (run scheduler + API)
│
├── frontend/                                # Solid.js TypeScript frontend
│   ├── README.md                            # Frontend-specific docs (optional)
│   ├── package.json                         # npm dependencies
│   ├── package-lock.json                    # Lockfile
│   ├── Dockerfile                           # Frontend container config
│   ├── .gitignore                           # Frontend-specific ignores
│   ├── .eslintrc.json                       # ESLint rules (TypeScript)
│   ├── .prettierrc                          # Prettier formatting rules
│   ├── tailwind.config.js                   # Tailwind CSS config (breakpoints, Geist fonts)
│   ├── postcss.config.js                    # PostCSS config (Tailwind processing)
│   ├── tsconfig.json                        # TypeScript compiler config
│   ├── vite.config.ts                       # Vite build config (vite-plugin-solid)
│   ├── index.html                           # HTML entry point
│   │
│   ├── src/                                 # Frontend source code
│   │   ├── index.tsx                        # App entry point (render <App />)
│   │   ├── App.tsx                          # Root component (Router + layout)
│   │   │
│   │   ├── components/                      # 12 custom Solid.js components
│   │   │   ├── SiteSearch.tsx               # Search/filter sites (deferred for MVP: list view)
│   │   │   ├── VerdictHeader.tsx            # Summary verdict for model accuracy
│   │   │   ├── ComparisonTable.tsx          # Side-by-side model comparison
│   │   │   ├── DeviationChart.tsx           # D3.js time-series deviation visualization
│   │   │   ├── ModelCard.tsx                # Model info card
│   │   │   ├── BiasIndicator.tsx            # Visual bias representation (+ or -)
│   │   │   ├── ParameterSelector.tsx        # Filter by parameter (wind, temp)
│   │   │   ├── HorizonSelector.tsx          # Filter by forecast horizon (H+6, H+24, H+48)
│   │   │   ├── DateRangePicker.tsx          # Date range filter
│   │   │   ├── LoadingState.tsx             # Loading spinner/skeleton
│   │   │   └── ErrorState.tsx               # Error message with retry button
│   │   │
│   │   ├── pages/                           # Route pages
│   │   │   ├── Home.tsx                     # Landing page (site list, deferred map)
│   │   │   ├── SiteDetail.tsx               # Individual site detail + model comparisons
│   │   │   └── About.tsx                    # About project, methodology, data sources
│   │   │
│   │   ├── lib/                             # Utilities & helpers
│   │   │   ├── api.ts                       # Typed API client (fetch wrapper, error handling)
│   │   │   ├── types.ts                     # TypeScript interfaces (Deviation, Site, Model, etc.)
│   │   │   └── formatters.ts                # Date formatting, number formatting utilities
│   │   │
│   │   └── styles/                          # Styles & fonts
│   │       └── index.css                    # Tailwind directives + Geist font imports
│   │
│   ├── public/                              # Static assets (served directly)
│   │   ├── favicon.ico                      # Site icon
│   │   ├── fonts/                           # Geist Sans + Geist Mono woff2 files
│   │   └── icons/                           # Additional icons if needed
│   │
│   └── tests/                               # Frontend tests (co-located alternative)
│       └── setup.ts                         # Vitest setup file
│
└── .github/                                 # GitHub Actions CI/CD
    └── workflows/
        └── ci.yml                           # CI/CD pipeline (test, build, deploy)
```

### Architectural Boundaries

**API Boundaries:**

- **External API (Public):**
  - Endpoint Base: `http://localhost:8000` (dev), `https://api.meteoscore.com` (prod)
  - Routes: `/sites`, `/models`, `/parameters`, `/deviations`, `/bias-summary`
  - Authentication: None (public read-only data)
  - Rate Limiting: 100 requests/minute per IP
  - CORS: Frontend origin only (`http://localhost:5173` dev, `https://meteoscore.com` prod)

- **Data Source APIs (External Dependencies):**
  - **Meteo-Parapente:** `https://data0.meteo-parapente.com/data.php` (JSON)
  - **AROME (Météo-France):** GRIB2 files via HTTP (50 req/min limit)
  - **ROMMA Beacons:** Station 241 Passy (scraping or API if available)
  - **FFVL balisemeteo:** `https://www.balisemeteo.com` (scraping, Varan ID 2834)

- **Internal API Communication:**
  - Backend ↔ TimescaleDB: PostgreSQL protocol, async SQLAlchemy
  - Frontend ↔ Backend API: HTTP/REST, JSON payloads (camelCase)
  - Scheduler ↔ Collectors: In-process Python function calls

**Component Boundaries:**

- **Backend Components:**
  - **Collectors Layer:** Independent, modular collectors (Strategy pattern)
    - Each collector implements `BaseCollector` interface
    - No direct dependencies between collectors
    - Collectors don't access database directly (return data to scheduler)

  - **Core Layer:** Shared business logic
    - `models.py`: Database schema (ORM layer)
    - `schemas.py`: API contracts (Pydantic validation)
    - `deviation_engine.py`: Stateless calculation logic
    - `database.py`: Session management (dependency injection)

  - **API Layer:** HTTP interface
    - Routes depend on `core.models` and `core.schemas`
    - Routes use `dependencies.py` for DB sessions
    - No direct collector access (collectors run via scheduler)

  - **Scheduler Layer:** Orchestration
    - Depends on collectors + core (models, database)
    - Runs independently from API (separate asyncio loop)
    - Uses APScheduler for cron-like scheduling

- **Frontend Components:**
  - **Pages:** Top-level route components
    - Manage page-level state (loading, errors, data fetching)
    - Compose multiple UI components
    - Use `@solidjs/router` for navigation

  - **UI Components:** Reusable presentation components
    - Accept props, emit events via callbacks
    - No direct API calls (receive data from pages)
    - Use Solid.js signals for local state only

  - **Lib Layer:** Utilities & API client
    - `api.ts`: Centralized fetch wrapper (all API calls go through here)
    - `types.ts`: Shared TypeScript interfaces
    - `formatters.ts`: Pure functions (no side effects)

**Data Boundaries:**

- **Database Schema Boundaries:**
  - **Reference Tables:** `sites`, `models`, `parameters` (seed data, rarely updated)
  - **Core Data:** `deviations` (TimescaleDB hypertable, high-volume writes)
  - **Aggregated Views:** `daily_mae`, `weekly_mae` (continuous aggregates, read-only)
  - **Foreign Key Constraints:** Enforce referential integrity between tables

- **Data Access Patterns:**
  - **Write Path:** Collectors → Scheduler → `deviation_engine` → SQLAlchemy → TimescaleDB
  - **Read Path:** Frontend → API routes → SQLAlchemy queries → TimescaleDB → JSON response
  - **No Direct Database Access:** Frontend never connects to DB (API layer enforces boundary)

- **Caching Boundaries:**
  - **No External Cache:** TimescaleDB continuous aggregates serve as "database-level cache"
  - **Browser Cache:** Static assets (fonts, icons) cached via HTTP headers
  - **API Response Cache:** None for MVP (re-evaluate if performance issues)

### Requirements to Structure Mapping

**Functional Requirements Mapping:**

1. **FR: Automated Forecast Collection**
   - **Implementation:** `backend/collectors/` (meteo_parapente.py, arome.py)
   - **Orchestration:** `backend/scheduler/jobs.py` (4x daily CronTrigger)
   - **Storage:** Writes to `deviations` table via `deviation_engine.py`
   - **Tests:** `backend/tests/test_collectors.py`, `backend/tests/test_integration.py`

2. **FR: Automated Observation Collection**
   - **Implementation:** `backend/collectors/` (romma.py, ffvl.py)
   - **Orchestration:** `backend/scheduler/jobs.py` (6x daily CronTrigger, 8h-18h)
   - **Storage:** Writes to `deviations` table via `deviation_engine.py`
   - **Tests:** `backend/tests/test_collectors.py`

3. **FR: Deviation Calculation Engine**
   - **Implementation:** `backend/core/deviation_engine.py`
   - **Logic:** `deviation = forecast_value - observed_value`
   - **Invoked By:** Scheduler jobs after collecting forecast+observation pairs
   - **Tests:** `backend/tests/test_deviation_engine.py`

4. **FR: Historical Time-Series Storage**
   - **Implementation:** TimescaleDB hypertables (`backend/db/init_hypertables.sql`)
   - **Schema:** `backend/core/models.py` (Deviation model)
   - **Migrations:** `backend/db/migrations/versions/001_initial_schema.py`
   - **Aggregates:** Continuous aggregates for daily/weekly MAE

5. **FR: Web Visualization Interface**
   - **Implementation:** `frontend/src/pages/` (Home.tsx, SiteDetail.tsx)
   - **Components:** `frontend/src/components/` (DeviationChart.tsx, ComparisonTable.tsx, etc.)
   - **Data Fetching:** `frontend/src/lib/api.ts` (fetchDeviations, fetchSites, etc.)
   - **Routing:** `@solidjs/router` in `App.tsx`

6. **FR: Contextual Bias Characterization**
   - **API Endpoint:** `backend/api/routes/bias_summary.py` (`GET /bias-summary`)
   - **Calculation:** Query TimescaleDB continuous aggregates (AVG(ABS(deviation)))
   - **Frontend Display:** `frontend/src/components/VerdictHeader.tsx`, `BiasIndicator.tsx`

**Cross-Cutting Concerns Mapping:**

1. **Scheduling & Orchestration:**
   - **Implementation:** `backend/scheduler/` (scheduler.py, jobs.py)
   - **Library:** APScheduler with CronTrigger
   - **Initialization:** `backend/main.py` (start scheduler on app startup)

2. **Error Handling:**
   - **Backend:** FastAPI HTTPException in `backend/api/routes/*.py`
   - **Frontend:** Try/catch in `frontend/src/lib/api.ts`, ErrorState component
   - **Logging:** Python `logging` module (stdout → Docker logs)

3. **Data Validation:**
   - **API Input:** Pydantic schemas in `backend/core/schemas.py`
   - **Collector Output:** Unit tests in `backend/tests/test_collectors.py`
   - **Aberrant Values:** Alerts in `backend/scheduler/jobs.py` (wind >200, temp <-50)

4. **Testing:**
   - **Backend Unit:** `backend/tests/test_*.py` (pytest, >80% coverage)
   - **Backend Integration:** `backend/tests/test_integration.py`
   - **Frontend Unit:** `frontend/src/**/*.test.tsx` (Vitest, optional for MVP)

5. **Configuration Management:**
   - **Environment Variables:** `.env` files, `backend/core/config.py` (Pydantic Settings)
   - **Frontend Env:** `import.meta.env.VITE_*` variables
   - **Docker Env:** `docker-compose.yml` environment sections

### Integration Points

**Internal Communication:**

1. **Scheduler → Collectors → Deviation Engine → Database:**
   ```
   APScheduler CronTrigger
     ↓
   scheduler/jobs.py (collect_forecasts(), collect_observations())
     ↓
   collectors/*.py (meteo_parapente.py, arome.py, romma.py, ffvl.py)
     ↓ return ForecastData / ObservationData
   core/deviation_engine.py (calculate_deviation())
     ↓
   core/models.py (Deviation ORM model)
     ↓
   TimescaleDB (INSERT into deviations table)
   ```

2. **Frontend → API → Database:**
   ```
   User Action (select site, date range)
     ↓
   frontend/src/pages/SiteDetail.tsx
     ↓ call fetchDeviations()
   frontend/src/lib/api.ts
     ↓ HTTP GET /deviations?siteId=1&startDate=...
   backend/api/routes/deviations.py
     ↓ SQLAlchemy query
   TimescaleDB (SELECT from deviations WHERE ...)
     ↓ JSON response {data: [...], meta: {...}}
   frontend displays in DeviationChart.tsx (D3.js)
   ```

3. **Database → Continuous Aggregates → API:**
   ```
   TimescaleDB Refresh Policy (automatic)
     ↓
   Continuous Aggregate (daily_mae view)
     ↓ precomputed AVG(ABS(deviation))
   backend/api/routes/bias_summary.py
     ↓ SELECT * FROM daily_mae WHERE ...
   Frontend displays in VerdictHeader.tsx
   ```

**External Integrations:**

1. **Meteo-Parapente API:**
   - **Trigger:** APScheduler 4x daily
   - **Endpoint:** `https://data0.meteo-parapente.com/data.php`
   - **Format:** JSON
   - **Collector:** `backend/collectors/meteo_parapente.py`
   - **Error Handling:** Retry with exponential backoff (3 attempts)

2. **AROME GRIB2 (Météo-France):**
   - **Trigger:** APScheduler 4x daily
   - **Format:** GRIB2 binary files
   - **Libraries:** `cfgrib`, `xarray` for parsing
   - **Collector:** `backend/collectors/arome.py`
   - **Rate Limit:** 50 requests/min (respect limit)

3. **ROMMA Beacons:**
   - **Trigger:** APScheduler 6x daily (8h-18h)
   - **Source:** Station 241 Passy
   - **Format:** HTML scraping (BeautifulSoup4) or API if available
   - **Collector:** `backend/collectors/romma.py`

4. **FFVL balisemeteo:**
   - **Trigger:** APScheduler 6x daily (8h-18h)
   - **Source:** Varan ID 2834
   - **URL:** `https://www.balisemeteo.com`
   - **Format:** HTML scraping (BeautifulSoup4)
   - **Collector:** `backend/collectors/ffvl.py`

**Data Flow:**

```
External Weather APIs (AROME, Meteo-Parapente)
  ↓ 4x daily
Forecast Collectors (backend/collectors/*.py)
  ↓ ForecastData objects
Scheduler Jobs (backend/scheduler/jobs.py)
  ↓
  ├─→ Store in staging (optional) OR
  └─→ Wait for matching observation

External Beacons (ROMMA, FFVL)
  ↓ 6x daily (8h-18h)
Observation Collectors (backend/collectors/*.py)
  ↓ ObservationData objects
Scheduler Jobs (backend/scheduler/jobs.py)
  ↓
Match with Forecast (same site, timestamp, parameter, horizon)
  ↓
Deviation Engine (backend/core/deviation_engine.py)
  ↓ deviation = forecast - observed
TimescaleDB deviations table
  ↓ Continuous aggregates refresh
TimescaleDB daily_mae view (precomputed metrics)
  ↓
FastAPI Routes (backend/api/routes/*.py)
  ↓ JSON response (camelCase)
Frontend API Client (frontend/src/lib/api.ts)
  ↓ TypeScript types
Solid.js Components (frontend/src/components/*.tsx)
  ↓ D3.js visualization
User Browser
```

### File Organization Patterns

**Configuration Files:**

- **Root Level:**
  - `docker-compose.yml`: Infrastructure orchestration (postgres, backend, frontend, traefik, adminer)
  - `.gitignore`: Exclude `.env`, `venv/`, `node_modules/`, `__pycache__/`, `dist/`
  - `.env.example`: Template for environment variables (committed)
  - `.env`: Actual secrets (gitignored)

- **Backend Config:**
  - `requirements.txt`: Python dependencies (FastAPI, SQLAlchemy, pandas, etc.)
  - `alembic.ini`: Alembic migration tool config
  - `pytest.ini`: Pytest settings (coverage thresholds, test paths)
  - `.python-version`: Python 3.11+

- **Frontend Config:**
  - `package.json`: npm dependencies (solid-js, d3, tailwindcss, etc.)
  - `vite.config.ts`: Vite build settings (vite-plugin-solid)
  - `tailwind.config.js`: Tailwind customization (breakpoints, Geist fonts)
  - `tsconfig.json`: TypeScript compiler options (strict mode, paths)
  - `.eslintrc.json`: ESLint rules
  - `.prettierrc`: Prettier formatting

**Source Organization:**

- **Backend Source:**
  - **Entry Point:** `backend/main.py` (start FastAPI + APScheduler)
  - **Collectors:** `backend/collectors/*.py` (one file per data source)
  - **Core Logic:** `backend/core/*.py` (models, schemas, deviation_engine, database, config)
  - **API Routes:** `backend/api/routes/*.py` (one file per resource)
  - **Scheduler:** `backend/scheduler/*.py` (scheduler setup, job definitions)
  - **Migrations:** `backend/db/migrations/versions/*.py` (Alembic version files)

- **Frontend Source:**
  - **Entry Point:** `frontend/src/index.tsx` (render <App />)
  - **App Root:** `frontend/src/App.tsx` (Router, global layout)
  - **Pages:** `frontend/src/pages/*.tsx` (route components)
  - **Components:** `frontend/src/components/*.tsx` (UI components)
  - **Utilities:** `frontend/src/lib/*.ts` (api client, types, formatters)
  - **Styles:** `frontend/src/styles/index.css` (Tailwind directives, Geist imports)

**Test Organization:**

- **Backend Tests:**
  - **Location:** `backend/tests/` (separate from source)
  - **Fixtures:** `backend/tests/conftest.py` (pytest fixtures, test DB setup)
  - **Unit Tests:** `backend/tests/test_*.py` (one test file per module)
  - **Integration:** `backend/tests/test_integration.py` (end-to-end pipeline)
  - **Coverage:** >80% target (enforced in `pytest.ini`)

- **Frontend Tests:**
  - **Location:** `frontend/tests/` or co-located `*.test.tsx` (optional for MVP)
  - **Framework:** Vitest + @solidjs/testing-library
  - **Setup:** `frontend/tests/setup.ts`

**Asset Organization:**

- **Frontend Static Assets:**
  - **Fonts:** `frontend/public/fonts/` (Geist Sans/Mono woff2)
  - **Icons:** `frontend/public/icons/` (favicon, etc.)
  - **Images:** `frontend/public/images/` (if needed)

- **Build Outputs:**
  - **Backend:** No build step (interpreted Python)
  - **Frontend:** `frontend/dist/` (Vite production build, gitignored)

### Development Workflow Integration

**Development Server Structure:**

- **Backend Dev:**
  - **Command:** `cd backend && source venv/bin/activate && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000`
  - **Hot Reload:** Uvicorn watches `backend/**/*.py` for changes
  - **Database:** Docker Compose `postgres` service (TimescaleDB)
  - **Logs:** Stdout (colored, structured)

- **Frontend Dev:**
  - **Command:** `cd frontend && npm run dev` (Vite dev server)
  - **Hot Module Replacement:** Vite HMR for instant updates
  - **Port:** `http://localhost:5173`
  - **Proxy:** API calls to `http://localhost:8000` (CORS configured)

- **Full Stack Dev:**
  - **Command:** `docker-compose up` (all services: postgres, backend, frontend, adminer)
  - **Ports:**
    - Backend API: `http://localhost:8000`
    - Frontend: `http://localhost:3000`
    - Adminer (DB UI): `http://localhost:8080`
    - PostgreSQL: `localhost:5432`

**Build Process Structure:**

- **Backend Build:**
  - **Docker Build:** `docker build -t meteo-score-backend ./backend`
  - **Multi-stage:** Copy requirements.txt → pip install → copy source
  - **Production Image:** Python 3.11-slim base, run `python main.py`

- **Frontend Build:**
  - **Command:** `npm run build` (Vite production build)
  - **Output:** `frontend/dist/` (minified, tree-shaken, optimized)
  - **Docker Build:** `docker build -t meteo-score-frontend ./frontend`
  - **Serve:** Nginx or Node.js static server

**Deployment Structure:**

- **Infrastructure:** Docker Compose orchestrates all services
- **Services:**
  - `postgres`: TimescaleDB image, persistent volume
  - `backend`: Python app (API + Scheduler)
  - `frontend`: Vite build served via Nginx/Node
  - `traefik`: Reverse proxy, automatic HTTPS (Let's Encrypt)
  - `adminer`: Database admin UI (optional in production)

- **Environment:**
  - **Dev:** `.env` with local settings
  - **Production:** `.env` with prod DATABASE_URL, API_BASE_URL, etc.
  - **Secrets:** GitHub Secrets for CI/CD (VPS SSH keys, DB passwords)

- **CI/CD:**
  - **Trigger:** Push to `main` branch
  - **Steps (`.github/workflows/ci.yml`):**
    1. Run backend tests (`pytest`)
    2. Run frontend tests (`npm run test`, optional)
    3. Build Docker images
    4. Push images to registry (optional) OR
    5. SSH to VPS, pull repo, `docker-compose up -d --build`

---

**Architecture Document Complete**: This structure provides a comprehensive blueprint for implementing the MétéoScore platform with clear boundaries, integration points, and organizational patterns that ensure all AI agents write compatible code.

---

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**

All technology choices work together seamlessly:
- **Backend Stack:** Python 3.11+ with FastAPI, SQLAlchemy (async with asyncpg), and Pydantic V2 are fully compatible. FastAPI's native async support aligns perfectly with SQLAlchemy's async engine.
- **Database:** TimescaleDB 2.13+ (PostgreSQL 15 extension) integrates natively with SQLAlchemy ORM while providing specialized time-series features (hypertables, continuous aggregates).
- **Frontend Stack:** TypeScript 5.0+, Solid.js with Vite build tooling, Tailwind CSS 4.0, and D3.js are all compatible and work together without conflicts.
- **Deployment:** Docker Compose orchestrates all services (postgres, backend, frontend, traefik, adminer) with proper networking and dependencies.
- **Scheduling:** APScheduler integrates cleanly with FastAPI's async architecture for in-process scheduling (4x daily forecasts, 6x daily observations).
- **Version Compatibility:** All specified versions are current, stable, and mutually compatible.

**No contradictory decisions found.** All technology choices support the "store deviations only" architectural insight and self-hosted infrastructure requirement.

**Pattern Consistency:**

Implementation patterns align perfectly with architectural decisions:
- **Naming Conventions:** Consistent 3-tier approach (snake_case Python/DB, camelCase TypeScript/JSON, PascalCase classes/components) prevents conflicts across API boundaries.
- **Error Handling:** Uniform exception-based approach (Python standard + FastAPI HTTPException backend, try/catch + ErrorState component frontend).
- **State Management:** Solid.js native signals (createSignal, createStore) align with framework philosophy—no external state library needed.
- **Data Flow:** Modular collectors follow Strategy pattern, enabling horizontal scaling without refactoring.
- **API Response Format:** Standardized `{data, meta}` wrapper with camelCase fields ensures consistent frontend consumption.
- **Loading States:** Descriptive `isLoading{Resource}` pattern prevents ambiguity across 12 components.

**All patterns support the chosen technology stack.** The deviation-only storage model is reflected in database schema, API endpoints (`/deviations`, `/bias-summary`), and frontend components (DeviationChart, BiasIndicator).

**Structure Alignment:**

Project structure fully supports all architectural decisions:
- **Modular Collectors:** `backend/collectors/` with Strategy pattern (base.py + source-specific implementations) enables adding new data sources without touching existing code.
- **Clear Boundaries:** Core layer (models, schemas, deviation_engine) separates business logic from API and collector layers.
- **Test Organization:** Backend tests in `tests/` (TDD for parsers), frontend tests co-located (component-specific).
- **Integration Points:** Scheduler → Collectors → Deviation Engine → Database flow is clearly mapped.
- **Component Structure:** 12 custom frontend components organized by type (pages/, components/, lib/) supports both current MVP and future expansion.
- **Configuration Management:** Centralized in `backend/core/config.py` (Pydantic Settings) and `.env` files for environment-specific overrides.

**The structure enables the chosen patterns.** Directory organization respects separation of concerns while maintaining clear data flow paths.

### Requirements Coverage Validation ✅

**Epic/Feature Coverage:**

No formal epics/stories exist yet (architecture precedes epic creation), but all functional requirements from the Product Brief are fully architecturally supported:

1. **Automated Forecast Collection** ✅ → `backend/collectors/` + `backend/scheduler/jobs.py`
2. **Automated Observation Collection** ✅ → `backend/collectors/` + `backend/scheduler/jobs.py`
3. **Deviation Calculation Engine** ✅ → `backend/core/deviation_engine.py`
4. **Historical Time-Series Storage** ✅ → TimescaleDB hypertables + continuous aggregates
5. **Web Visualization Interface** ✅ → Solid.js components + @solidjs/router
6. **Contextual Bias Characterization** ✅ → `GET /bias-summary` API + VerdictHeader/BiasIndicator components

**Functional Requirements Coverage:**

All 6 core functional requirements have complete architectural implementations:
- **Forecast Collection:** Modular collectors (meteo_parapente.py, arome.py) with cfgrib/xarray/requests, APScheduler 4x daily
- **Observation Collection:** Beacon collectors (romma.py, ffvl.py) with BeautifulSoup4 scraping, APScheduler 6x daily (8h-18h)
- **Deviation Calculation:** Stateless `deviation_engine.py` calculates `forecast_value - observed_value`, fully testable
- **Time-Series Storage:** TimescaleDB hypertables (7-day chunks), composite primary key, Alembic migrations
- **Visualization:** 12 Solid.js components, D3.js charts, Tailwind styling, responsive design
- **Bias Insights:** Continuous aggregates for MAE metrics, `/bias-summary` endpoint, actionable frontend display

**Non-Functional Requirements Coverage:**

All 7 NFRs are architecturally addressed:
- **Reliability (>90% uptime):** APScheduler with retry logic, monitoring, graceful degradation
- **Performance (<2s API, <3s frontend):** Continuous aggregates, async SQLAlchemy, Vite code splitting
- **Scalability (1 → 50+ sites):** Modular collectors, TimescaleDB hypertables, horizontal structure
- **Data Integrity (6-level validation):** Manual validation, unit tests (>80%), automated alerts, cross-validation, historical comparison, ship-and-iterate
- **Maintainability (TDD, >80% coverage):** pytest + pytest-cov, ruff/black/mypy, ESLint/Prettier, CI/CD
- **Accessibility (WCAG 2.1 AA):** Semantic HTML, ARIA, keyboard nav, color contrast (from UX spec)
- **Security (public data):** No auth needed, rate limiting, Pydantic validation, HTTPS via Traefik

**No functional or non-functional requirement lacks architectural support.**

### Implementation Readiness Validation ✅

**Decision Completeness:**

All critical architectural decisions are documented with implementation-ready specificity:
- ✅ Technology stack fully specified with versions (Python 3.11+, PostgreSQL 15, TimescaleDB 2.13+, TypeScript 5.0+, all libraries)
- ✅ Implementation patterns comprehensive (naming, error handling, state management, API format, loading states, retry logic)
- ✅ Consistency rules clear and enforceable (database snake_case, API camelCase, linting with ruff/mypy/ESLint)
- ✅ Examples provided for all major patterns (6 code examples, 5 anti-pattern examples, data flow diagrams)

**AI agents have everything needed to implement consistently.** No ambiguous decisions, no missing specifications.

**Structure Completeness:**

The project structure is exceptionally detailed (2198+ lines of architecture documentation):
- ✅ Complete directory tree (150+ files and directories explicitly defined)
- ✅ All integration points clearly specified (scheduler → collectors → deviation engine → database → API → frontend)
- ✅ Component boundaries well-defined (backend layers: collectors, core, API, scheduler; frontend layers: pages, components, lib)
- ✅ Requirements to structure mapping (all 6 FRs + 7 NFRs mapped to specific files/directories)

**The structure is implementation-ready.** An AI agent can start coding immediately with clear file paths and responsibilities.

**Pattern Completeness:**

All potential conflict points between AI agents are addressed with explicit patterns:
- ✅ Naming conflicts resolved (snake_case Python/DB, camelCase TS/JSON, PascalCase classes/components, Field(alias="siteId") for mapping)
- ✅ Error handling standardized (FastAPI HTTPException backend, try/catch + ErrorState frontend, structured logging)
- ✅ Communication patterns fully specified (centralized API client, signal naming conventions, immutable updates)
- ✅ Process patterns complete (exponential backoff retry, per-resource loading states, Pydantic validation, TDD testing)

**No conflict points remain unaddressed.** AI agents will produce compatible code without coordination.

### Gap Analysis Results

**Critical Gaps:** ✅ **NONE FOUND**

After comprehensive review, there are **zero implementation-blocking gaps**:
- All critical technology decisions are made with specific versions
- Complete project structure with all necessary directories and files
- All functional and non-functional requirements have architectural support
- Integration points and data flows are fully specified
- No ambiguous or contradictory decisions

**Important Gaps:** ✅ **NONE** (Intentional Deferrals Only)

The following are **not gaps** but deliberate architectural decisions following the "ship and iterate" principle:

1. **No External Caching (Redis):** Explicitly deferred until scaling to 10+ models × 50+ sites
2. **No Formal API Documentation (OpenAPI/Swagger):** Deferred (code as documentation, FastAPI can enable `/docs` with zero effort)
3. **No Interactive Map (SiteMap.tsx):** Deferred to multi-site phase (POC has 1 site, list view sufficient for MVP)
4. **No Advanced Observability (Grafana/Loki/Prometheus):** Deferred until operational complexity grows

**All "gaps" have clear rationale and re-evaluation triggers documented.**

**Nice-to-Have Gaps (Future Enhancements):**

Low-priority optimizations that don't block implementation:
1. Migration file examples (Alembic generates templates automatically)
2. Frontend test examples (optional for MVP)
3. Docker health check endpoints (simple HTTP checks sufficient)

**Overall Gap Assessment:** 🟢 **ARCHITECTURE IS COMPLETE**

The architecture is ready for immediate implementation. AI agents can proceed with confidence.

### Validation Issues Addressed

**No Critical Issues Found** ✅

Comprehensive validation across coherence, coverage, and readiness revealed **zero issues** requiring resolution before implementation.

**Positive Validation Findings:**

1. **Exceptional Detail Level:** 2198+ lines of architecture documentation provides implementation-ready specificity
2. **Breakthrough Insight Integrated:** "Store deviations only, not raw data" (100x storage reduction) consistently reflected across database schema, API design, and frontend components
3. **Pattern Consistency:** All 8 pattern categories (naming, structure, format, communication, process) are comprehensive and mutually reinforcing
4. **First Principles Alignment:** Custom structure decision honors the "simplify from first principles" approach from brainstorming session
5. **Testability Built-In:** TDD approach, >80% coverage target, pytest configuration all specified architecturally

**Design Quality Highlights:**

- **Modular Collectors:** Strategy pattern enables horizontal scaling without refactoring
- **No Over-Engineering:** Deliberate deferrals (no caching, no API docs, no map for MVP) follow "ship and iterate" philosophy
- **Separation of Concerns:** Backend and frontend layers have clear boundaries
- **Data Flow Clarity:** Every integration point documented with data flow diagrams
- **Accessibility from Start:** WCAG 2.1 AA compliance integrated, not bolted on later

**Confidence Level for Implementation:** 🟢 **VERY HIGH**

No changes required before proceeding to implementation phase.

### Architecture Completeness Checklist

**✅ Requirements Analysis**

- [x] Project context thoroughly analyzed (Product Brief, UX spec, technical research, brainstorming session)
- [x] Scale and complexity assessed (Medium complexity, 8-10 major components, monolithic with modular collectors)
- [x] Technical constraints identified (GRIB2 parsing, rate limits, beacon scraping, self-hosted requirement)
- [x] Cross-cutting concerns mapped (scheduling, error handling, logging, monitoring, data validation, testing, deployment)

**✅ Architectural Decisions**

- [x] Critical decisions documented with versions (Python 3.11+, FastAPI, SQLAlchemy, TimescaleDB 2.13+, Solid.js, TypeScript 5.0+, Tailwind 4.0)
- [x] Technology stack fully specified (backend, frontend, database, deployment, scheduling, testing tools)
- [x] Integration patterns defined (modular collectors with Strategy pattern, deviation-only storage model)
- [x] Performance considerations addressed (TimescaleDB continuous aggregates, no external cache needed for MVP)

**✅ Implementation Patterns**

- [x] Naming conventions established (3-tier: snake_case Python/DB, camelCase TS/JSON, PascalCase classes/components)
- [x] Structure patterns defined (test organization, component organization, collector organization)
- [x] Communication patterns specified (API client, signals, state management, API response format)
- [x] Process patterns documented (error handling, retry logic, loading states, data validation)

**✅ Project Structure**

- [x] Complete directory structure defined (150+ files/directories explicitly documented)
- [x] Component boundaries established (backend layers: collectors, core, API, scheduler; frontend layers: pages, components, lib)
- [x] Integration points mapped (scheduler → collectors → deviation engine → database → API → frontend)
- [x] Requirements to structure mapping complete (all 6 FRs + 7 NFRs mapped to implementation locations)

### Architecture Readiness Assessment

**Overall Status:** 🟢 **READY FOR IMPLEMENTATION**

**Confidence Level:** **VERY HIGH** based on validation results

**Reasoning:**
- Zero critical gaps (all implementation-blocking decisions are made)
- Exceptional documentation detail (2198+ lines, 150+ files specified)
- Comprehensive pattern coverage (8 categories, 6 good examples, 5 anti-pattern examples)
- Requirements fully mapped to structure (6 FRs + 7 NFRs architecturally supported)
- No contradictions or ambiguities found
- All AI agent conflict points addressed with explicit patterns

**Key Strengths:**

1. **Modular Collector Architecture:** Strategy pattern enables adding data sources without modifying existing code
2. **Deviation-Only Storage Model:** Breakthrough insight (100x storage reduction) architecturally integrated
3. **Self-Hosted Infrastructure:** No external service dependencies ensures full control and cost predictability
4. **Test-Driven Approach:** TDD for data parsers, >80% coverage target, 6-level validation strategy
5. **Ship-and-Iterate Philosophy:** Deliberate deferrals prevent over-engineering while maintaining extensibility

**Areas for Future Enhancement (Post-MVP):**

Intentional deferrals, not architectural weaknesses:
1. External Caching (Redis) - when scaling to 10+ models × 50+ sites
2. Interactive Map - when expanding beyond 4-5 sites
3. Advanced Observability (Grafana/Loki/Prometheus) - when operational complexity grows
4. API Documentation - enable FastAPI `/docs` if external consumers emerge
5. Celery Workers - replace APScheduler if scheduling becomes complex at scale

**None of these enhancements block current implementation.** The MVP architecture is complete and sufficient.

### Implementation Handoff

**AI Agent Guidelines:**

When implementing this architecture, all AI agents (human or AI-assisted) MUST:

1. **Follow All Architectural Decisions Exactly as Documented**
   - Use specified technology versions (Python 3.11+, PostgreSQL 15, TimescaleDB 2.13+, TypeScript 5.0+)
   - Implement deviation-only storage model (no full raw forecast/observation data)
   - Respect self-hosted infrastructure constraint (no external services)

2. **Use Implementation Patterns Consistently Across All Components**
   - Apply naming conventions by layer (snake_case Python/DB, camelCase TS/JSON, PascalCase classes/components)
   - Follow error handling patterns (FastAPI HTTPException backend, try/catch + ErrorState frontend)
   - Use standardized API response format ({data, meta} wrapper, camelCase fields)
   - Implement loading states with descriptive names (isLoading{Resource})

3. **Respect Project Structure and Boundaries**
   - Place collectors in `backend/collectors/` (one file per data source, all implement BaseCollector)
   - Separate tests: `backend/tests/` (unit + integration), `frontend/src/**/*.test.tsx` (component tests)
   - Keep core business logic in `backend/core/` (models, schemas, deviation_engine, database, config)
   - Frontend API calls ONLY through `frontend/src/lib/api.ts` (no direct fetch in components)

4. **Refer to This Document for All Architectural Questions**
   - Naming convention unclear? Check "Naming Patterns" section
   - Error handling approach? Check "Process Patterns > Error Handling Patterns"
   - State management pattern? Check "Communication Patterns > State Management Patterns"
   - Integration point unclear? Check "Integration Points" section

**First Implementation Priority:**

Initialize Custom Project Structure (see "Starter Template Evaluation > Initialization Commands"):

```bash
# Step 1: Create project structure
mkdir meteo-score && cd meteo-score

# Step 2: Backend setup
mkdir -p backend/{collectors,core,api,db,scheduler,tests}
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy pydantic pydantic-settings \
            psycopg2-binary pandas xarray cfgrib requests beautifulsoup4 \
            apscheduler alembic python-dotenv \
            pytest pytest-cov pytest-asyncio httpx
pip freeze > requirements.txt

# Step 3: Frontend setup
cd ../
npx degit solidjs/templates/ts frontend
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install geist

# Step 4: Docker setup
cd ../
touch docker-compose.yml .env.example .gitignore README.md
```

**Implementation Sequence:**

1. **Week 1-2:** Project setup (Docker Compose with TimescaleDB, FastAPI skeleton, Solid.js skeleton)
2. **Week 2-3:** POC data pipeline (Meteo-Parapente collector, deviation engine, manual validation)
3. **Week 3-4:** Backend API (SQLAlchemy models, Pydantic schemas, API routes, tests)
4. **Week 4-5:** Scheduler (APScheduler setup, idempotency, error handling)
5. **Week 5-7:** Frontend MVP (@solidjs/router, API client, components, D3.js charts, Tailwind styling)
6. **Week 7-8:** Expansion (AROME collector, ROMMA/FFVL collectors, continuous aggregates)
7. **Week 8-9:** Production deployment (GitHub Actions CI/CD, VPS setup, Traefik + Let's Encrypt, monitoring)

---

**Architecture Validation Complete**: This architecture has passed comprehensive coherence, coverage, and readiness validation. The MétéoScore platform is ready for implementation with zero critical gaps and very high confidence in AI agent consistency.

---

## Architecture Completion Summary

### Workflow Completion

**Architecture Decision Workflow:** COMPLETED ✅
**Total Steps Completed:** 8
**Date Completed:** 2026-01-10
**Document Location:** `_bmad-output/planning-artifacts/architecture-meteo-score-2026-01-10.md`

### Final Architecture Deliverables

**📋 Complete Architecture Document**

- All architectural decisions documented with specific versions
- Implementation patterns ensuring AI agent consistency
- Complete project structure with all files and directories (150+ files/directories defined)
- Requirements to architecture mapping (6 FRs + 7 NFRs fully supported)
- Validation confirming coherence and completeness

**🏗️ Implementation Ready Foundation**

- 40+ architectural decisions made across 6 major areas
- 8 implementation pattern categories defined (naming, structure, format, communication, process)
- 10+ architectural components specified (collectors, core, API, scheduler, frontend)
- 13 requirements fully supported (6 functional + 7 non-functional)

**📚 AI Agent Implementation Guide**

- Technology stack with verified versions (Python 3.11+, PostgreSQL 15, TimescaleDB 2.13+, TypeScript 5.0+, Solid.js, Tailwind 4.0)
- Consistency rules that prevent implementation conflicts (3-tier naming conventions, standardized error handling, API response format)
- Project structure with clear boundaries (backend/frontend separation, modular collectors, layered architecture)
- Integration patterns and communication standards (scheduler → collectors → deviation engine → database → API → frontend)

### Implementation Handoff

**For AI Agents:**
This architecture document is your complete guide for implementing MétéoScore. Follow all decisions, patterns, and structures exactly as documented.

**First Implementation Priority:**
Initialize custom project structure using the commands documented in "Starter Template Evaluation > Initialization Commands":

```bash
# Step 1: Create project structure
mkdir meteo-score && cd meteo-score

# Step 2: Backend setup
mkdir -p backend/{collectors,core,api,db,scheduler,tests}
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy pydantic pydantic-settings \
            psycopg2-binary pandas xarray cfgrib requests beautifulsoup4 \
            apscheduler alembic python-dotenv \
            pytest pytest-cov pytest-asyncio httpx
pip freeze > requirements.txt

# Step 3: Frontend setup
cd ../
npx degit solidjs/templates/ts frontend
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install geist

# Step 4: Docker setup
cd ../
touch docker-compose.yml .env.example .gitignore README.md
```

**Development Sequence:**

1. Initialize project using documented starter template (Week 1-2)
2. Set up Docker Compose with TimescaleDB + FastAPI skeleton + Solid.js skeleton
3. Implement POC data pipeline (Meteo-Parapente collector, deviation engine, manual validation) (Week 2-3)
4. Build backend API (SQLAlchemy models, Pydantic schemas, routes, tests) (Week 3-4)
5. Implement scheduler (APScheduler, idempotency, error handling) (Week 4-5)
6. Build frontend MVP (@solidjs/router, API client, 12 components, D3.js charts) (Week 5-7)
7. Expand collectors (AROME GRIB2, ROMMA/FFVL beacons, continuous aggregates) (Week 7-8)
8. Production deployment (GitHub Actions CI/CD, VPS setup, Traefik + HTTPS, monitoring) (Week 8-9)

### Quality Assurance Checklist

**✅ Architecture Coherence**

- [x] All decisions work together without conflicts
- [x] Technology choices are compatible (FastAPI + SQLAlchemy async, TimescaleDB + PostgreSQL 15, Solid.js + Vite)
- [x] Patterns support the architectural decisions (modular collectors, deviation-only storage, 3-tier naming)
- [x] Structure aligns with all choices (backend layers, frontend components, Docker Compose deployment)

**✅ Requirements Coverage**

- [x] All functional requirements are supported (6 FRs: forecast collection, observation collection, deviation calculation, time-series storage, visualization, bias characterization)
- [x] All non-functional requirements are addressed (7 NFRs: reliability >90%, performance <2s API, scalability 1→50+ sites, data integrity 6-level validation, maintainability TDD >80%, accessibility WCAG 2.1 AA, security public data)
- [x] Cross-cutting concerns are handled (scheduling, error handling, logging, monitoring, data validation, testing, deployment)
- [x] Integration points are defined (scheduler → collectors → deviation engine → database → API → frontend)

**✅ Implementation Readiness**

- [x] Decisions are specific and actionable (all technology versions specified, no ambiguities)
- [x] Patterns prevent agent conflicts (naming conventions, error handling, API format, state management)
- [x] Structure is complete and unambiguous (150+ files/directories explicitly defined)
- [x] Examples are provided for clarity (6 code examples, 5 anti-pattern examples, data flow diagrams)

### Project Success Factors

**🎯 Clear Decision Framework**
Every technology choice was made collaboratively with clear rationale, ensuring all stakeholders understand the architectural direction. Custom structure decision honors "simplify from first principles" approach.

**🔧 Consistency Guarantee**
Implementation patterns and rules ensure that multiple AI agents will produce compatible, consistent code that works together seamlessly. 3-tier naming conventions prevent conflicts across API boundaries.

**📋 Complete Coverage**
All project requirements are architecturally supported, with clear mapping from business needs to technical implementation. Zero critical gaps found during validation.

**🏗️ Solid Foundation**
The custom project structure and architectural patterns provide a production-ready foundation following current best practices. Breakthrough "deviation-only storage" insight (100x reduction) architecturally integrated.

---

**Architecture Status:** READY FOR IMPLEMENTATION ✅

**Next Phase:** Begin implementation using the architectural decisions and patterns documented herein.

**Document Maintenance:** Update this architecture when major technical decisions are made during implementation.
