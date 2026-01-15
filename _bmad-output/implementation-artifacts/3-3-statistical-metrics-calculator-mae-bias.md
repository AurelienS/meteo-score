# Story 3.3: Statistical Metrics Calculator (MAE, Bias)

Status: done

## Story

As a data analyst,
I want to calculate statistical accuracy metrics (MAE, bias, confidence intervals),
So that I can objectively compare forecast model performance.

## Acceptance Criteria

1. **AC1: MAE Calculation** - `MAE = mean(abs(deviation))` for each model/site/parameter/horizon combination
2. **AC2: Bias Calculation** - `bias = mean(deviation)` where positive = underestimate, negative = overestimate
3. **AC3: Confidence Intervals** - Calculate 95% CI using scipy t-distribution
4. **AC4: Standard Deviation** - Calculate `std_dev = stddev(deviation)` for variability analysis
5. **AC5: Sample Size Tracking** - Track number of deviations used in calculation
6. **AC6: Confidence Levels** - Determine data confidence: insufficient (<30), preliminary (30-90), validated (>=90)
7. **AC7: Min/Max Deviations** - Track min and max deviation values for range analysis
8. **AC8: Persistence** - Store calculated metrics in `accuracy_metrics` table with UNIQUE constraint
9. **AC9: Test Coverage** - >80% coverage with TDD approach

## Tasks / Subtasks

- [x] Task 1: Create database schema for accuracy_metrics (AC: 8)
  - [x] 1.1: Create Alembic migration for `accuracy_metrics` table
  - [x] 1.2: Add indexes for efficient querying
  - [x] 1.3: Create SQLAlchemy model `AccuracyMetric`

- [x] Task 2: Write TDD tests FIRST (AC: 1-9)
  - [x] 2.1: Create `backend/tests/test_metrics_service.py`
  - [x] 2.2: Test MAE calculation accuracy (sample deviations → correct MAE)
  - [x] 2.3: Test bias calculation (positive for underestimate, negative for overestimate)
  - [x] 2.4: Test confidence interval calculation (scipy t-distribution)
  - [x] 2.5: Test confidence level thresholds (29 = insufficient, 31 = preliminary, 91 = validated)
  - [x] 2.6: Test edge case: single sample (std_dev = 0)
  - [x] 2.7: Test edge case: all deviations identical
  - [x] 2.8: Test idempotency (re-running updates, doesn't duplicate)
  - [x] 2.9: Test input validation

- [x] Task 3: Implement MetricsService class (AC: 1-7)
  - [x] 3.1: Create `backend/services/metrics_service.py`
  - [x] 3.2: Implement `calculate_accuracy_metrics()` async method
  - [x] 3.3: Implement `determine_confidence_level()` helper
  - [x] 3.4: Implement `calculate_confidence_interval()` with scipy.stats
  - [x] 3.5: Add input validation with ValueError

- [x] Task 4: Implement persistence layer (AC: 8)
  - [x] 4.1: Implement `save_metrics()` method with upsert logic
  - [x] 4.2: Handle UNIQUE constraint (update on conflict)
  - [x] 4.3: Add logging for metrics calculation

- [x] Task 5: Integration and verification (AC: 9)
  - [x] 5.1: Run `pytest --cov` and verify >80%
  - [x] 5.2: Test with sample deviations from story 3-2
  - [x] 5.3: Verify metrics stored correctly
  - [x] 5.4: Update services/__init__.py exports

## Dev Notes

### Mathematical Definitions

**Mean Absolute Error (MAE):**
```python
MAE = mean(abs(deviation))
# Lower MAE = more accurate forecasts
```

**Bias (Systematic Error):**
```python
bias = mean(deviation)
# Positive bias: model systematically underestimates (observed > forecast)
# Negative bias: model systematically overestimates (observed < forecast)
```

**Confidence Interval (95%):**
```python
from scipy import stats

def calculate_confidence_interval(
    bias: float,
    std_dev: float,
    sample_size: int,
    confidence: float = 0.95
) -> tuple[float, float]:
    """Calculate 95% CI using t-distribution."""
    if sample_size <= 1:
        return (bias, bias)  # No CI possible

    t_stat = stats.t.ppf((1 + confidence) / 2, sample_size - 1)
    se = std_dev / (sample_size ** 0.5)  # Standard error
    margin = t_stat * se
    return (bias - margin, bias + margin)
```

### Database Schema

**New: accuracy_metrics table:**
```sql
CREATE TABLE accuracy_metrics (
  id SERIAL PRIMARY KEY,
  model_id INTEGER NOT NULL REFERENCES models(id),
  site_id INTEGER NOT NULL REFERENCES sites(id),
  parameter_id INTEGER NOT NULL REFERENCES parameters(id),
  horizon INTEGER NOT NULL,
  mae DECIMAL(10, 4) NOT NULL,
  bias DECIMAL(10, 4) NOT NULL,
  std_dev DECIMAL(10, 4) NOT NULL,
  sample_size INTEGER NOT NULL,
  confidence_level VARCHAR(20) NOT NULL, -- 'insufficient', 'preliminary', 'validated'
  ci_lower DECIMAL(10, 4),  -- 95% CI lower bound
  ci_upper DECIMAL(10, 4),  -- 95% CI upper bound
  min_deviation DECIMAL(10, 4) NOT NULL,
  max_deviation DECIMAL(10, 4) NOT NULL,
  calculated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(model_id, site_id, parameter_id, horizon)
);

CREATE INDEX idx_metrics_site_param ON accuracy_metrics(site_id, parameter_id);
CREATE INDEX idx_metrics_confidence ON accuracy_metrics(confidence_level);
CREATE INDEX idx_metrics_model_horizon ON accuracy_metrics(model_id, horizon);
```

### MetricsService Interface

```python
# backend/services/metrics_service.py
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

@dataclass
class AccuracyMetrics:
    """Data class for calculated accuracy metrics."""
    model_id: int
    site_id: int
    parameter_id: int
    horizon: int
    mae: Decimal
    bias: Decimal
    std_dev: Decimal
    sample_size: int
    confidence_level: str  # 'insufficient', 'preliminary', 'validated'
    ci_lower: Optional[Decimal]
    ci_upper: Optional[Decimal]
    min_deviation: Decimal
    max_deviation: Decimal

class MetricsService:
    """Service for calculating forecast accuracy metrics."""

    PRELIMINARY_THRESHOLD: int = 30   # days of data
    VALIDATED_THRESHOLD: int = 90     # days of data

    async def calculate_accuracy_metrics(
        self,
        db: AsyncSession,
        model_id: int,
        site_id: int,
        parameter_id: int,
        horizon: int,
    ) -> AccuracyMetrics:
        """
        Calculate MAE, bias, and confidence metrics from deviations.

        Args:
            db: Async database session.
            model_id: ID of the forecast model.
            site_id: ID of the site.
            parameter_id: ID of the parameter.
            horizon: Forecast horizon in hours.

        Returns:
            AccuracyMetrics dataclass with calculated values.

        Raises:
            ValueError: If no deviations found for the combination.
        """
        pass

    def determine_confidence_level(self, sample_size: int) -> str:
        """Determine data confidence based on sample size."""
        if sample_size < self.PRELIMINARY_THRESHOLD:
            return 'insufficient'
        elif sample_size < self.VALIDATED_THRESHOLD:
            return 'preliminary'
        else:
            return 'validated'

    def calculate_confidence_interval(
        self,
        bias: float,
        std_dev: float,
        sample_size: int,
        confidence: float = 0.95,
    ) -> tuple[float, float]:
        """Calculate confidence interval using t-distribution."""
        pass

    async def save_metrics(
        self,
        db: AsyncSession,
        metrics: AccuracyMetrics,
    ) -> None:
        """Save or update metrics in database (upsert)."""
        pass
```

### Confidence Level Thresholds

| Sample Size | Confidence Level | Description |
|-------------|------------------|-------------|
| < 30 | insufficient | Not enough data for reliable statistics |
| 30-89 | preliminary | Moderate confidence, trends visible |
| >= 90 | validated | High confidence, statistically significant |

### Project Structure Notes

**New files to create:**
- `backend/services/metrics_service.py`
- `backend/tests/test_metrics_service.py`
- `backend/db/migrations/versions/YYYYMMDD_XXX_add_accuracy_metrics_table.py`

**Files to modify:**
- `backend/core/models.py` - Add AccuracyMetric model
- `backend/services/__init__.py` - Export MetricsService

### Technical Requirements from Architecture

[Source: _bmad-output/project-context.md]

- **Async/Await:** ALL database operations MUST use `async`/`await`
- **SQLAlchemy:** Use `AsyncSession`, `select()` with `await session.execute()`
- **Type hints:** ALL functions MUST have complete type hints
- **Tests:** TDD approach, >80% coverage, pytest-asyncio for async tests
- **Decimal:** Use Decimal for all metric fields (precision)
- **scipy:** Use `scipy.stats.t.ppf()` for t-distribution confidence intervals

### Previous Story Intelligence (3-2)

From story 3-2 completion notes:
- DeviationService patterns established
- Deviation table stores: timestamp, site_id, model_id, parameter_id, horizon, deviation
- Sign convention: `deviation = observed - forecast` (positive = underestimate)
- Timezone normalization helper available: `normalize_datetime_for_db`
- Input validation pattern with ValueError for invalid parameters
- Batch processing for performance
- 514 tests currently passing, 95.24% coverage achieved

### SQL Aggregation Queries

**Calculate metrics from deviations:**
```python
from sqlalchemy import func, select
from core.models import Deviation

# Query to calculate all metrics
query = (
    select(
        func.avg(func.abs(Deviation.deviation)).label('mae'),
        func.avg(Deviation.deviation).label('bias'),
        func.stddev(Deviation.deviation).label('std_dev'),
        func.count().label('sample_size'),
        func.min(Deviation.deviation).label('min_deviation'),
        func.max(Deviation.deviation).label('max_deviation'),
    )
    .where(
        Deviation.model_id == model_id,
        Deviation.site_id == site_id,
        Deviation.parameter_id == parameter_id,
        Deviation.horizon == horizon,
    )
)
```

### Edge Cases to Handle

1. **No deviations:** Raise ValueError with descriptive message
2. **Single sample:** std_dev = 0, CI = (bias, bias)
3. **All identical deviations:** std_dev = 0, CI = (bias, bias)
4. **Large sample size:** Ensure Decimal precision for very small metrics
5. **Negative MAE:** Should never happen (absolute value), add assertion

### Test Data Setup

```python
# Example test fixture - create sample deviations
@pytest_asyncio.fixture
async def sample_deviations(test_db: AsyncSession, sample_site, sample_model, wind_speed_param):
    """Create sample deviations for metrics testing.

    Creates 5 deviations: [2.0, -1.0, 3.0, -2.0, 1.0]
    Expected MAE = 1.8
    Expected bias = 0.6
    """
    from datetime import timedelta

    base_time = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
    deviation_values = [Decimal("2.0"), Decimal("-1.0"), Decimal("3.0"), Decimal("-2.0"), Decimal("1.0")]

    for i, dev_value in enumerate(deviation_values):
        deviation = Deviation(
            timestamp=base_time + timedelta(hours=i),
            site_id=sample_site.id,
            model_id=sample_model.id,
            parameter_id=wind_speed_param.id,
            horizon=12,
            forecast_value=Decimal("20.0"),
            observed_value=Decimal("20.0") + dev_value,
            deviation=dev_value,
        )
        test_db.add(deviation)

    await test_db.commit()
```

### scipy Dependency

**IMPORTANT:** Ensure scipy is installed for confidence interval calculations.

```python
# Check if scipy is available
try:
    from scipy import stats
except ImportError:
    raise ImportError("scipy is required for confidence interval calculations. Install with: pip install scipy")
```

### References

- [Epic 3 Definition: _bmad-output/planning-artifacts/epics.md#Story-3.3]
- [Architecture: _bmad-output/planning-artifacts/architecture-meteo-score-2026-01-10.md]
- [Project Context: _bmad-output/project-context.md]
- [Existing Models: backend/core/models.py]
- [Deviation Model: backend/core/models.py#Deviation]
- [Previous Story 3-2: _bmad-output/implementation-artifacts/3-2-deviation-calculation-logic.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No blocking issues encountered

### Completion Notes List

- Implemented TDD approach: wrote 25 comprehensive tests BEFORE implementation
- Created Alembic migration `004` for `accuracy_metrics` table
- Added AccuracyMetric model to core/models.py with UNIQUE constraint
- Implemented MetricsService with:
  - `calculate_accuracy_metrics()`: SQL aggregation for MAE, bias, std_dev, min/max
  - `calculate_confidence_interval()`: scipy t-distribution for 95% CI
  - `determine_confidence_level()`: threshold-based classification (insufficient/preliminary/validated)
  - `save_metrics()`: upsert logic with PostgreSQL ON CONFLICT and SQLite fallback
  - `_calculate_std_dev()`: sample standard deviation with Bessel's correction
- Added AccuracyMetrics dataclass for structured return values
- Added timezone normalization helper usage for SQLite test compatibility
- Input validation with ValueError for invalid parameters
- All acceptance criteria verified:
  - AC1: MAE calculation (mean of absolute deviations)
  - AC2: Bias calculation (positive = underestimate, negative = overestimate)
  - AC3: 95% CI using scipy.stats.t.ppf
  - AC4: Standard deviation with Bessel's correction
  - AC5: Sample size tracking
  - AC6: Confidence levels (insufficient <30, preliminary 30-89, validated >=90)
  - AC7: Min/max deviation tracking
  - AC8: Persistence with upsert (UNIQUE constraint)
  - AC9: 94% coverage for metrics_service.py (exceeds 80% requirement)
- Full test suite: 506 tests pass (481 existing + 25 new)

### File List

**New Files:**
- backend/services/metrics_service.py
- backend/tests/test_metrics_service.py
- backend/db/migrations/versions/20260115_0400_004_add_accuracy_metrics_table.py

**Modified Files:**
- backend/core/models.py (added AccuracyMetric model)
- backend/services/__init__.py (exported MetricsService, AccuracyMetrics)
- backend/tests/conftest.py (added accuracy_metrics cleanup)

## Senior Developer Review

### Review Date
2026-01-15

### Issues Found and Fixed

| ID | Severity | Issue | Fix Applied |
|----|----------|-------|-------------|
| M1 | MEDIUM | Missing horizon validation | Added `if horizon < 0` check in metrics_service.py:93-94 |
| M2 | MEDIUM | Missing test for invalid parameter_id | Added test_invalid_parameter_id_raises_value_error |
| M3 | MEDIUM | Unused import `math` in test file | Removed unused import |
| M4 | MEDIUM | PostgreSQL upsert path untested | Added test_save_metrics_postgresql_path with mocked dialect |

### Tests Added During Review

- `test_invalid_parameter_id_raises_value_error`: Validates parameter_id input validation
- `test_invalid_horizon_raises_value_error`: Validates horizon input validation
- `test_save_metrics_postgresql_path`: Tests PostgreSQL ON CONFLICT upsert path with mocked dialect

### Final Test Results

- **28 metrics service tests pass** (was 25, +3 new)
- **95%+ coverage for metrics_service.py** (exceeds 80% requirement)

## Change Log

- 2026-01-15: Story created by SM agent with comprehensive developer context
- 2026-01-15: Implementation complete - 25 tests pass, 94% coverage for metrics_service.py
- 2026-01-15: Code review complete - 4 MEDIUM issues fixed, 3 tests added
