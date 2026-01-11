# Story 2.1: Implement BaseCollector Interface and Core Data Models

Status: done

## Story

As a developer,
I want to create the BaseCollector abstract interface and core data models for the collector architecture,
So that all weather data collectors follow a consistent pattern and can be orchestrated uniformly.

## Acceptance Criteria

1. **AC1: BaseCollector Abstract Class** - Create `backend/collectors/base.py` with abstract methods:
   - `async def collect_forecast(site_id: int, forecast_run: datetime) -> List[ForecastData]`
   - `async def collect_observation(site_id: int, observation_time: datetime) -> List[ObservationData]`
   - Both methods are abstract and must be implemented by subclasses

2. **AC2: Data Transfer Objects** - Create `backend/core/data_models.py` with dataclasses:
   - `ForecastData`: site_id, model_id, parameter_id, forecast_run, valid_time, horizon, value
   - `ObservationData`: site_id, parameter_id, observation_time, value
   - All fields properly typed with type hints

3. **AC3: Deviation Engine** - Create `backend/core/deviation_engine.py`:
   - `calculate_deviation(forecast: ForecastData, observation: ObservationData) -> Decimal`
   - Stateless function: returns `forecast.value - observation.value`

4. **AC4: Collector Utilities** - Create `backend/collectors/utils.py`:
   - Exponential backoff retry decorator with configurable max_retries (default=3)
   - HTTP client wrapper with timeout and error handling
   - Date/time parsing utilities for various formats

5. **AC5: Complete Type Hints** - All functions have complete type hints

6. **AC6: Unit Tests** - Create `backend/tests/test_base_collector.py`:
   - Test deviation calculation with various inputs (positive/negative/zero deviations)
   - Test retry logic with mock failures
   - Test data model validation
   - Test coverage >80% for all new code

## Tasks / Subtasks

- [x] Task 1: Create data transfer objects (AC: 2)
  - [x] 1.1: Create `backend/core/data_models.py`
  - [x] 1.2: Define `ForecastData` dataclass with all required fields
  - [x] 1.3: Define `ObservationData` dataclass with all required fields
  - [x] 1.4: Add type hints using Decimal for numeric values

- [x] Task 2: Create deviation engine (AC: 3)
  - [x] 2.1: Create `backend/core/deviation_engine.py`
  - [x] 2.2: Implement `calculate_deviation()` function
  - [x] 2.3: Add docstring with Args, Returns, Raises

- [x] Task 3: Create collector utilities (AC: 4)
  - [x] 3.1: Create `backend/collectors/utils.py`
  - [x] 3.2: Implement `@retry_with_backoff` decorator
  - [x] 3.3: Implement `HttpClient` class with timeout handling
  - [x] 3.4: Implement date parsing utilities

- [x] Task 4: Create BaseCollector abstract class (AC: 1)
  - [x] 4.1: Create `backend/collectors/base.py`
  - [x] 4.2: Define `BaseCollector` ABC with abstract methods
  - [x] 4.3: Import data models for type hints

- [x] Task 5: Write unit tests (AC: 6)
  - [x] 5.1: Create `backend/tests/test_base_collector.py`
  - [x] 5.2: Test deviation calculation (positive, negative, zero)
  - [x] 5.3: Test retry decorator with mock failures
  - [x] 5.4: Test ForecastData/ObservationData validation
  - [x] 5.5: Verify >80% coverage

- [x] Task 6: Verify type hints and run type-check (AC: 5)
  - [x] 6.1: Run `mypy backend/collectors backend/core/data_models.py backend/core/deviation_engine.py`
  - [x] 6.2: Fix any type errors

## Dev Notes

### Architecture Patterns

- **Strategy Pattern**: All collectors implement `BaseCollector` interface
- **Stateless Functions**: `deviation_engine.py` has no state, pure functions
- **Data Transfer Objects**: Use `@dataclass` for lightweight data containers (NOT Pydantic - those are for API responses)
- **Async/Await**: ALL collector methods MUST be async

### Existing Code Context

The backend already has SQLAlchemy models in `backend/core/models.py`:
- `Site`, `Model`, `Parameter`, `Deviation` ORM models
- Deviation table has: `timestamp`, `site_id`, `model_id`, `parameter_id`, `horizon`, `forecast_value`, `observed_value`, `deviation`

The new data models (`ForecastData`, `ObservationData`) are **transfer objects** for passing data between collectors and the database layer. They are NOT ORM models.

### File Structure (Create These Files)

```
backend/
├── collectors/
│   ├── __init__.py (exists - empty)
│   ├── base.py      ← NEW: BaseCollector ABC
│   └── utils.py     ← NEW: Retry decorator, HTTP client
├── core/
│   ├── models.py (exists - SQLAlchemy ORM)
│   ├── schemas.py (exists - Pydantic API responses)
│   ├── data_models.py    ← NEW: ForecastData, ObservationData dataclasses
│   └── deviation_engine.py ← NEW: calculate_deviation()
└── tests/
    └── test_base_collector.py ← NEW: Unit tests
```

### Code Patterns to Follow

**Python Naming:**
- Classes: `PascalCase` (BaseCollector, ForecastData)
- Functions: `snake_case` (calculate_deviation, retry_with_backoff)
- Constants: `UPPER_SNAKE_CASE` (MAX_RETRIES, DEFAULT_TIMEOUT)

**Type Hints (Required):**
```python
from decimal import Decimal
from datetime import datetime
from typing import List

async def collect_forecast(
    self,
    site_id: int,
    forecast_run: datetime
) -> List[ForecastData]:
    ...
```

**Dataclass Pattern:**
```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class ForecastData:
    site_id: int
    model_id: int
    parameter_id: int
    forecast_run: datetime
    valid_time: datetime
    horizon: int  # hours ahead
    value: Decimal
```

**Retry Decorator Pattern:**
```python
import asyncio
from functools import wraps
from typing import TypeVar, Callable, Any

T = TypeVar("T")

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for exponential backoff retry logic."""
    ...
```

### Testing Standards

- Use `pytest` with `pytest-asyncio` for async tests
- Mock external APIs - NEVER call real endpoints in tests
- Use `pytest-mock` or `unittest.mock`
- Target >80% coverage

**Test Pattern:**
```python
import pytest
from decimal import Decimal
from backend.core.deviation_engine import calculate_deviation
from backend.core.data_models import ForecastData, ObservationData

def test_calculate_deviation_positive():
    forecast = ForecastData(...)
    observation = ObservationData(...)
    result = calculate_deviation(forecast, observation)
    assert result == Decimal("5.0")  # forecast was 5 higher than observed
```

### Project Structure Notes

- All new files go in existing directories (no new folders needed)
- `backend/collectors/__init__.py` already exists
- Update `__init__.py` files to export new classes

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1]
- [Source: _bmad-output/planning-artifacts/architecture-meteo-score-2026-01-10.md#Collectors]
- [Source: _bmad-output/project-context.md#Backend Stack]
- [Source: backend/core/models.py - Existing ORM models]
- [Source: backend/core/schemas.py - Existing Pydantic schemas]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Created `ForecastData` and `ObservationData` frozen dataclasses with Decimal values for precision
- Implemented `calculate_deviation()` with validation for matching site_id and parameter_id
- Created comprehensive `utils.py` with:
  - `@retry_with_backoff` decorator with exponential backoff (configurable max_retries, base_delay, max_delay)
  - `HttpClient` async context manager with `get()`, `get_text()`, `get_bytes()` methods
  - Date parsing utilities: `parse_iso_datetime()`, `parse_unix_timestamp()`, `parse_datetime_flexible()`
  - Custom exceptions: `CollectorError`, `HttpClientError`, `RetryExhaustedError`
- Implemented `BaseCollector` ABC with async abstract methods for forecast and observation collection
- Created 40 unit tests covering all components (10 added during code review)
- All 127 tests pass (40 new + 87 existing)
- Test coverage: 81.82% (above 80% requirement)
- Type check passes with mypy

**Code Review Fixes Applied:**
- Added HTTP error tests (4xx, 5xx, network errors, invalid JSON)
- Added CollectorError exception tests
- Updated `collectors/__init__.py` with proper exports
- Updated `core/__init__.py` with ForecastData, ObservationData, calculate_deviation exports
- Fixed incorrect timestamp in docstring examples (1736596800 → 1768132800)
- Removed unused AsyncMock import

### File List

**New Files:**
- `backend/core/data_models.py` - ForecastData, ObservationData dataclasses
- `backend/core/deviation_engine.py` - calculate_deviation() function
- `backend/collectors/base.py` - BaseCollector abstract class
- `backend/collectors/utils.py` - Retry decorator, HttpClient, date parsing utilities
- `backend/tests/test_base_collector.py` - 40 unit tests

**Modified Files:**
- `backend/collectors/__init__.py` - Added exports for BaseCollector, utilities, exceptions
- `backend/core/__init__.py` - Added exports for data_models and deviation_engine

## Change Log

- 2026-01-11: Implemented Story 2.1 - BaseCollector interface and core data models
- 2026-01-11: Code review fixes - Added 10 tests, updated __init__.py exports, fixed docstrings
