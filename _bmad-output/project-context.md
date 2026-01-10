---
project_name: 'meteo-score'
user_name: 'boss'
date: '2026-01-10'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality', 'critical_antipatterns']
existing_patterns_found: 8
status: 'complete'
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

### Backend Stack
- **Python:** 3.11+ (async/await patterns, type hints required)
- **Web Framework:** FastAPI (native async support)
- **ORM:** SQLAlchemy (async mode with asyncpg driver - **NOT** psycopg2)
- **Validation:** Pydantic V2 (breaking changes from V1, use Field(alias=) for camelCase mapping)
- **Database:** TimescaleDB 2.13+ on PostgreSQL 15 (hypertables, continuous aggregates)
- **Scheduling:** APScheduler (in-process, cron-like)
- **Testing:** pytest + pytest-cov (>80% coverage enforced), pytest-asyncio, httpx

### Frontend Stack
- **Language:** TypeScript 5.0+ (strict mode enabled)
- **Framework:** Solid.js (reactive signals, NOT React)
- **Router:** @solidjs/router (official, file-based conventions)
- **Styling:** Tailwind CSS 4.0 (utility-first, mobile-first)
- **Typography:** Geist Sans + Geist Mono
- **Visualization:** D3.js (custom charts, manual DOM manipulation in refs)
- **Build Tool:** Vite (with vite-plugin-solid, esbuild)

### Data Processing
- **Météo GRIB2:** cfgrib + xarray (binary format parsing)
- **JSON APIs:** requests (synchronous OK for collectors)
- **HTML Scraping:** BeautifulSoup4 (beacon data extraction)
- **Data Manipulation:** pandas (time-series calculations)

### Infrastructure
- **Containerization:** Docker Compose (dev + prod parity)
- **Reverse Proxy:** Traefik v2.10 (automatic HTTPS via Let's Encrypt)
- **Database Migrations:** Alembic (schema versioning)
- **CI/CD:** GitHub Actions (automated tests + deployment)

### Version Constraints (CRITICAL)
- ⚠️ PostgreSQL **MUST** be version 15 (TimescaleDB 2.13+ dependency)
- ⚠️ Python **MUST** be 3.11+ (async SQLAlchemy patterns require it)
- ⚠️ Use **asyncpg** driver (psycopg2 is synchronous only)
- ⚠️ Pydantic V2 API is incompatible with V1 (use Field(alias="camelCase") for API mapping)

---

## Critical Implementation Rules

### Language-Specific Rules

#### Python Rules (Backend)

**Naming Conventions:**
- Modules/functions: `snake_case` (deviation_engine.py, calculate_deviation())
- Classes: `PascalCase` (MeteoParapenteCollector, Site)
- Constants: `UPPER_SNAKE_CASE` (MAX_RETRIES, API_ENDPOINT)
- Private members: Leading underscore (_parse_response(), _internal_field)

**Async/Await Patterns (CRITICAL):**
- ⚠️ ALL database operations MUST use `async`/`await`
- ⚠️ ALL FastAPI routes MUST be async functions
- ⚠️ Use `AsyncSession` from SQLAlchemy (NEVER synchronous Session)
- ⚠️ Collector methods MUST be async: `async def collect_forecast(...)`

**Type Hints (Required):**
- ALL functions MUST have complete type hints
- Example: `async def get_site(site_id: int) -> Site:`
- Use `from typing import List, Dict, Optional, TypeVar` as needed

**Pydantic V2 Field Mapping (snake_case ↔ camelCase):**
- Backend internal: `snake_case` (site_id, forecast_value, observed_value)
- JSON API: `camelCase` (siteId, forecastValue, observedValue)
- Use `Field(alias="camelCase")` to map between them
- Set `populate_by_name = True` in model Config to accept both formats
- Example:
  ```python
  class DeviationResponse(BaseModel):
      site_id: int = Field(alias="siteId")
      forecast_value: float = Field(alias="forecastValue")

      class Config:
          populate_by_name = True
  ```

**Error Handling:**
- Use FastAPI `HTTPException` for API errors
- Custom domain exceptions: `class CollectorError(Exception)`, `class ParsingError(Exception)`
- Log errors with appropriate levels: `logger.error(f"Collection failed: {e}")`

#### TypeScript Rules (Frontend)

**Naming Conventions:**
- Components: `PascalCase.tsx` (DeviationChart.tsx, SiteSearch.tsx)
- Utilities: `camelCase.ts` (api.ts, types.ts, formatters.ts)
- Functions/variables: `camelCase` (fetchDeviations, forecastValue, siteId)
- Constants: `UPPER_SNAKE_CASE` (API_BASE_URL, DEFAULT_DATE_FORMAT)
- Types/Interfaces: `PascalCase` (Deviation, Site, Model, ApiResponse<T>)

**Solid.js Signal Naming (CRITICAL - This is NOT React):**
- Boolean flags: `isLoading{Resource}` - BE SPECIFIC! (isLoadingSites, isLoadingDeviations)
- ❌ NEVER use generic `loading` or `isLoading` - always specify WHAT
- Data signals: Descriptive nouns (sites, deviations, selectedSite)
- Setters: `set{SignalName}` (setIsLoadingSites, setSites, setSelectedSite)

**Immutability Rules (CRITICAL for Solid.js Reactivity):**
- ⚠️ NEVER mutate signal values directly
- ❌ BAD: `sites().push(newSite)` - breaks reactivity!
- ✅ GOOD: `setSites([...sites(), newSite])` - creates new array
- ✅ GOOD: `setSites(prev => [...prev, newSite])` - functional update
- Always create new objects/arrays for updates

**Import Organization:**
- External libraries first: `import { createSignal } from 'solid-js';`
- Local imports second: `import { fetchDeviations } from '../lib/api';`
- Types last: `import type { Deviation, Site } from '../lib/types';`

---

### Framework-Specific Rules

#### FastAPI Patterns (Backend)

**Dependency Injection:**
- Use `Depends()` for database sessions and shared dependencies
- Example: `async def get_deviations(db: AsyncSession = Depends(get_db)):`
- NEVER create database sessions manually in route functions

**Query Parameter Mapping (camelCase API):**
- Use `Query(..., alias="camelCase")` to maintain API naming convention
- Example: `site_id: int = Query(..., alias="siteId")`
- Backend receives snake_case variable, API expects camelCase parameter

**Response Models:**
- ALWAYS specify `response_model` in route decorators
- Example: `@router.get("/", response_model=List[DeviationResponse])`
- Enables automatic Pydantic serialization with Field(alias=) mapping

**Exception Handling:**
- Use `HTTPException` for all API errors
- Standard status codes: 400 (ValidationError), 404 (NotFound), 429 (RateLimitError), 500 (InternalServerError)
- Always include descriptive `detail` message

**SQLAlchemy Async Patterns (CRITICAL):**
- ⚠️ ALWAYS use `async with` for session lifecycle management
- ⚠️ ALWAYS await session operations: `await session.execute()`, `await session.commit()`
- Use new-style queries: `await session.execute(select(Model).where(...))`
- Call `.scalars().all()` or `.scalar_one_or_none()` on results
- ❌ NEVER use old `session.query()` (deprecated in async mode)

#### Solid.js Patterns (Frontend - NOT React!)

**Reactive Primitives (Different from React):**
- ⚠️ Solid.js is NOT React - do not use React hooks!
- Use `createSignal()` for local state (NOT `useState()`)
- Use `createStore()` for complex objects (NOT `useReducer()`)
- Use `createMemo()` for derived values (NOT `useMemo()`)
- Use `createEffect()` for side effects (NOT `useEffect()`)
- Use `onMount()` for component initialization (NOT `useEffect(() => {}, [])`)

**Control Flow Components (NOT JSX Conditionals):**
- Use `<Show when={condition}>` instead of `{condition && <Component />}`
- Use `<For each={array}>` instead of `{array.map()}`
- Use `<Switch>/<Match>` for multiple conditions instead of ternaries
- Solid.js optimizes these differently - DO NOT use JSX patterns from React

**Event Handlers:**
- Use camelCase: `onClick`, `onChange` (NOT lowercase `onclick`, `onchange`)
- Pass functions directly: `onClick={handleClick}` (NOT `onClick={() => handleClick()}`)
- Solid.js uses native DOM events, NOT React's synthetic events

**Component Props (CRITICAL - Reactivity):**
- ⚠️ DO NOT destructure props in function parameters - breaks reactivity!
- ❌ BAD: `function Chart({ siteId, modelId })` - loses reactivity
- ✅ GOOD: `function Chart(props: ChartProps)` - access via `props.siteId`
- Define props interface: `interface ChartProps { siteId: number; modelId: number; }`

**Router Patterns (@solidjs/router):**
- Use `<A>` component for navigation (NOT `<a>` or React's `<Link>`)
- Access route params: `const params = useParams(); const id = params.id;`
- Programmatic navigation: `const navigate = useNavigate(); navigate('/path');`
- Use `useLocation()` for current location info

---

### Testing Rules

#### Backend Testing (pytest)

**Test Organization:**
- Location: `backend/tests/` (separate from source code)
- Naming: `test_{module}.py` (test_collectors.py, test_deviation_engine.py, test_api_sites.py)
- Fixtures: Centralized in `backend/tests/conftest.py` (test DB, mock collectors, common data)

**TDD Approach (CRITICAL for Data Parsers):**
- ⚠️ Write tests BEFORE implementing data collectors (AROME, Meteo-Parapente, ROMMA, FFVL)
- Pattern: Red (failing test) → Green (passing test) → Refactor
- Data parsing is mission-critical - tests validate correctness from the start

**Coverage Requirements (Enforced):**
- ⚠️ >80% coverage REQUIRED (enforced in pytest.ini and CI)
- Use `pytest --cov=backend --cov-report=term-missing` to measure
- CI MUST fail if coverage drops below 80%

**Async Test Patterns:**
- Use `@pytest.mark.asyncio` decorator for async tests
- Import: `import pytest` then mark with `@pytest.mark.asyncio`
- Example:
  ```python
  @pytest.mark.asyncio
  async def test_collect_forecast():
      collector = MeteoParapenteCollector()
      data = await collector.collect_forecast(site_id=1, forecast_run=datetime.now())
      assert len(data) > 0
  ```

**Test Database:**
- ⚠️ Use SEPARATE test database (NEVER use production DB in tests)
- Fixtures create/teardown test DB per session
- Use in-memory SQLite OR separate PostgreSQL test instance

**API Testing (FastAPI TestClient):**
- Use `httpx.AsyncClient` for async API tests
- Example:
  ```python
  async with AsyncClient(app=app, base_url="http://test") as ac:
      response = await ac.get("/sites")
  assert response.status_code == 200
  ```

**Mock External APIs (CRITICAL):**
- ⚠️ NEVER call real external APIs in tests (AROME, Meteo-Parapente, beacons)
- Use `pytest-mock` or `unittest.mock` to mock responses
- Create fixtures for common mock data

#### Frontend Testing (Vitest - Optional for MVP)

**Test Organization:**
- Co-located: `frontend/src/**/*.test.tsx` OR centralized: `frontend/tests/`
- Naming: `{Component}.test.tsx` (DeviationChart.test.tsx)

**Testing Library (Solid.js-Specific):**
- ⚠️ Use `@solidjs/testing-library` (NOT React Testing Library!)
- Import: `import { render, screen } from '@solidjs/testing-library';`
- Solid.js has different reactivity model - needs Solid-specific testing tools

**Component Test Pattern:**
- Render component, query DOM, assert behavior
- Use `render(() => <Component {...props} />)` - note the arrow function!

#### 6-Level Validation Strategy (Data Quality)

Your architecture specifies a comprehensive validation approach:

1. **Manual Validation:** Human review of initial POC samples (first week)
2. **Unit Tests:** pytest for parsers (>80% coverage, TDD approach)
3. **Automated Alerts:** Flag aberrant values (wind >200 km/h, temp <-50°C, deviation >100)
4. **Cross-Validation:** Compare multiple observation sources when available
5. **Historical Comparison:** Statistical outlier detection
6. **Ship-and-Iterate:** Deploy cautiously, allow margin for error correction

---

### Code Quality & Style Rules

#### Backend Code Quality (Python)

**Linting & Formatting:**
- **ruff:** Python linter (fast, replaces flake8/isort/pyupgrade)
- **black:** Code formatter (opinionated, 88 char line length)
- **mypy:** Static type checker (enforce all type hints)
- Use pre-commit hooks to run these automatically

**Code Organization:**
- Collectors: `backend/collectors/{source_name}.py` (each implements BaseCollector)
- Core: `backend/core/` (models.py, schemas.py, deviation_engine.py, database.py, config.py)
- API: `backend/api/routes/{resource}.py` (sites.py, deviations.py, bias_summary.py)
- Tests: `backend/tests/test_{module}.py` (separate from source)

**Import Organization:**
```python
# 1. Standard library
from datetime import datetime
from typing import List, Optional

# 2. Third-party
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local imports
from core.models import Site
from core.schemas import SiteResponse
```

**Documentation:**
- Docstrings for all public classes/functions (Google style)
- Include Args, Returns, Raises sections
- Avoid obvious comments - code should be self-explanatory

#### Frontend Code Quality (TypeScript)

**Linting & Formatting:**
- **ESLint:** TypeScript linter with recommended config
- **Prettier:** Code formatter (consistent style)
- Use pre-commit hooks for auto-formatting

**Code Organization:**
- Components: `frontend/src/components/PascalCase.tsx`
- Pages: `frontend/src/pages/PascalCase.tsx`
- Utilities: `frontend/src/lib/camelCase.ts`
- Types: Centralized in `frontend/src/lib/types.ts`

**File Naming (CRITICAL):**
- Backend modules: `snake_case.py` (deviation_engine.py)
- Backend tests: `test_{module}.py`
- Frontend components: `PascalCase.tsx` (DeviationChart.tsx)
- Frontend utilities: `camelCase.ts` (api.ts, formatters.ts)
- Frontend tests: `{Component}.test.tsx`

**Comment Style:**
- Backend: Docstrings for public APIs, `#` for complex logic
- Frontend: JSDoc `/** */` for functions, `//` for inline comments
- Comment WHY, not WHAT (code should be self-explanatory)

#### Database Naming (Consistency)

- Tables: `snake_case` plural (deviations, sites, models, parameters)
- Columns: `snake_case` (site_id, forecast_value, observed_value)
- Foreign keys: `{table_singular}_id` (site_id, model_id)
- Indexes: `idx_{table}_{columns}`
- ⚠️ ALL timestamps: Use `TIMESTAMPTZ` (timezone-aware), NEVER `TIMESTAMP`

#### API Response Format (Consistency)

**Standard Response:**
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

**Error Response:**
```json
{
  "error": "ValidationError",
  "detail": "Invalid date range: startDate must be before endDate",
  "statusCode": 400
}
```

**Field Naming:**
- Use `camelCase` in JSON (siteId, forecastValue, observedValue)
- Dates: ISO 8601 with timezone (`"2026-01-10T14:30:00Z"`)
- Numbers: JSON numbers, NOT strings (`25.5` not `"25.5"`)

---

### Critical Don't-Miss Rules (Anti-Patterns & Gotchas)

#### Anti-Patterns Backend

**❌ Mixing Naming Conventions:**
- NEVER mix camelCase in Python: `class meteoParapenteCollector` ❌
- ALWAYS use Python conventions: `class MeteoParapenteCollector` ✅

**❌ Using Synchronous Database Operations:**
- NEVER use `psycopg2` (synchronous) - use `asyncpg` ✅
- NEVER use synchronous `Session` - use `AsyncSession` ✅
- NEVER use old `session.query()` - use `select()` with `await session.execute()` ✅

**❌ Returning Errors as Success:**
- NEVER: `return {"error": "Not found"}` ❌
- ALWAYS: `raise HTTPException(status_code=404, detail="Not found")` ✅

**❌ Inconsistent Date Formats:**
- NEVER use Unix timestamps: `{"timestamp": 1736518200}` ❌
- NEVER use dates without time: `"2026-01-10"` ❌
- NEVER use `TIMESTAMP` in DB (no timezone) ❌
- ALWAYS use ISO 8601 with timezone: `"2026-01-10T14:30:00Z"` ✅
- ALWAYS use `TIMESTAMPTZ` in PostgreSQL ✅

**❌ Forgetting Field Aliases:**
- NEVER forget `Field(alias="camelCase")` in Pydantic schemas
- NEVER forget `Query(..., alias="camelCase")` for API params
- Without aliases, API violates camelCase convention

#### Anti-Patterns Frontend (Solid.js)

**❌ Using React Patterns (CRITICAL - This is NOT React!):**
- NEVER use `useState`, `useEffect`, `useMemo`, `useReducer` ❌
- NEVER use `{condition && <Component />}` ❌
- NEVER use `array.map()` for rendering lists ❌
- NEVER destructure props: `function Chart({ siteId })` ❌ (breaks reactivity!)
- ALWAYS use `createSignal`, `createEffect`, `createMemo` ✅
- ALWAYS use `<Show when={}>`, `<For each={}>` ✅
- ALWAYS access props via object: `props.siteId` ✅

**❌ Mutating Signals (Breaks Reactivity):**
- NEVER: `sites().push(newSite)` ❌
- NEVER: `site().name = "New"` ❌
- ALWAYS: `setSites([...sites(), newSite])` ✅
- ALWAYS create new objects/arrays for updates

**❌ Generic Loading States:**
- NEVER: `const [loading, setLoading] = createSignal(false)` ❌
- ALWAYS: `const [isLoadingSites, setIsLoadingSites] = createSignal(false)` ✅
- Be specific about WHAT is loading

**❌ Lowercase Event Handlers:**
- NEVER: `onclick`, `onchange` ❌
- ALWAYS: `onClick`, `onChange` ✅

#### Architecture-Specific Gotchas

**Storage Model (Deviation-Only - CRITICAL):**
- ⚠️ Store ONLY: `forecast_value`, `observed_value`, `deviation`
- ⚠️ DO NOT store complete GRIB2 files or full beacon datasets
- This is a 100x storage reduction breakthrough - respect it!

**Modular Collectors (Strategy Pattern):**
- ⚠️ ALL collectors MUST implement `BaseCollector` interface
- ⚠️ Each collector in separate file: `backend/collectors/{source}.py`
- ⚠️ Collectors NEVER write to DB directly - return data to scheduler

**TimescaleDB-Specific:**
- ⚠️ Use `create_hypertable('deviations', 'timestamp', chunk_time_interval='7 days')`
- ⚠️ Use continuous aggregates for precomputed metrics (daily/weekly MAE)
- ⚠️ DO NOT treat as regular PostgreSQL - leverage time-series features

**API Calls (Frontend):**
- ⚠️ ALL API calls MUST go through `frontend/src/lib/api.ts`
- ⚠️ NEVER use `fetch()` directly in components
- Ensures consistent error handling and type safety

**Self-Hosted Infrastructure (NO External Services):**
- ❌ NO Auth0, Clerk, Supabase Auth
- ❌ NO PlanetScale, Neon, AWS RDS
- ❌ NO Datadog, New Relic
- ❌ NO CDN dependencies
- ✅ Everything runs in Docker Compose

#### Security & Performance Gotchas

**Public Data Platform:**
- No authentication needed (all data is public)
- DO implement rate limiting (100 req/min per IP)
- DO validate all inputs with Pydantic schemas

**External API Rate Limits:**
- ⚠️ AROME has 50 req/min limit - RESPECT IT
- ⚠️ Implement exponential backoff retry (max 3 attempts)
- ⚠️ NEVER expose API keys in frontend code

**Edge Cases:**
- Handle missing observations gracefully (forecasts without matching obs)
- Handle API failures without crashing pipeline
- Validate aberrant values: wind >200 km/h, temp <-50°C, deviation >100

---

## Quick Reference

**Read the architecture document first:** `_bmad-output/planning-artifacts/architecture-meteo-score-2026-01-10.md`

This project context file highlights the unobvious details that AI agents might miss. When in doubt, refer to the full architecture document for comprehensive guidance.

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Refer to the architecture document for comprehensive context
- Update this file if new critical patterns emerge

**For Humans:**

- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time
- Document only unobvious patterns that agents might miss

**Last Updated:** 2026-01-10
