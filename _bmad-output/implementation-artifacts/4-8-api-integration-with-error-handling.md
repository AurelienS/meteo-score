# Story 4.8: API Integration with Error Handling

Status: done

## Story

As a developer,
I want to fetch data from the FastAPI backend with proper error handling,
So that users see helpful messages when data is unavailable or errors occur.

## Acceptance Criteria

1. **AC1: Retry Functionality** - Error messages include a retry button that refetches data
2. **AC2: Network Error Handling** - Handle fetch failures (network offline, DNS errors, CORS)
3. **AC3: Request Timeout** - API requests timeout after 30 seconds with user-friendly message
4. **AC4: TypeScript** - No compilation errors

## Tasks / Subtasks

- [x] Task 1: Add retry functionality to error displays (AC: 1)
  - [x] 1.1: Add refetch callback to loadAccuracyData function
  - [x] 1.2: Add retry button to accuracy error display in Home.tsx
  - [x] 1.3: Add retry button to time series error display
  - [x] 1.4: Style retry buttons consistently

- [x] Task 2: Handle network errors (AC: 2)
  - [x] 2.1: Wrap fetch in try-catch in api.ts
  - [x] 2.2: Create NetworkError class for connection failures
  - [x] 2.3: Differentiate network vs HTTP errors in UI messaging
  - [x] 2.4: Test offline behavior (DevTools Network tab)

- [x] Task 3: Add request timeout (AC: 3)
  - [x] 3.1: Create fetchWithTimeout wrapper using AbortController
  - [x] 3.2: Set default timeout to 30 seconds
  - [x] 3.3: Create TimeoutError class
  - [x] 3.4: Show timeout-specific message in UI

- [x] Task 4: Verification (AC: 4)
  - [x] 4.1: Run `npm run type-check` - no errors
  - [x] 4.2: Run `npm run lint` - no new warnings
  - [x] 4.3: Manual test error scenarios

## Dev Notes

### Current Implementation State

**ALREADY IMPLEMENTED (DO NOT RECREATE):**

1. **API Service** (`frontend/src/lib/api.ts`):
   - `ApiRequestError` class with statusCode and errorType
   - `fetchApi<T>` generic wrapper with error handling
   - `fetchSites()`, `fetchParameters()`
   - `fetchSiteAccuracy()` with parameter validation
   - `fetchAccuracyTimeSeries()` with granularity validation

2. **Types** (`frontend/src/lib/types.ts`):
   - All types: Site, Parameter, ModelAccuracyMetrics, SiteAccuracyResponse, etc.
   - ApiError interface for error responses

3. **Home Page** (`frontend/src/pages/Home.tsx`):
   - Loading states: `isLoadingSites`, `isLoadingParameters`, `isLoadingAccuracy`, `isLoadingTimeSeries`
   - Error states: `error`, `accuracyError`, `timeSeriesError`
   - Error display UI: Red/orange alert boxes with `<Show when={error()}>`
   - Loading skeletons with animate-pulse

### Gaps to Fill

1. **Retry Functionality**: Current error displays have no way to retry. Add buttons.

2. **Network Errors**: Current `fetchApi` doesn't handle network failures (TypeError from fetch). Need to catch and wrap.

3. **Request Timeout**: No timeout - requests hang indefinitely. Use AbortController.

### Implementation Patterns

**Retry Button Pattern:**
```tsx
// In Home.tsx error display
<button
  class="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors min-h-[44px]"
  onClick={() => loadAccuracyData(selectedSiteId(), selectedParameterId(), selectedHorizon())}
>
  Retry
</button>
```

**Network Error Handling Pattern:**
```typescript
// In api.ts - wrap existing fetchApi
export class NetworkError extends Error {
  constructor(message: string = 'Network error - please check your connection') {
    super(message);
    this.name = 'NetworkError';
  }
}

export async function fetchApi<T>(endpoint: string): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  let response: Response;
  try {
    response = await fetch(url);
  } catch (error) {
    // Network failure (offline, DNS, CORS, etc.)
    throw new NetworkError();
  }

  // ... rest of existing error handling
}
```

**Timeout Pattern with AbortController:**
```typescript
const DEFAULT_TIMEOUT_MS = 30000;

export class TimeoutError extends Error {
  constructor(message: string = 'Request timed out - please try again') {
    super(message);
    this.name = 'TimeoutError';
  }
}

async function fetchWithTimeout(url: string, timeoutMs: number = DEFAULT_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new TimeoutError();
    }
    throw new NetworkError();
  }
}
```

**Error Type Checking in UI:**
```tsx
import { ApiRequestError, NetworkError, TimeoutError } from '../lib/api';

const getErrorMessage = (err: Error): string => {
  if (err instanceof TimeoutError) {
    return 'Request timed out. The server may be busy.';
  }
  if (err instanceof NetworkError) {
    return 'Unable to connect. Check your internet connection.';
  }
  if (err instanceof ApiRequestError) {
    return err.message;
  }
  return 'An unexpected error occurred.';
};
```

### File Structure

```
frontend/src/
├── lib/
│   ├── api.ts         # MODIFY: Add NetworkError, TimeoutError, fetchWithTimeout
│   └── types.ts       # NO CHANGES
├── pages/
│   └── Home.tsx       # MODIFY: Add retry buttons to error displays
└── components/
    └── ...            # NO CHANGES
```

### Constants

```typescript
/** Default request timeout in milliseconds (30 seconds) */
const DEFAULT_TIMEOUT_MS = 30000;
```

### Previous Story Learnings

From Story 4-7 code review:
1. Use `min-h-[44px]` for touch-friendly buttons
2. Add focus states for accessibility: `focus:outline-none focus:ring-2 focus:ring-primary-500`
3. Use named constants for configuration values
4. Export new error classes for use in components

### Testing Scenarios

1. **Network offline**: Chrome DevTools → Network → Offline
2. **Slow network**: Network → Slow 3G
3. **Timeout**: Can simulate by adding delay in backend or using DevTools throttling
4. **404 error**: Use invalid site/parameter ID
5. **500 error**: Requires backend to return error

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-4.8]
- [Source: frontend/src/lib/api.ts - Existing API client]
- [Source: frontend/src/lib/types.ts - Type definitions]
- [Source: frontend/src/pages/Home.tsx - Current error handling]
- [Source: Story 4-7 Code Review - Accessibility learnings]
- [MDN AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)

## Change Log

- 2026-01-16: Story created with comprehensive context for dev agent
- 2026-01-16: Implementation completed, moved to review

## Dev Agent Record

### Implementation Summary

Successfully implemented enhanced API error handling with retry functionality, network error detection, and request timeout support.

### Files Modified

1. **frontend/src/lib/api.ts** - MODIFIED: Added NetworkError, TimeoutError classes, fetchWithTimeout with AbortController
2. **frontend/src/pages/Home.tsx** - MODIFIED: Added retry buttons to all error displays, retry handler functions

### Key Implementation Decisions

1. **Error Class Hierarchy**: Created distinct error classes (ApiRequestError, NetworkError, TimeoutError) for proper error differentiation in UI.

2. **AbortController for Timeout**: Used native AbortController API with 30-second default timeout. This is the modern, recommended approach for request cancellation.

3. **Retry Handlers**: Created separate retry functions for each data type (retryInitialLoad, retryAccuracyLoad, retryTimeSeriesLoad) rather than a generic retry to maintain type safety and proper state management.

4. **Accessibility**: All retry buttons have:
   - `min-h-[44px]` for touch targets
   - `focus:ring-2` for keyboard navigation
   - Proper color contrast (bg-red-600, bg-orange-600)

5. **Error Propagation**: Network and timeout errors propagate the user-friendly default message, while API errors preserve the server's error message for debugging.

### Verification Results

- **TypeScript**: Passes with no errors (`npm run type-check`)
- **ESLint**: No new warnings (existing false-positive in AccuracyTimeSeriesChart)

### Acceptance Criteria Status

| AC | Description | Status |
|----|-------------|--------|
| AC1 | Retry Functionality | PASS |
| AC2 | Network Error Handling | PASS |
| AC3 | Request Timeout | PASS |
| AC4 | TypeScript | PASS |

## Senior Developer Review (AI)

**Reviewer:** Claude | **Date:** 2026-01-16 | **Outcome:** APPROVED

### Issues Found and Fixed

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| M1 | MEDIUM | Duplicate code: `retryInitialLoad` duplicated `onMount` logic - extracted to shared `loadInitialData` function | FIXED |
| M2 | MEDIUM | Retry buttons missing `disabled` state during loading - added disabled prop and "Retrying..." text | FIXED |
| L1 | LOW | Error messages didn't leverage error type for context-specific guidance - added `getErrorMessage` helper | FIXED |
| L2 | LOW | No `aria-live` region for error messages - added `role="alert"` to all error displays | FIXED |

### Fixes Applied

1. **M1 - Extract Shared Function**: Created `loadInitialData()` function that handles loading sites and parameters, replacing duplicate code in `onMount` and `retryInitialLoad`.

2. **M2 - Disabled State**: Added `disabled={isLoading...()}` to all retry buttons with `disabled:opacity-50 disabled:cursor-not-allowed` styling. Button text changes to "Retrying..." during load.

3. **L1 - Error Type Messages**: Added `getErrorMessage(err)` helper function that returns context-specific messages:
   - TimeoutError: "Request timed out. The server may be busy - please try again later."
   - NetworkError: "Unable to connect. Please check your internet connection."
   - Other errors: Preserve original message

4. **L2 - Accessibility**: Added `role="alert"` to all three error display divs for screen reader announcements.

### Verification

- TypeScript: PASS (no errors)
- ESLint: No new warnings (existing false-positive in AccuracyTimeSeriesChart)
