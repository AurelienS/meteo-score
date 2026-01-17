# Story 5.1: Backend Admin API with Basic Auth

Status: done

## Story

As an admin,
I want protected API endpoints for scheduler control and collection history,
So that only I can access sensitive system information and trigger collections.

## Acceptance Criteria

1. **AC1: Basic Auth Middleware** - All /api/admin/* routes protected with HTTP Basic Auth
2. **AC2: Environment Credentials** - Admin credentials read from ADMIN_USERNAME and ADMIN_PASSWORD env vars
3. **AC3: Extended Status Endpoint** - GET /api/admin/scheduler/status returns scheduler status + last 10 executions per job
4. **AC4: Jobs Endpoint** - GET /api/admin/scheduler/jobs returns scheduled jobs with next run times
5. **AC5: Scheduler Toggle** - POST /api/admin/scheduler/toggle starts/stops scheduler at runtime
6. **AC6: Manual Forecast Trigger** - POST /api/admin/collect/forecasts triggers immediate forecast collection
7. **AC7: Manual Observation Trigger** - POST /api/admin/collect/observations triggers immediate observation collection
8. **AC8: Execution History** - Track last N executions (not just last one) with timestamps, status, record counts
9. **AC9: Unit Tests** - Tests for auth middleware and all endpoints

## Tasks / Subtasks

- [x] Task 1: Create Basic Auth dependency (AC: 1, 2)
  - [x] 1.1: Create backend/api/dependencies/auth.py with HTTPBasic dependency
  - [x] 1.2: Read ADMIN_USERNAME/ADMIN_PASSWORD from environment (with defaults for dev)
  - [x] 1.3: Return 401 Unauthorized if credentials don't match
  - [x] 1.4: Add ADMIN_USERNAME/ADMIN_PASSWORD to docker-compose.yml environment

- [x] Task 2: Extend execution history tracking (AC: 8)
  - [x] 2.1: Modify scheduler/jobs.py to keep list of last 10 executions per job (not just last one)
  - [x] 2.2: Add get_execution_history(job_id, limit=10) function
  - [x] 2.3: Include error details in execution records when status is "partial" or "failed"

- [x] Task 3: Create admin router with endpoints (AC: 3, 4, 5, 6, 7)
  - [x] 3.1: Create backend/api/routes/admin.py with APIRouter prefix="/admin"
  - [x] 3.2: Add Basic Auth dependency to router
  - [x] 3.3: GET /scheduler/status - return running state + execution history
  - [x] 3.4: GET /scheduler/jobs - return job list with next run times (reuse existing logic)
  - [x] 3.5: POST /scheduler/toggle - call start_scheduler() or stop_scheduler() based on current state
  - [x] 3.6: POST /collect/forecasts - call collect_all_forecasts() directly, return results
  - [x] 3.7: POST /collect/observations - call collect_all_observations() directly, return results
  - [x] 3.8: Register admin router in backend/api/routes/__init__.py

- [x] Task 4: Write unit tests (AC: 9)
  - [x] 4.1: Test auth middleware rejects missing/invalid credentials
  - [x] 4.2: Test auth middleware accepts valid credentials
  - [x] 4.3: Test scheduler status endpoint returns expected structure
  - [x] 4.4: Test scheduler toggle endpoint starts/stops scheduler
  - [x] 4.5: Test manual collection endpoints trigger jobs

- [x] Task 5: Verification
  - [x] 5.1: Run tests - all pass
  - [x] 5.2: Manual test with curl - verify 401 without auth, 200 with auth
  - [x] 5.3: Verify docker-compose.yml has env vars

## Dev Notes

### Existing Infrastructure

**Already exists:**

1. **scheduler/scheduler.py**:
   - `get_scheduler()` - returns AsyncIOScheduler singleton
   - `start_scheduler()` / `stop_scheduler()` - lifecycle functions
   - `scheduler.running` - boolean for status

2. **scheduler/jobs.py**:
   - `collect_all_forecasts()` / `collect_all_observations()` - can be called directly
   - `_job_executions` dict - tracks last execution per job (needs extension)
   - `get_last_execution(job_id)` - returns last execution only

3. **api/routes/scheduler.py**:
   - Existing `/api/scheduler/status` and `/api/scheduler/jobs` endpoints (public)
   - Can reuse response schemas: SchedulerStatusResponse, ScheduledJobInfo, etc.

### Implementation Approach

1. Keep existing public scheduler routes as-is (backward compatible)
2. Create new `/api/admin/*` routes with auth protection
3. Extend execution tracking to keep history list instead of single record
4. Use FastAPI's HTTPBasic security dependency

### Code Patterns

**Basic Auth Dependency:**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import os

security = HTTPBasic()

def get_admin_credentials():
    return (
        os.getenv("ADMIN_USERNAME", "admin"),
        os.getenv("ADMIN_PASSWORD", "changeme"),
    )

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    username, password = get_admin_credentials()
    is_username_correct = secrets.compare_digest(credentials.username, username)
    is_password_correct = secrets.compare_digest(credentials.password, password)
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
```

**Admin Router:**
```python
from fastapi import APIRouter, Depends
from api.dependencies.auth import verify_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(verify_admin)])
```

### Environment Variables

Add to docker-compose.yml backend service:
```yaml
environment:
  ADMIN_USERNAME: ${ADMIN_USERNAME:-admin}
  ADMIN_PASSWORD: ${ADMIN_PASSWORD}  # Required, no default in prod
```

### API Response Schemas

```python
class ExecutionRecord(BaseModel):
    start_time: str
    end_time: str
    duration_seconds: float
    status: str  # "success", "partial", "failed"
    records_collected: int
    error: Optional[str] = None

class AdminSchedulerStatusResponse(BaseModel):
    running: bool
    forecast_history: list[ExecutionRecord]
    observation_history: list[ExecutionRecord]

class ToggleResponse(BaseModel):
    running: bool
    message: str

class CollectionResponse(BaseModel):
    status: str
    records_collected: int
    duration_seconds: float
```

## Change Log

- 2026-01-17: Story created for Epic 5 Admin Dashboard
- 2026-01-17: Implementation completed - all tasks done, 20 tests pass

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - implementation proceeded without issues.

### Completion Notes List

1. **Basic Auth Dependency**: Created `backend/api/dependencies/auth.py` with HTTPBasic security using constant-time comparison via `secrets.compare_digest()` to prevent timing attacks. Credentials read from `ADMIN_USERNAME` and `ADMIN_PASSWORD` environment variables with dev defaults.

2. **Execution History Tracking**: Modified `scheduler/jobs.py` to store list of last 10 executions per job (not just last one). Added `_add_execution_record()` helper and `get_execution_history(job_id, limit)` function. Error details now tracked in records.

3. **Admin Router**: Created `backend/api/routes/admin.py` with 5 endpoints:
   - `GET /api/admin/scheduler/status` - Running state + execution history
   - `GET /api/admin/scheduler/jobs` - Scheduled jobs with next run times
   - `POST /api/admin/scheduler/toggle` - Start/stop scheduler
   - `POST /api/admin/collect/forecasts` - Trigger manual forecast collection
   - `POST /api/admin/collect/observations` - Trigger manual observation collection

4. **Docker Compose**: Added `ADMIN_USERNAME` and `ADMIN_PASSWORD` environment variables to backend service.

5. **Unit Tests**: 20 tests covering auth middleware, scheduler endpoints, toggle functionality, and execution history tracking. All tests pass.

6. **Test Results**:
   - Admin API Tests: 20 passed
   - Full Test Suite: 621 passed
   - Coverage: 96.32%

### File List

- **backend/api/dependencies/__init__.py** - CREATED: Empty init file
- **backend/api/dependencies/auth.py** - CREATED: Basic Auth dependency with HTTPBasic + rate limiting
- **backend/api/routes/admin.py** - CREATED: Admin router with 5 protected endpoints
- **backend/api/routes/__init__.py** - MODIFIED: Added admin router import and registration
- **backend/scheduler/jobs.py** - MODIFIED: Extended execution tracking with history list
- **backend/tests/test_admin_api.py** - CREATED: 21 unit tests for admin API
- **docker-compose.yml** - MODIFIED: Added ADMIN_USERNAME/ADMIN_PASSWORD env vars

## Senior Developer Review

### Review Date
2026-01-17

### Issues Found and Fixed

#### HIGH Issues (2)

**H1: Default password in production**
- Location: docker-compose.yml:38
- Problem: ADMIN_PASSWORD had a default "changeme" value, insecure for production
- Fix: Changed to `${ADMIN_PASSWORD:?ADMIN_PASSWORD must be set}` to require explicit value

**H2: No rate limiting on admin endpoints**
- Location: backend/api/dependencies/auth.py
- Problem: Admin endpoints had no protection against brute-force attacks
- Fix: Added dedicated rate limiter (5 failed attempts per minute) with IP tracking

#### MEDIUM Issues (2)

**M1: Exceptions silently swallowed in collection endpoints**
- Location: backend/api/routes/admin.py:187, 231
- Problem: Exception tracebacks were lost when collection failed
- Fix: Added `logger.exception()` call to log full traceback before returning error

**M2: Dead code in test**
- Location: backend/tests/test_admin_api.py:318-327
- Problem: `side_effect` function defined but never used in mock
- Fix: Removed unused code, simplified test

### Post-Review Verification
- All 622 tests pass
- Coverage: 96.32%
- New test added for rate limiting verification

