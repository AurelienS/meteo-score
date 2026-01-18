# Story 6.8: Fix Data Collection Pipeline

Status: done

## Story

As a **system administrator**,
I want **the data collection pipeline to actually persist data to the database and provide visibility into collected data**,
So that **forecasts and observations are stored, can be analyzed, and I can verify data correctness**.

## Problem Statement

Critical bugs discovered in production:
1. **Data not persisted**: Collectors return data but never save to database
2. **Execution history lost on restart**: Stored in-memory dict, resets on deployment
3. **Beacon IDs not used**: Hardcoded defaults instead of configured beacon IDs
4. **No data visibility**: Cannot verify if collected data is correct

## Acceptance Criteria

1. **AC1**: Given forecasts are collected, when the collection job completes, then forecast records are persisted to the Forecast table
2. **AC2**: Given observations are collected, when the collection job completes, then observation records are persisted to the Observation table
3. **AC3**: Given a collection job runs, when I view admin dashboard, then I see execution history that persists across deployments
4. **AC4**: Given I am in the admin dashboard, when I view collection status, then I can see a "sneak peek" of recent collected data (last 5 records per source)
5. **AC5**: Given beacon IDs are configured for a site, when observation collection runs, then it uses the configured beacon IDs (not hardcoded defaults)
6. **AC6**: Given I need to seed the database, when I run the CLI command, then seed data is inserted (only if tables are empty)
7. **AC7**: Given I trigger manual collection from admin, when it completes, then I see the actual persisted record count (not just returned count)

## Tasks / Subtasks

- [x] Task 1: Add data persistence to collectors (AC: 1, 2, 7)
  - [x] Create `storage_service.py` with `save_forecasts()` and `save_observations()` functions
  - [x] Modify `collect_all_forecasts()` to call storage after collection
  - [x] Modify `collect_all_observations()` to call storage after collection
  - [x] Handle duplicates gracefully (upsert via INSERT ... ON CONFLICT DO NOTHING)
  - [x] Return actual persisted count in job result

- [x] Task 2: Persist execution history to database (AC: 3)
  - [x] Create `ExecutionLog` model with job_id, start_time, end_time, status, records_collected, errors
  - [x] Create alembic migration for execution_logs table (006)
  - [x] Update to write execution log to database via `save_execution_log()`
  - [x] Update `get_execution_history()` to read from database
  - [x] Records are now persistent across restarts

- [x] Task 3: Fix beacon ID mapping (AC: 5)
  - [x] Update `get_site_configs()` to load from database (async version)
  - [x] Add beacon ID columns to Site model (primary + backup for ROMMA and FFVL)
  - [x] Add beacon IDs to seed data
  - [x] Implement backup beacon fallback logic in observation collection
  - [x] Pass beacon_id to ROMMA and FFVL collectors

- [x] Task 4: Add admin data preview / sneak peek (AC: 4)
  - [x] Create API endpoint `GET /api/admin/data-preview` returning recent records
  - [x] Return last 5 forecasts per model with timestamp, site, parameter, value
  - [x] Return last 5 observations per source with timestamp, site, parameter, value
  - [x] Add frontend component to display data preview in admin dashboard
  - [x] Add i18n translations for preview labels

- [x] Task 5: Add admin total stats (AC: 4)
  - [x] Create API endpoint `GET /api/admin/stats` with total counts
  - [x] Return: total_forecasts, total_observations, total_deviations, total_pairs, total_sites
  - [x] Add date range for counts (all time, last 7 days, last 30 days)
  - [x] Display stats prominently in admin dashboard

- [x] Task 6: Create CLI for manual operations (AC: 6)
  - [x] Create `backend/cli.py` with argparse
  - [x] Add `seed` command that runs db.seed (with --force flag to override non-empty check)
  - [x] Add `migrate` command that runs alembic upgrade head
  - [x] Add `collect-forecasts` command for manual trigger
  - [x] Add `collect-observations` command for manual trigger
  - [x] Add `stats` command to show DB statistics
  - [x] Document CLI usage in README

- [x] Task 7: Verify and test (AC: 1-7)
  - [x] Test data persistence with mock collectors (test_storage_service.py)
  - [x] Test execution history persistence (test_storage_service.py)
  - [x] Test admin preview and stats endpoints (test_admin_api.py)
  - [x] Test CLI commands (test_cli.py)
  - [x] Test scheduler jobs with backup beacon logic (test_scheduler_jobs.py)

## Dev Notes

### Current Code Issues

**scheduler/jobs.py:108-201** - `collect_all_forecasts()`:
```python
# Returns data but never saves it!
all_data.extend(data)  # Line 140
...
return all_data  # Line 201 - Data is lost!
```

**scheduler/jobs.py:28** - In-memory history:
```python
_job_executions: dict[str, list[dict[str, Any]]] = {}  # Resets on restart
```

**scheduler/jobs.py:77-105** - Hardcoded config:
```python
"romma_station_id": "PASSY",  # String, not integer!
"ffvl_beacon_id": "123",  # Not actually used
```

### Storage Service Design

```python
# backend/services/storage.py
async def save_forecasts(db: AsyncSession, forecasts: list[ForecastData]) -> int:
    """Save forecasts to database, returning count of new records."""
    saved = 0
    for f in forecasts:
        # Convert ForecastData to Forecast model
        # Use INSERT ... ON CONFLICT DO NOTHING for idempotency
        ...
    return saved
```

### ExecutionLog Model

```python
class ExecutionLog(Base):
    __tablename__ = "execution_log"

    id: int (PK)
    job_id: str  # "collect_forecasts" or "collect_observations"
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    status: str  # "success", "partial", "failed"
    records_collected: int
    records_persisted: int
    errors: JSON (nullable)
    created_at: datetime
```

### Admin Preview Response

```json
{
  "forecasts": {
    "AROME": [
      {"timestamp": "2026-01-17T12:00:00Z", "site": "Passy", "parameter": "Wind Speed", "value": 15.2}
    ],
    "Meteo-Parapente": [...]
  },
  "observations": {
    "ROMMA": [...],
    "FFVL": [...]
  },
  "totals": {
    "forecasts": 1234,
    "observations": 567,
    "deviations": 890
  }
}
```

### CLI Commands

```bash
# In Docker container
docker-compose exec backend python -m cli seed          # Run seed (only if empty)
docker-compose exec backend python -m cli seed --force  # Force seed
docker-compose exec backend python -m cli migrate       # Run migrations
docker-compose exec backend python -m cli collect-forecasts   # Manual trigger
docker-compose exec backend python -m cli collect-observations
docker-compose exec backend python -m cli stats         # Show DB stats
```

### Beacon ID Research Needed

For Passy Plaine Joux, need to find:
- ROMMA beacon ID (integer) - check https://www.romma.fr/
- FFVL beacon ID (integer) - check https://www.balisemeteo.com/

## Dev Agent Record

### File List

**New Files Created:**
- `backend/services/storage_service.py` - Data persistence service with save_forecasts, save_observations, save_execution_log
- `backend/cli.py` - CLI for manual operations (seed, migrate, stats, collect)
- `backend/db/migrations/versions/20260117_0100_006_add_execution_logs_table.py` - Migration for execution_logs and beacon IDs
- `backend/tests/test_storage_service.py` - Tests for storage service
- `backend/tests/test_cli.py` - Tests for CLI commands
- `backend/tests/test_scheduler_jobs.py` - Tests for scheduler jobs

**Modified Files:**
- `backend/core/models.py` - Added ExecutionLog model, beacon ID columns to Site
- `backend/scheduler/jobs.py` - Refactored to persist data, load sites from DB, backup beacon fallback
- `backend/api/routes/admin.py` - Added stats and data-preview endpoints with days filter
- `backend/services/storage_service.py` - Added days filter to get_data_stats()
- `backend/db/seed.py` - Added beacon IDs to seed data
- `backend/tests/conftest.py` - Added execution_logs cleanup
- `backend/tests/test_admin_api.py` - Updated tests for new endpoints
- `frontend/src/pages/Admin.tsx` - Added DataStatsCard and DataPreviewTable components
- `frontend/src/lib/api.ts` - Added fetchAdminStats and fetchAdminDataPreview functions
- `frontend/src/lib/types.ts` - Added DataStatsResponse, ForecastPreviewRecord, ObservationPreviewRecord types
- `frontend/src/locales/en.json` - Added admin dashboard translations
- `frontend/src/locales/fr.json` - Added admin dashboard translations (French)
- `README.md` - Documented CLI usage

### Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-18 | Initial implementation of data persistence pipeline | Claude |
| 2026-01-18 | Code review fixes: error handling, logging, test improvements | Claude |
| 2026-01-18 | Added frontend data preview & stats components with date range filter | Claude |
| 2026-01-18 | Added i18n translations (EN/FR) for admin dashboard | Claude |
| 2026-01-18 | Documented CLI usage in README | Claude |

## References

- [Source: backend/scheduler/jobs.py]
- [Source: backend/collectors/romma.py]
- [Source: backend/collectors/ffvl.py]
- [Source: backend/services/matching_service.py]
