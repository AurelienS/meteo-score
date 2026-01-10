---
story_id: "1.1"
epic: 1
title: "Initialize Custom Project Structure"
status: "ready-for-dev"
created: "2026-01-11"
---

# Story 1.1: Initialize Custom Project Structure

## User Story

As a developer,
I want to initialize the custom project structure following the architecture specifications,
So that the codebase is organized correctly from the start and all team members follow consistent patterns.

## Business Context

MétéoScore is an open-source platform that objectively evaluates weather forecast model accuracy for paragliding sites by comparing predictions against real-world observations. This story establishes the foundational project structure that enables:

- **Clear separation of concerns** between backend data pipeline and frontend visualization
- **Modular architecture** for weather data collectors (Strategy pattern)
- **Production-ready development environment** with Docker Compose parity
- **Consistent tooling** across the team (linting, testing, type checking)

The custom structure provides maximum flexibility for the specialized weather data pipeline while avoiding unnecessary authentication/authorization complexity from standard boilerplates. This is the critical first step that ensures all subsequent development follows architectural decisions documented in `architecture-meteo-score-2026-01-10.md`.

## Acceptance Criteria

### Given the architecture document specifies the project structure

### When I initialize the project

### Then the following directory structure is created:

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

### And Python virtual environment is created with Python 3.11+

- Virtual environment is created in `backend/venv/`
- Python version is 3.11 or higher
- Virtual environment is activated successfully
- `.python-version` file specifies Python 3.11+

### And Backend dependencies are installed

**Core Dependencies:**
- `fastapi` - Web framework
- `uvicorn[standard]` - ASGI server
- `sqlalchemy` - ORM with async support
- `pydantic` - Data validation
- `pydantic-settings` - Environment variable management
- `psycopg2-binary` - PostgreSQL adapter

**Data Processing:**
- `pandas` - Data manipulation
- `xarray` - Multi-dimensional arrays (for GRIB2 data)
- `cfgrib` - GRIB2 file parsing
- `requests` - HTTP client for API calls
- `beautifulsoup4` - HTML parsing for beacon scraping

**Scheduling & Migrations:**
- `apscheduler` - Job scheduling (4x daily forecasts, 6x daily observations)
- `alembic` - Database migrations
- `python-dotenv` - Environment variable loading

**Testing:**
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting
- `pytest-asyncio` - Async test support
- `httpx` - FastAPI TestClient dependency

**Linting & Type Checking:**
- `ruff` - Fast Python linter
- `black` - Code formatter
- `mypy` - Static type checker

All dependencies listed in `backend/requirements.txt`

### And Frontend is initialized with Solid.js TypeScript template

- Frontend initialized using `npx degit solidjs/templates/ts frontend`
- TypeScript configuration present (`tsconfig.json`)
- Vite build tool configured (`vite.config.ts`)
- Solid.js plugin installed (`vite-plugin-solid`)

### And Frontend dependencies are installed

**Core Framework:**
- `solid-js` - Reactive UI framework
- `@solidjs/router` - Official routing library

**Styling:**
- `tailwindcss` - Utility-first CSS framework (version 4.0)
- `postcss` - CSS transformation tool
- `autoprefixer` - CSS vendor prefixing
- `geist` - Geist Sans and Geist Mono typography

**Visualization:**
- `d3` - Data visualization library for custom charts
- `@types/d3` - TypeScript definitions for D3.js

**Development Tools:**
- `typescript` - TypeScript compiler (5.0+)
- `eslint` - JavaScript/TypeScript linter
- `prettier` - Code formatter
- `@typescript-eslint/parser` - ESLint TypeScript parser
- `@typescript-eslint/eslint-plugin` - ESLint TypeScript rules

All dependencies listed in `frontend/package.json` and `frontend/package-lock.json`

### And `.env.example` file is created with all required environment variables documented

**Database Configuration:**
```
# Database
DATABASE_URL=postgresql://meteo_user:secure_password@localhost:5432/meteo_score
POSTGRES_USER=meteo_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=meteo_score
```

**Backend Configuration:**
```
# Backend API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
LOG_LEVEL=info
```

**External API Keys (if needed):**
```
# Weather Data Sources
METEO_FRANCE_API_KEY=your_api_key_here
METEO_PARAPENTE_API_URL=https://data0.meteo-parapente.com/data.php
```

**Scheduler Configuration:**
```
# Data Collection Schedule
FORECAST_COLLECTION_HOURS=0,6,12,18  # UTC hours for forecast collection
OBSERVATION_COLLECTION_HOURS=0,4,8,12,16,20  # UTC hours for observation collection
```

### And `.gitignore` file is created excluding:

- `venv/` - Python virtual environment
- `node_modules/` - Node.js dependencies
- `.env` - Environment variables (secrets)
- `__pycache__/` - Python bytecode cache
- `*.pyc` - Compiled Python files
- `.pytest_cache/` - Pytest cache
- `.mypy_cache/` - MyPy cache
- `dist/` - Frontend build output
- `.DS_Store` - macOS system files
- `*.log` - Log files
- `.vscode/` - Editor-specific settings (optional)
- `.idea/` - IDE-specific settings (optional)

### And `README.md` is created with project overview and setup instructions

**Required Sections:**
1. **Project Title & Description** - MétéoScore overview and mission
2. **Key Features** - Objective forecast comparison, site-specific analysis, bias characterization
3. **Technology Stack** - Backend (Python 3.11+, FastAPI, TimescaleDB), Frontend (Solid.js, TypeScript, Tailwind CSS)
4. **Prerequisites** - Python 3.11+, Node.js 18+, Docker & Docker Compose
5. **Local Development Setup:**
   - Clone repository
   - Backend setup (virtual environment, dependencies, `.env` configuration)
   - Frontend setup (npm install, environment variables)
   - Docker Compose setup (services startup)
6. **Project Structure** - Directory tree with brief descriptions
7. **Development Workflow** - Running tests, linting, type checking
8. **Contributing** - Link to contribution guidelines (if applicable)
9. **License** - Open-source license information

### And All linting tools are configured

**Backend Linting (`backend/`):**

1. **Ruff Configuration** (`.ruff.toml` or `pyproject.toml`):
   - Line length: 100 characters
   - Target Python version: 3.11
   - Select rules: pycodestyle (E), pyflakes (F), isort (I), type-checking (TYP)
   - Exclude: `venv/`, `migrations/`, `__pycache__/`

2. **Black Configuration** (`pyproject.toml`):
   - Line length: 100 characters
   - Target Python versions: py311+
   - Exclude: migrations, venv

3. **MyPy Configuration** (`mypy.ini` or `pyproject.toml`):
   - Python version: 3.11
   - Strict mode enabled
   - Ignore missing imports for third-party libraries without stubs
   - Check untyped definitions

4. **Pytest Configuration** (`pytest.ini`):
   - Test paths: `tests/`
   - Coverage threshold: 80%
   - Async mode: auto

**Frontend Linting (`frontend/`):**

1. **ESLint Configuration** (`.eslintrc.json`):
   - Parser: `@typescript-eslint/parser`
   - Plugins: `@typescript-eslint`, `solid`
   - Extends: `eslint:recommended`, `plugin:@typescript-eslint/recommended`
   - Rules: TypeScript-specific rules, Solid.js best practices
   - Ignore patterns: `dist/`, `node_modules/`

2. **Prettier Configuration** (`.prettierrc`):
   - Semi-colons: true
   - Single quotes: false (use double quotes)
   - Tab width: 2
   - Print width: 100
   - Trailing commas: es5

3. **TypeScript Configuration** (`tsconfig.json`):
   - Strict mode: enabled
   - Target: ES2020
   - Module: ESNext
   - JSX: preserve (for Solid.js)
   - Module resolution: bundler
   - Paths aliases: `@/*` → `./src/*`

## Technical Requirements

### Complete Project Structure

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
│   ├── pyproject.toml                       # Python project metadata (ruff, black, mypy config)
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
│   │   │   ├── ErrorState.tsx               # Error message display
│   │   │   └── SiteMap.tsx                  # Interactive map (Leaflet or Mapbox) - deferred
│   │   │
│   │   ├── pages/                           # Page components
│   │   │   ├── Home.tsx                     # Landing page (site list)
│   │   │   ├── SiteDetail.tsx               # Site comparison view
│   │   │   └── About.tsx                    # Methodology explanation
│   │   │
│   │   ├── lib/                             # Utilities & API client
│   │   │   ├── api.ts                       # Fetch wrapper for backend API
│   │   │   ├── types.ts                     # TypeScript interfaces (Deviation, Site, Model, etc.)
│   │   │   └── formatters.ts                # Date formatting, number formatting utilities
│   │   │
│   │   └── styles/                          # Global styles
│   │       └── index.css                    # Tailwind directives + Geist font imports
│   │
│   └── public/                              # Static assets (served directly)
│       └── favicon.ico                      # Site favicon
│
└── _bmad-output/                            # BMAD workflow artifacts (not part of application)
    ├── planning-artifacts/
    │   ├── epics.md
    │   ├── architecture-meteo-score-2026-01-10.md
    │   └── product-brief-meteo-score-2026-01-10.md
    └── implementation-artifacts/
        └── 1-1-initialize-custom-project-structure.md (this file)
```

### Backend Dependencies (requirements.txt)

```
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.9

# Database
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
alembic==1.13.1

# Data Validation & Config
pydantic==2.5.3
pydantic-settings==2.1.0

# Data Processing
pandas==2.1.4
xarray==2024.1.0
cfgrib==0.9.10.4
requests==2.31.0
beautifulsoup4==4.12.3

# Scheduling
apscheduler==3.10.4

# Environment Variables
python-dotenv==1.0.0

# Testing
pytest==7.4.4
pytest-cov==4.1.0
pytest-asyncio==0.23.3
httpx==0.26.0

# Linting & Type Checking
ruff==0.1.13
black==24.1.1
mypy==1.8.0
```

### Frontend Dependencies (package.json)

```json
{
  "name": "meteo-score-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext .ts,.tsx",
    "format": "prettier --write \"src/**/*.{ts,tsx,css}\""
  },
  "dependencies": {
    "solid-js": "^1.8.11",
    "@solidjs/router": "^0.10.10",
    "d3": "^7.8.5",
    "geist": "^1.2.0"
  },
  "devDependencies": {
    "vite": "^5.0.11",
    "vite-plugin-solid": "^2.8.2",
    "typescript": "^5.3.3",
    "tailwindcss": "^4.0.0",
    "postcss": "^8.4.33",
    "autoprefixer": "^10.4.17",
    "@types/d3": "^7.4.3",
    "eslint": "^8.56.0",
    "@typescript-eslint/parser": "^6.19.0",
    "@typescript-eslint/eslint-plugin": "^6.19.0",
    "eslint-plugin-solid": "^0.13.1",
    "prettier": "^3.2.4"
  }
}
```

## Architecture Compliance

### Architectural Decisions Established by Custom Structure

**Language & Runtime:**
- Backend: Python 3.11+ with full type hints (Pydantic V2 for validation)
- Frontend: TypeScript 5.0+ with Solid.js reactive primitives
- Async everywhere: Backend uses `async`/`await` for I/O operations (API calls, database queries)
- Virtual environments: Python `venv` for isolation, `node_modules` for frontend

**Project Organization Principles:**
- **Modular Collectors:** Strategy pattern for data collectors (base.py defines interface)
- **Layered Backend:** Clear separation between collectors, core logic, API, and scheduler
- **Component-Based Frontend:** 12 custom Solid.js components following composition over inheritance
- **Test-Driven Development:** Separate `tests/` directory with >80% coverage target

**Naming Conventions:**
- Database/Backend: `snake_case` (tables, columns, Python functions)
- API/JSON: `camelCase` (all JSON fields for frontend consumption)
- TypeScript: `camelCase` for variables/functions, `PascalCase` for components/interfaces
- Files: `snake_case.py` (Python), `PascalCase.tsx` (Solid.js components), `camelCase.ts` (utilities)

**Technology Stack Versions:**
- Python 3.11+ (required for modern async features and type hints)
- PostgreSQL 15 with TimescaleDB 2.13+ (time-series optimization)
- TypeScript 5.0+ (strict mode for type safety)
- Tailwind CSS 4.0 (utility-first styling)
- Solid.js 1.8+ (reactive UI framework)

**Critical Constraints:**
- Self-hosted infrastructure only (no external service dependencies)
- Public read-only data (no authentication/authorization needed for MVP)
- Deviation-only storage model (no full raw forecast/observation data)
- Data collection: 4x daily forecasts, 6x daily observations

## Implementation Notes

### Initialization Command Sequence

```bash
# 1. Create project root
mkdir meteo-score && cd meteo-score

# 2. Create root-level config files
touch .env.example .gitignore README.md docker-compose.yml

# 3. Backend initialization
mkdir -p backend/{collectors,core,api/routes,db/migrations/versions,scheduler,tests}
cd backend

# Create Python version file
echo "3.11" > .python-version

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install fastapi uvicorn[standard] sqlalchemy pydantic pydantic-settings \
            psycopg2-binary pandas xarray cfgrib requests beautifulsoup4 \
            apscheduler alembic python-dotenv \
            pytest pytest-cov pytest-asyncio httpx \
            ruff black mypy

# Generate requirements.txt
pip freeze > requirements.txt

# Create __init__.py files for Python packages
touch collectors/__init__.py core/__init__.py api/__init__.py \
      api/routes/__init__.py scheduler/__init__.py tests/__init__.py

# Create configuration files
touch alembic.ini pytest.ini pyproject.toml .env.example

# 4. Frontend initialization
cd ../
npx degit solidjs/templates/ts frontend
cd frontend

# Install core dependencies
npm install

# Install development dependencies
npm install -D tailwindcss postcss autoprefixer eslint prettier \
                @typescript-eslint/parser @typescript-eslint/eslint-plugin \
                eslint-plugin-solid

# Install additional runtime dependencies
npm install @solidjs/router d3 geist
npm install -D @types/d3

# Initialize Tailwind CSS
npx tailwindcss init -p

# Create directory structure
mkdir -p src/{components,pages,lib,styles}
mkdir -p public

# Create configuration files
touch .eslintrc.json .prettierrc

# 5. Return to project root
cd ../
```

### Key Files to Create Manually

1. **Root `.gitignore`** - Comprehensive exclusions for Python and Node.js
2. **Root `.env.example`** - All environment variables with documentation
3. **Root `README.md`** - Project overview and setup instructions
4. **Backend `pyproject.toml`** - Ruff, Black, and MyPy configurations
5. **Backend `pytest.ini`** - Test discovery and coverage settings
6. **Backend `alembic.ini`** - Alembic migration configuration
7. **Frontend `.eslintrc.json`** - ESLint rules for TypeScript + Solid.js
8. **Frontend `.prettierrc`** - Code formatting rules
9. **Frontend `tailwind.config.js`** - Tailwind customization (Geist fonts, breakpoints)

### Docker Compose Placeholder

Create `docker-compose.yml` with basic structure (full implementation in Story 1.2):

```yaml
version: '3.9'

services:
  postgres:
    image: timescale/timescaledb:latest-pg15
    # Full configuration in Story 1.2

  backend:
    build: ./backend
    # Full configuration in Story 1.2

  frontend:
    build: ./frontend
    # Full configuration in Story 1.2

  traefik:
    image: traefik:v2.10
    # Full configuration in Story 1.2

  adminer:
    image: adminer:latest
    # Full configuration in Story 1.2
```

## Definition of Done

- [x] Project root directory `meteo-score/` created
- [x] Backend directory structure matches architecture specification exactly
- [x] Frontend directory structure matches architecture specification exactly
- [x] Python 3.11+ virtual environment created in `backend/venv/`
- [x] All backend dependencies installed and listed in `requirements.txt`
- [x] Frontend initialized with Solid.js TypeScript template
- [x] All frontend dependencies installed and listed in `package.json` and `package-lock.json`
- [x] Root `.env.example` file created with all required environment variables
- [x] Root `.gitignore` file created excluding venv, node_modules, .env, __pycache__
- [x] Root `README.md` created with project overview and setup instructions
- [x] Backend linting tools configured: ruff, black, mypy (`pyproject.toml`)
- [x] Backend test configuration created (`pytest.ini`)
- [x] Frontend linting tools configured: ESLint (`.eslintrc.json`), Prettier (`.prettierrc`)
- [x] Tailwind CSS configured with PostCSS (`tailwind.config.js`, `postcss.config.js`)
- [x] TypeScript configured with strict mode (`tsconfig.json`)
- [x] All Python package directories have `__init__.py` files
- [x] `docker-compose.yml` placeholder created (full implementation in Story 1.2)
- [x] Backend can start virtual environment without errors
- [x] Frontend can run `npm install` without errors
- [x] All configuration files are valid (no syntax errors)
- [x] Project structure verified against architecture document

## Related Files

- **Epic file:** `/home/fly/dev/meteo-score/_bmad-output/planning-artifacts/epics.md` (Story 1.1, lines 256-294)
- **Architecture:** `/home/fly/dev/meteo-score/_bmad-output/planning-artifacts/architecture-meteo-score-2026-01-10.md`
- **Product Brief:** `/home/fly/dev/meteo-score/_bmad-output/planning-artifacts/product-brief-meteo-score-2026-01-10.md`

## Success Validation

**After completing this story, you should be able to:**

1. Navigate the directory structure and find all expected folders
2. Activate the Python virtual environment and see Python 3.11+
3. Run `pip list` in backend and see all required dependencies installed
4. Run `npm list` in frontend and see all required dependencies installed
5. Open configuration files and see proper formatting (no syntax errors)
6. Verify `.gitignore` excludes virtual environments and node_modules
7. Read `README.md` and understand project setup from scratch
8. Confirm all `__init__.py` files exist in Python package directories
9. Run `ruff check backend/` without crashing (may report issues in empty files)
10. Run `npm run lint` in frontend without configuration errors

**What This Story DOES NOT Include:**
- Docker Compose service implementation (Story 1.2)
- Database schema creation (Epic 2)
- API route implementation (Epic 3)
- Frontend component implementation (Epic 5)
- Any actual code logic (only project structure and configuration)

---

**Story Prepared By:** BMAD Workflow
**Story File Created:** 2026-01-11
**Ready for Development:** Yes
