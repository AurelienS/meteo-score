# Story 5.2: Frontend Admin Dashboard Page

Status: done

## Story

As an admin,
I want a web interface to view collection status and control the scheduler,
So that I can monitor and manage the system without using CLI tools.

## Acceptance Criteria

1. **AC1: Admin Route** - /admin route exists in Solid.js router
2. **AC2: Basic Auth Prompt** - Browser shows native Basic Auth dialog when accessing /admin
3. **AC3: Scheduler Status Display** - Page shows scheduler running/stopped status
4. **AC4: Next Run Times** - Display next scheduled collection times for each job
5. **AC5: Execution History** - Show last 10 executions per job type with status, duration, records
6. **AC6: Manual Trigger Buttons** - Buttons to trigger forecast and observation collection manually
7. **AC7: Scheduler Toggle** - Switch/button to start/stop the scheduler
8. **AC8: Loading States** - Show loading indicators during API calls
9. **AC9: Error Handling** - Display error messages when API calls fail
10. **AC10: Auto-refresh** - Status refreshes automatically every 30 seconds

## Tasks / Subtasks

- [x] Task 1: Create Admin page component (AC: 1, 2)
  - [x] 1.1: Add /admin route to App.tsx router
  - [x] 1.2: Create src/pages/Admin.tsx component
  - [x] 1.3: Verify Basic Auth prompt appears (handled by browser natively)

- [x] Task 2: Implement scheduler status section (AC: 3, 4)
  - [x] 2.1: Create API client functions in lib/api.ts for admin endpoints
  - [x] 2.2: Display scheduler running/stopped status with indicator
  - [x] 2.3: Display next run times for scheduled jobs

- [x] Task 3: Implement execution history section (AC: 5)
  - [x] 3.1: Create ExecutionHistoryTable component
  - [x] 3.2: Display last 10 executions for forecasts
  - [x] 3.3: Display last 10 executions for observations
  - [x] 3.4: Show status badges (success/partial/failed)
  - [x] 3.5: Show duration and record counts

- [x] Task 4: Implement control buttons (AC: 6, 7, 8)
  - [x] 4.1: Add "Trigger Forecasts" button with loading state
  - [x] 4.2: Add "Trigger Observations" button with loading state
  - [x] 4.3: Add scheduler toggle button/switch
  - [x] 4.4: Refresh status after each action

- [x] Task 5: Implement auto-refresh and error handling (AC: 9, 10)
  - [x] 5.1: Add 30-second auto-refresh interval
  - [x] 5.2: Display error messages in alert/toast
  - [x] 5.3: Handle 401/429 errors appropriately

- [x] Task 6: Verification
  - [x] 6.1: TypeScript compiles without errors
  - [x] 6.2: Page renders correctly with mock data
  - [x] 6.3: All interactive elements work

## Dev Notes

### API Endpoints (from Story 5-1)

All endpoints require Basic Auth header.

```typescript
// GET /api/admin/scheduler/status
interface AdminSchedulerStatusResponse {
  running: boolean;
  forecastHistory: ExecutionRecord[];
  observationHistory: ExecutionRecord[];
}

interface ExecutionRecord {
  startTime: string;
  endTime: string;
  durationSeconds: number;
  status: 'success' | 'partial' | 'failed';
  recordsCollected: number;
  errors?: string[];
}

// GET /api/admin/scheduler/jobs
interface SchedulerJobsResponse {
  jobs: ScheduledJobInfo[];
}

interface ScheduledJobInfo {
  id: string;
  name: string;
  nextRunTime: string | null;
  trigger: string;
}

// POST /api/admin/scheduler/toggle
interface ToggleResponse {
  running: boolean;
  message: string;
}

// POST /api/admin/collect/forecasts
// POST /api/admin/collect/observations
interface CollectionResponse {
  status: string;
  recordsCollected: number;
  durationSeconds: number;
  errors?: string[];
}
```

### Basic Auth with Fetch

Browser handles Basic Auth natively when server returns 401 with WWW-Authenticate: Basic header.

```typescript
// No special handling needed - browser will prompt automatically
const response = await fetch('/api/admin/scheduler/status');
// If 401, browser shows auth dialog
```

### Solid.js Patterns (from project-context.md)

- Use `createSignal()` for state
- Use `createEffect()` for side effects (auto-refresh)
- Use `onMount()` for initial data fetch
- Use `<Show>` and `<For>` for conditional/list rendering
- DO NOT destructure props

### UI Structure

```
Admin Dashboard
├── Header: "Admin Dashboard" + Scheduler Status Badge
├── Scheduler Info Section
│   ├── Running Status (green/red indicator)
│   ├── Next Run Times table
│   └── Toggle Button
├── Manual Collection Section
│   ├── Trigger Forecasts Button
│   └── Trigger Observations Button
├── Execution History Section
│   ├── Forecasts History Table
│   └── Observations History Table
└── Error Display (if any)
```

### Tailwind Classes Reference

- Status badges: `bg-green-100 text-green-800` (success), `bg-red-100 text-red-800` (failed)
- Buttons: `bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded`
- Tables: `min-w-full divide-y divide-gray-200`
- Loading: `animate-spin` on spinner icon

## Dev Agent Record

### File List

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/pages/Admin.tsx` | Created | Admin dashboard page with scheduler status, execution history, control buttons |
| `frontend/src/lib/types.ts` | Modified | Added admin API types (ExecutionRecord, AdminSchedulerStatusResponse, etc.) |
| `frontend/src/lib/api.ts` | Modified | Added admin API functions (fetchAdminSchedulerStatus, toggleScheduler, etc.) |
| `frontend/src/App.tsx` | Modified | Added /admin route to router |

### Implementation Notes

- Used Solid.js patterns: createSignal, createEffect, onMount, onCleanup, Show, For
- Auto-refresh every 30 seconds with pause during active operations
- Confirmation dialog for stopping scheduler (destructive action)
- Proper error handling for ApiRequestError, NetworkError, TimeoutError
- Accessibility: aria-labels on spinner, role="status" on status indicator
- Execution history shows errors when present (expandable rows)

## Change Log

- 2026-01-17: Story created for Epic 5 Admin Dashboard
- 2026-01-17: Implementation complete - Admin.tsx page with scheduler status, execution history, control buttons, auto-refresh
- 2026-01-17: Code review fixes - Added NetworkError/TimeoutError handling, error display in history, confirmation dialog, accessibility improvements
