# Story 3.1: Forecast-Observation Matching Engine

Status: done

## Story

As a data analyst,
I want to automatically match forecast predictions with actual observations,
So that I can calculate deviations between predicted and observed weather parameters.

## Acceptance Criteria

1. **AC1: Temporal Matching** - Observation timestamp within ±30 minutes of forecast valid_time
2. **AC2: Spatial Matching** - Exact site_id match between forecast and observation
3. **AC3: Parameter Matching** - Exact parameter_id match (wind_speed, wind_direction, temperature)
4. **AC4: Horizon Calculation** - Calculate horizon = forecast.valid_time - forecast.forecast_run (in hours)
5. **AC5: Staging Table** - Matched pairs stored in `forecast_observation_pairs` table with all required fields
6. **AC6: Time Tolerance Boundaries** - ±29 min = match, ±31 min = no match
7. **AC7: Multiple Observations** - When multiple observations within tolerance, select closest to valid_time
8. **AC8: Idempotency** - Re-running matching doesn't create duplicates (UNIQUE constraint)
9. **AC9: Test Coverage** - >80% coverage with TDD approach

## Tasks / Subtasks

- [x] Task 1: Create database schema for intermediate storage (AC: 5, 8)
  - [x] 1.1: Create Alembic migration for `forecasts` table (if not exists)
  - [x] 1.2: Create Alembic migration for `observations` table (if not exists)
  - [x] 1.3: Create Alembic migration for `forecast_observation_pairs` staging table
  - [x] 1.4: Add indexes for efficient matching queries

- [x] Task 2: Create SQLAlchemy models (AC: 5)
  - [x] 2.1: Create `Forecast` model in `backend/core/models.py`
  - [x] 2.2: Create `Observation` model in `backend/core/models.py`
  - [x] 2.3: Create `ForecastObservationPair` model in `backend/core/models.py`

- [x] Task 3: Write TDD tests FIRST (AC: 1-9)
  - [x] 3.1: Create `backend/tests/test_matching_service.py`
  - [x] 3.2: Test exact time match (observation at forecast.valid_time)
  - [x] 3.3: Test time tolerance boundaries (±29 min = match, ±31 min = no match)
  - [x] 3.4: Test multiple observations within tolerance (select closest)
  - [x] 3.5: Test missing observation (no pair created)
  - [x] 3.6: Test multiple forecasts for same valid_time (all matched)
  - [x] 3.7: Test horizon calculation accuracy (6h, 12h, 24h, 48h forecasts)
  - [x] 3.8: Test idempotency (re-run doesn't duplicate)

- [x] Task 4: Implement MatchingService (AC: 1-4, 6-7)
  - [x] 4.1: Create `backend/services/matching_service.py`
  - [x] 4.2: Implement `match_forecasts_to_observations()` async method
  - [x] 4.3: Implement time tolerance logic (±30 min window)
  - [x] 4.4: Implement "closest observation" selection when multiple matches
  - [x] 4.5: Implement batch processing (1000 pairs at a time)
  - [x] 4.6: Add logging for unmatched forecasts/observations

- [x] Task 5: Verify coverage and cleanup (AC: 9)
  - [x] 5.1: Run `pytest --cov` and verify >80%
  - [x] 5.2: Address any failing tests
  - [x] 5.3: Manual test with sample data

## Dev Notes

### Critical Architecture Decision

**IMPORTANT:** The current schema stores deviations directly without intermediate `forecasts`/`observations` tables. This story requires creating these intermediate tables for proper matching.

The matching pipeline will be:
```
Collectors → forecasts/observations tables → MatchingService → forecast_observation_pairs → DeviationService → deviations hypertable
```

### Database Schema (from Epic 3.1)

```sql
-- New: forecasts table (if not exists)
CREATE TABLE forecasts (
  id SERIAL PRIMARY KEY,
  site_id INTEGER NOT NULL REFERENCES sites(id),
  model_id INTEGER NOT NULL REFERENCES models(id),
  parameter_id INTEGER NOT NULL REFERENCES parameters(id),
  forecast_run TIMESTAMPTZ NOT NULL,
  valid_time TIMESTAMPTZ NOT NULL,
  value DECIMAL(10,2) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(site_id, model_id, parameter_id, forecast_run, valid_time)
);

-- New: observations table (if not exists)
CREATE TABLE observations (
  id SERIAL PRIMARY KEY,
  site_id INTEGER NOT NULL REFERENCES sites(id),
  parameter_id INTEGER NOT NULL REFERENCES parameters(id),
  observation_time TIMESTAMPTZ NOT NULL,
  value DECIMAL(10,2) NOT NULL,
  source VARCHAR(50), -- 'ROMMA', 'FFVL', etc.
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(site_id, parameter_id, observation_time, source)
);

-- Staging table for matched pairs
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

### MatchingService Interface

```python
# backend/services/matching_service.py
from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

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
        pass
```

### Project Structure Notes

**New files to create:**
- `backend/services/__init__.py`
- `backend/services/matching_service.py`
- `backend/tests/test_matching_service.py`
- `backend/db/migrations/versions/YYYYMMDD_XXX_add_forecasts_observations_tables.py`

**Files to modify:**
- `backend/core/models.py` - Add Forecast, Observation, ForecastObservationPair models

**Alignment with existing patterns:**
- Follow SQLAlchemy 2.0 style from `backend/core/models.py`
- Use async/await patterns (AsyncSession)
- Use Decimal for values (consistent with existing Deviation model)
- Use TIMESTAMPTZ for all timestamps

### Technical Requirements from Architecture

[Source: _bmad-output/project-context.md#Critical Implementation Rules]

- **Async/Await:** ALL database operations MUST use `async`/`await`
- **SQLAlchemy:** Use `AsyncSession`, `select()` with `await session.execute()`
- **Type hints:** ALL functions MUST have complete type hints
- **Tests:** TDD approach, >80% coverage, pytest-asyncio for async tests
- **Naming:** snake_case for modules/functions, PascalCase for classes

### Previous Story Intelligence (2-7)

From story 2-7 completion notes:
- Test import paths use `collectors.*` not `backend.collectors.*`
- MetricsRegistry singleton pattern in `backend/api/routes/metrics.py`
- ValidationResult pattern with is_aberrant flag
- 454 tests currently passing, 95.36% coverage achieved

### Matching Logic Details

**Time tolerance implementation:**
```python
def is_within_tolerance(
    forecast_valid_time: datetime,
    observation_time: datetime,
    tolerance_minutes: int = 30
) -> bool:
    """Check if observation is within tolerance of forecast valid_time."""
    diff = abs((observation_time - forecast_valid_time).total_seconds())
    return diff <= tolerance_minutes * 60
```

**Horizon calculation:**
```python
def calculate_horizon(forecast_run: datetime, valid_time: datetime) -> int:
    """Calculate forecast horizon in hours."""
    diff = valid_time - forecast_run
    return int(diff.total_seconds() / 3600)
```

**Multiple observations selection:**
```python
# When multiple observations within tolerance, select closest
observations_in_range = [obs for obs in observations if is_within_tolerance(forecast.valid_time, obs.observation_time)]
if observations_in_range:
    closest_obs = min(observations_in_range, key=lambda o: abs((o.observation_time - forecast.valid_time).total_seconds()))
```

### Edge Cases to Handle

1. **No matching observation:** Skip forecast, log for monitoring
2. **Multiple observations in tolerance:** Select closest to valid_time
3. **Multiple forecasts for same valid_time:** Match each forecast independently
4. **Duplicate matching runs:** UNIQUE constraint prevents duplicates
5. **Timezone handling:** Use TIMESTAMPTZ, ensure all times are UTC

### Test Data Setup

```python
# Example test fixture
@pytest.fixture
async def sample_forecast(db_session):
    forecast = Forecast(
        site_id=1,
        model_id=1,  # AROME
        parameter_id=1,  # wind_speed
        forecast_run=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        valid_time=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        value=Decimal("25.5")
    )
    db_session.add(forecast)
    await db_session.commit()
    return forecast
```

### References

- [Epic 3 Definition: _bmad-output/planning-artifacts/epics.md#Epic-3]
- [Architecture: _bmad-output/planning-artifacts/architecture-meteo-score-2026-01-10.md]
- [Project Context: _bmad-output/project-context.md]
- [Existing Models: backend/core/models.py]
- [Data Models: backend/core/data_models.py]
- [Previous Story 2-7: _bmad-output/implementation-artifacts/2-7-implement-error-handling-retry-logic-and-data-validation.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No blocking issues encountered

### Completion Notes List

- Implemented TDD approach: wrote 21 comprehensive tests BEFORE implementation
- Created Alembic migration `002` for forecasts, observations, and forecast_observation_pairs tables
- Added 3 new SQLAlchemy models (Forecast, Observation, ForecastObservationPair) following existing patterns
- Implemented MatchingService with async/await patterns
- Added timezone normalization helper to handle SQLite test database timezone stripping
- All acceptance criteria verified:
  - AC1-3: Temporal, spatial, and parameter matching tested
  - AC4: Horizon calculation tested for 6h, 12h, 24h, 48h
  - AC5: Staging table with all required fields
  - AC6: Time tolerance boundaries (±29 min match, ±31 min no match)
  - AC7: Multiple observations select closest
  - AC8: Idempotency via UNIQUE constraint
  - AC9: 90.73% coverage (exceeds 80% requirement)
- Full test suite: 485 tests pass

### File List

**New Files:**
- backend/db/migrations/versions/20260115_0200_002_add_forecasts_observations_pairs.py
- backend/services/__init__.py
- backend/services/matching_service.py
- backend/tests/test_matching_service.py

**Modified Files:**
- backend/core/models.py (added Forecast, Observation, ForecastObservationPair models)
- backend/tests/conftest.py (added cleanup for new tables)

## Senior Developer Review

### Review Date
2026-01-15

### Issues Found and Fixed

| ID | Severity | Issue | Fix Applied |
|----|----------|-------|-------------|
| H1 | HIGH | O(n*m) nested loop performance | Pre-grouped observations by parameter_id using dict |
| M1 | MEDIUM | BATCH_SIZE defined but never used | Implemented actual batch processing every 1000 pairs |
| M2 | MEDIUM | IntegrityError rollback breaks session | Check existence before insert instead of catching errors |
| M3 | MEDIUM | Unused imports (Decimal, Optional) | Removed unused imports |
| M4 | MEDIUM | No input validation | Added ValueError for invalid site_id and date range |
| M5 | MEDIUM | Helper functions not exported | Added exports to __init__.py |

### Tests Added During Review

- `test_invalid_site_id_raises_error`: Validates site_id > 0
- `test_invalid_date_range_raises_error`: Validates start_date < end_date

### Final Test Results

- **23 matching service tests pass** (was 21, +2 for validation)
- **487 total tests pass**
- **90.72% coverage** (exceeds 80% requirement)

## Change Log

- 2026-01-15: Story created by SM agent with comprehensive developer context
- 2026-01-15: Implementation complete - all 21 tests pass, 90.73% coverage achieved
- 2026-01-15: Code review complete - 6 issues fixed (1 HIGH, 5 MEDIUM), 2 tests added
