# Story 4.6: Data Freshness & Sample Size Indicators

Status: done

## Story

As a user,
I want to see when data was last updated and how much data is available,
So that I can judge the reliability and currency of the metrics.

## Acceptance Criteria

1. **AC1: DataFreshnessIndicator Component** - Display data freshness information
2. **AC2: Last Update Timestamp** - Show relative ("2 hours ago") and absolute date
3. **AC3: Sample Size Display** - Show total measurements count
4. **AC4: Date Range Display** - Show data coverage period (start to end)
5. **AC5: Confidence Level Indicator** - Visual indicator with status message
6. **AC6: Auto-refresh Relative Time** - Relative timestamps update every minute
7. **AC7: Integration** - Component integrated into Home page
8. **AC8: TypeScript** - No compilation errors, proper typing

## Tasks / Subtasks

- [x] Task 1: Create DataFreshnessIndicator component (AC: 1, 2, 3, 4, 5, 8)
  - [x] 1.1: Create `frontend/src/components/DataFreshnessIndicator.tsx`
  - [x] 1.2: Define props interface with proper types
  - [x] 1.3: Implement `formatDate()` helper for absolute dates
  - [x] 1.4: Implement `formatRelativeTime()` helper for relative times
  - [x] 1.5: Implement `getDaysOfData()` helper for date range calculation
  - [x] 1.6: Create 3-column responsive grid layout
  - [x] 1.7: Add confidence level indicator with icon and message

- [x] Task 2: Add auto-refresh for relative time (AC: 6)
  - [x] 2.1: Create `now` signal that updates every minute
  - [x] 2.2: Use `setInterval` in `onMount`
  - [x] 2.3: Clean up interval in `onCleanup`
  - [x] 2.4: Pass `now` to `formatRelativeTime` for reactivity

- [x] Task 3: Integrate into Home page (AC: 7)
  - [x] 3.1: Import DataFreshnessIndicator in Home.tsx
  - [x] 3.2: Calculate date range from time series data (first/last bucket)
  - [x] 3.3: Calculate aggregate sample size from all models
  - [x] 3.4: Derive last update from latest time series bucket
  - [x] 3.5: Position below model comparison table, above bias cards

- [x] Task 4: Verification (AC: 8)
  - [x] 4.1: Run `npm run type-check` - no errors
  - [x] 4.2: Run `npm run lint` - no new warnings
  - [x] 4.3: Manual test with sample data

## Dev Notes

### Existing Data Available

The backend API already provides most data needed. **No backend changes required.**

**From `SiteAccuracyResponse` → `ModelAccuracyMetrics`:**
```typescript
interface ModelAccuracyMetrics {
  modelId: number;
  modelName: string;
  mae: number;
  bias: number;
  stdDev: number;
  sampleSize: number;          // ✅ Already available
  confidenceLevel: ConfidenceLevel;  // ✅ Already available
  confidenceMessage: string;   // ✅ Already available
}
```

**From `TimeSeriesAccuracyResponse` → `TimeSeriesDataPoint[]`:**
```typescript
interface TimeSeriesDataPoint {
  bucket: string;  // ISO 8601 date - can derive date range
  mae: number;
  bias: number;
  sampleSize: number;
}
```

### Data Derivation Strategy

1. **sampleSize**: Sum of `sampleSize` across all models from accuracy data, OR use highest model's sample size
2. **confidenceLevel**: Use the lowest confidence level across all models (most conservative)
3. **dateRange**: Calculate from time series data:
   - `start`: First bucket date from any model's time series
   - `end`: Last bucket date from any model's time series
4. **lastUpdate**: Use the `end` date from time series (latest data point)

### Component Props Interface

```typescript
interface DataFreshnessIndicatorProps {
  lastUpdate: Date;
  sampleSize: number;
  dateRange: {
    start: Date;
    end: Date;
  };
  confidenceLevel: ConfidenceLevel;
}
```

### Relative Time Formatting

```typescript
const formatRelativeTime = (date: Date, now: Date) => {
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
};
```

### Auto-Refresh Pattern

```typescript
const [now, setNow] = createSignal(new Date());

onMount(() => {
  const interval = setInterval(() => {
    setNow(new Date());
  }, 60000); // Update every minute

  onCleanup(() => clearInterval(interval));
});
```

### Confidence Level Visual Indicators

| Level | Icon | Color | Message |
|-------|------|-------|---------|
| validated | ✅ | green-700 | "Metrics are statistically reliable (90+ days)" |
| preliminary | 🔶 | orange-700 | "Results will stabilize with more data (30-89 days)" |
| insufficient | ⚠️ | red-700 | "Collect more data for reliable metrics (<30 days)" |

### Layout Structure

```tsx
<div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
  <h4 class="text-sm font-semibold text-gray-700 mb-3">Data Information</h4>

  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    {/* Last Updated */}
    {/* Sample Size */}
    {/* Data Range */}
  </div>

  <div class="mt-4 pt-4 border-t border-gray-200">
    {/* Confidence Level Indicator */}
  </div>
</div>
```

### Integration in Home.tsx

Calculate freshness data from existing signals:

```typescript
// Derive freshness data from time series and accuracy data
const freshnessData = createMemo(() => {
  const tsData = timeSeriesData();
  const accData = accuracyData();

  if (!accData || tsData.length === 0) return null;

  // Get all buckets from all models
  const allBuckets = tsData.flatMap(m => m.data.map(d => d.date));
  if (allBuckets.length === 0) return null;

  // Sort to find min/max
  allBuckets.sort((a, b) => a.getTime() - b.getTime());

  // Aggregate sample size (sum across models)
  const totalSampleSize = accData.models.reduce((sum, m) => sum + m.sampleSize, 0);

  // Use lowest confidence level (most conservative)
  const confidenceLevels: ConfidenceLevel[] = ['insufficient', 'preliminary', 'validated'];
  const lowestConfidence = accData.models.reduce((lowest, m) => {
    const currentIdx = confidenceLevels.indexOf(m.confidenceLevel);
    const lowestIdx = confidenceLevels.indexOf(lowest);
    return currentIdx < lowestIdx ? m.confidenceLevel : lowest;
  }, 'validated' as ConfidenceLevel);

  return {
    lastUpdate: allBuckets[allBuckets.length - 1],
    sampleSize: totalSampleSize,
    dateRange: {
      start: allBuckets[0],
      end: allBuckets[allBuckets.length - 1],
    },
    confidenceLevel: lowestConfidence,
  };
});
```

### Solid.js Patterns (CRITICAL)

**DO NOT destructure props:**
```tsx
// ❌ BAD
const DataFreshnessIndicator = ({ lastUpdate, sampleSize }) => { ... }

// ✅ GOOD
const DataFreshnessIndicator: Component<DataFreshnessIndicatorProps> = (props) => {
  // Access via props.lastUpdate, props.sampleSize
}
```

**Use createMemo for derived values:**
```tsx
const daysOfData = createMemo(() => {
  const diffMs = props.dateRange.end.getTime() - props.dateRange.start.getTime();
  return Math.floor(diffMs / 86400000);
});
```

### File Structure

```
frontend/src/
├── components/
│   ├── DataFreshnessIndicator.tsx  # NEW
│   ├── AccuracyTimeSeriesChart.tsx
│   ├── BiasCharacterizationCard.tsx
│   ├── ModelComparisonTable.tsx
│   └── ...
├── pages/
│   └── Home.tsx                     # MODIFY (add freshness section)
└── lib/
    └── types.ts                     # NO CHANGES NEEDED
```

### Previous Story Learnings (4-5)

From Story 4-5 code review:
1. **XSS Prevention**: Sanitize any user-provided text before rendering in HTML
2. **Error States**: Always provide user-visible error feedback, not just console logs
3. **Magic Numbers**: Use named constants for colors and configuration
4. **Shadow Consistency**: Use `shadow-md` for loading skeletons to match existing components

### Positioning in Home Page

Place between Model Comparison Table and Bias Characterization Cards:

```
┌─────────────────────────────────────┐
│         Model Comparison Table       │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│      DataFreshnessIndicator         │  ← NEW
│  (Last Update | Sample Size | Range)│
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  ✅ Validated Data                   │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│    Bias Characterization Cards       │
└─────────────────────────────────────┘
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-4.6]
- [Source: _bmad-output/project-context.md#Solid.js-Patterns]
- [Source: frontend/src/lib/types.ts - ModelAccuracyMetrics, TimeSeriesDataPoint]
- [Source: frontend/src/pages/Home.tsx - Integration patterns]
- [Source: Story 4-5 Code Review - Learnings applied]

## Change Log

- 2026-01-16: Story created with comprehensive context for dev agent
- 2026-01-16: Implementation completed, moved to review
- 2026-01-16: Code review completed, 5 issues fixed, status → done

## Dev Agent Record

### Implementation Summary

Successfully implemented the DataFreshnessIndicator component displaying data freshness information with auto-refresh capability.

### Files Modified

1. **frontend/src/components/DataFreshnessIndicator.tsx** - NEW: Data freshness indicator component (145 lines)
2. **frontend/src/pages/Home.tsx** - MODIFIED: Added DataFreshnessIndicator integration with freshness data derivation

### Key Implementation Decisions

1. **Data Derivation Strategy**: All freshness data is derived from existing API responses (no backend changes required):
   - `sampleSize`: Sum of all models' sample sizes
   - `confidenceLevel`: Lowest (most conservative) level across models
   - `dateRange`: Calculated from time series bucket dates (first/last)
   - `lastUpdate`: Uses the latest time series bucket date

2. **Auto-Refresh Pattern**: Used `setInterval` in `onMount` with `onCleanup` for proper interval cleanup. The `now` signal updates every minute to trigger reactive re-renders of relative time.

3. **Confidence Level Configuration**: Used a typed configuration object (`CONFIDENCE_CONFIG`) to centralize icon, color, and message definitions for each confidence level.

4. **Time Constants**: Extracted magic numbers into named constants (`MS_PER_MINUTE`, `MS_PER_HOUR`, `MS_PER_DAY`) for clarity.

5. **Conservative Confidence Calculation**: When multiple models have different confidence levels, the lowest (most conservative) is displayed to avoid giving users false confidence.

### Verification Results

- **TypeScript**: Passes with no errors (`npm run type-check`)
- **ESLint**: No new warnings (existing false-positive warning in AccuracyTimeSeriesChart)

### Acceptance Criteria Status

| AC | Description | Status |
|----|-------------|--------|
| AC1 | DataFreshnessIndicator Component | PASS |
| AC2 | Last Update Timestamp (relative + absolute) | PASS |
| AC3 | Sample Size Display | PASS |
| AC4 | Date Range Display | PASS |
| AC5 | Confidence Level Indicator | PASS |
| AC6 | Auto-refresh Relative Time | PASS |
| AC7 | Integration into Home page | PASS |
| AC8 | TypeScript compiles | PASS |

## Senior Developer Review (AI)

**Reviewer:** boss | **Date:** 2026-01-16 | **Outcome:** APPROVED

### Issues Found and Fixed

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| M1 | MEDIUM | Negative time difference not handled in formatRelativeTime | FIXED |
| M2 | MEDIUM | Freshness data shows while time series still loading | FIXED |
| L1 | LOW | Zero days display when start=end date | FIXED |
| L2 | LOW | Mutating sort on array | FIXED |
| L3 | LOW | Non-exhaustive confidence levels array | FIXED |

### Fixes Applied

1. **Negative Time Handling** - Added check for negative `diffMs` at start of `formatRelativeTime()`, treating future dates as "just now"
2. **Loading State Check** - Added `!isLoadingTimeSeries()` condition to DataFreshnessIndicator Show block
3. **Minimum Days** - Used `Math.max(1, ...)` to ensure at least "1 day of data" is shown
4. **Immutable Sort** - Changed to `[...allBuckets].sort()` creating new array before sorting
5. **Shared Constant** - Extracted `CONFIDENCE_LEVELS_ORDERED` constant for maintainability

### Verification

- TypeScript: PASS (no errors)
- ESLint: No new warnings (existing false-positive in AccuracyTimeSeriesChart)
