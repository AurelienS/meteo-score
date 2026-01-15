# Story 3.4: TimescaleDB Continuous Aggregates

Status: done

## Story

As a developer,
I want to pre-compute rolling statistics using TimescaleDB continuous aggregates,
So that API queries return results instantly without scanning millions of deviation records.

## Acceptance Criteria

1. **AC1: Daily Aggregate** - Create `daily_accuracy_metrics` continuous aggregate with MAE, bias, std_dev, sample_size
2. **AC2: Weekly Aggregate** - Create `weekly_accuracy_metrics` continuous aggregate
3. **AC3: Monthly Aggregate** - Create `monthly_accuracy_metrics` continuous aggregate
4. **AC4: Refresh Policies** - Configure automatic refresh policies for each aggregate
5. **AC5: Query Performance** - Queries on aggregates return in <100ms vs scanning raw deviations
6. **AC6: Manual Refresh** - Provide utility function to manually refresh aggregates
7. **AC7: Test Coverage** - >80% coverage with integration tests

## Tasks / Subtasks

- [x] Task 1: Create TimescaleDB migration for continuous aggregates
  - [x] 1.1: Create migration file for daily_accuracy_metrics view
  - [x] 1.2: Create migration for weekly_accuracy_metrics view
  - [x] 1.3: Create migration for monthly_accuracy_metrics view
  - [x] 1.4: Add refresh policies for each aggregate

- [x] Task 2: Write TDD tests FIRST
  - [x] 2.1: Create `backend/tests/test_continuous_aggregates.py`
  - [x] 2.2: Test daily aggregate calculates correct MAE/bias
  - [x] 2.3: Test weekly aggregate groups correctly
  - [x] 2.4: Test monthly aggregate groups correctly
  - [x] 2.5: Test refresh policies are configured
  - [x] 2.6: Test manual refresh function works

- [x] Task 3: Implement AggregateService
  - [x] 3.1: Create `backend/services/aggregate_service.py`
  - [x] 3.2: Implement `refresh_daily_aggregate()` method
  - [x] 3.3: Implement `refresh_all_aggregates()` method
  - [x] 3.4: Implement `query_daily_metrics()` method
  - [x] 3.5: Implement `query_weekly_metrics()` method
  - [x] 3.6: Implement `query_monthly_metrics()` method

- [x] Task 4: Integration and verification
  - [x] 4.1: Run `pytest --cov` and verify >80%
  - [x] 4.2: Test with Docker PostgreSQL + TimescaleDB
  - [x] 4.3: Verify aggregates auto-refresh
  - [x] 4.4: Update services/__init__.py exports

## Dev Notes

### TimescaleDB Continuous Aggregates SQL

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

-- Refresh policy: update weekly
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

-- Refresh policy: update monthly
SELECT add_continuous_aggregate_policy('monthly_accuracy_metrics',
  start_offset => INTERVAL '3 months',
  end_offset => INTERVAL '1 day',
  schedule_interval => INTERVAL '30 days');
```

### Testing Considerations

**IMPORTANT:** Continuous aggregates are a TimescaleDB-specific feature. Tests must:
1. Use PostgreSQL + TimescaleDB (not SQLite)
2. Skip gracefully in SQLite test environment
3. Use Docker for integration tests

```python
import pytest

# Skip if not using PostgreSQL with TimescaleDB
@pytest.mark.skipif(
    "postgresql" not in os.environ.get("DATABASE_URL", ""),
    reason="Requires PostgreSQL with TimescaleDB"
)
class TestContinuousAggregates:
    ...
```

### Manual Refresh Function

```python
async def refresh_continuous_aggregate(
    db: AsyncSession,
    aggregate_name: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> None:
    """Manually refresh a continuous aggregate.

    Args:
        db: Database session
        aggregate_name: Name of the continuous aggregate view
        start_time: Optional start of refresh window
        end_time: Optional end of refresh window
    """
    if start_time and end_time:
        await db.execute(text(
            f"CALL refresh_continuous_aggregate('{aggregate_name}', "
            f"'{start_time.isoformat()}', '{end_time.isoformat()}')"
        ))
    else:
        await db.execute(text(
            f"CALL refresh_continuous_aggregate('{aggregate_name}', NULL, NULL)"
        ))
    await db.commit()
```

### Project Structure Notes

**New files to create:**
- `backend/services/aggregate_service.py`
- `backend/tests/test_continuous_aggregates.py`
- `backend/db/migrations/versions/YYYYMMDD_XXX_add_continuous_aggregates.py`

**Files to modify:**
- `backend/services/__init__.py` - Export AggregateService

### Previous Story Intelligence (3-3)

From story 3-3:
- MetricsService calculates on-demand metrics
- AccuracyMetric model stores calculated metrics
- Continuous aggregates complement on-demand calculation with pre-computed rollups

### References

- [Epic 3 Definition: _bmad-output/planning-artifacts/epics.md#Story-3.4]
- [TimescaleDB Continuous Aggregates Docs](https://docs.timescale.com/use-timescale/latest/continuous-aggregates/)
- [Previous Story 3-3: _bmad-output/implementation-artifacts/3-3-statistical-metrics-calculator-mae-bias.md]

## Change Log

- 2026-01-15: Story created for continuous aggregates implementation
