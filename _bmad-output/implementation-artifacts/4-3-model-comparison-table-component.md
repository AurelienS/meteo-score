# Story 4.3: Model Comparison Table Component

Status: done

## Story

As a user,
I want to see a comparison table of model accuracy metrics,
So that I can identify which model performs best for my selected site and parameter.

## Acceptance Criteria

1. **AC1: ModelComparisonTable Component** - Table displaying MAE, bias, sample size, confidence for all models
2. **AC2: Sorting** - Models automatically sorted by MAE (best first)
3. **AC3: Best Model Highlight** - Green background row + "Best" badge for top performer
4. **AC4: Confidence Badges** - Color-coded badges (red/orange/green) for insufficient/preliminary/validated
5. **AC5: Bias Text** - Human-readable bias interpretation (Underestimates/Overestimates by X)
6. **AC6: Responsive** - Horizontal scroll on mobile, full-width on desktop
7. **AC7: Empty State** - "No data available" message when no models
8. **AC8: TypeScript** - No compilation errors, proper typing
9. **AC9: API Integration** - Fetch accuracy data from `/api/v1/analysis/sites/{siteId}/accuracy`

## Tasks / Subtasks

- [x] Task 1: Add API types and fetch function (AC: 8, 9)
  - [x] 1.1: Add `ModelAccuracyMetrics` interface to `frontend/src/lib/types.ts`
  - [x] 1.2: Add `SiteAccuracyResponse` interface to `frontend/src/lib/types.ts`
  - [x] 1.3: Add `fetchSiteAccuracy(siteId, parameterId, horizon)` to `frontend/src/lib/api.ts`

- [x] Task 2: Create ModelComparisonTable component (AC: 1, 5, 6, 7, 8)
  - [x] 2.1: Create `frontend/src/components/ModelComparisonTable.tsx`
  - [x] 2.2: Define ModelComparisonTableProps interface (models, parameterUnit)
  - [x] 2.3: Implement table with columns: Model, MAE, Bias, Sample Size, Confidence
  - [x] 2.4: Add `getBiasText()` helper for bias interpretation
  - [x] 2.5: Add empty state with `<Show when={models.length === 0}>`
  - [x] 2.6: Add responsive `overflow-x-auto` wrapper

- [x] Task 3: Add confidence badges (AC: 4)
  - [x] 3.1: Implement `getConfidenceBadge()` helper function
  - [x] 3.2: Map confidence levels to colors (insufficient=red, preliminary=orange, validated=green)
  - [x] 3.3: Style badges with Tailwind (rounded, px-2 py-1, text-xs)

- [x] Task 4: Add sorting and best model highlight (AC: 2, 3)
  - [x] 4.1: Sort models by MAE in component or parent
  - [x] 4.2: Highlight first row with `bg-green-50`
  - [x] 4.3: Add "Best" badge next to first model name

- [x] Task 5: Integrate into Home page (AC: 9)
  - [x] 5.1: Add `fetchSiteAccuracy` call to Home.tsx
  - [x] 5.2: Add `accuracyData` signal for API response
  - [x] 5.3: Add `isLoadingAccuracy` signal
  - [x] 5.4: Trigger fetch when site/parameter/horizon changes
  - [x] 5.5: Render ModelComparisonTable with sorted models

- [x] Task 6: Verification (AC: 8)
  - [x] 6.1: Run `npm run type-check` - no errors
  - [x] 6.2: Run `npm run lint` - no warnings
  - [x] 6.3: Manual test with sample data

## Dev Notes

### Backend API Endpoint

**Endpoint:** `GET /api/v1/analysis/sites/{site_id}/accuracy`

**Query Parameters:**
- `parameterId` (required): Weather parameter ID
- `horizon` (required): Forecast horizon in hours

**Response Schema (camelCase JSON):**
```typescript
interface SiteAccuracyResponse {
  siteId: number;
  siteName: string;
  parameterId: number;
  parameterName: string;
  horizon: number;
  models: ModelAccuracyMetrics[];
}

interface ModelAccuracyMetrics {
  modelId: number;
  modelName: string;
  mae: number;
  bias: number;
  stdDev: number;
  sampleSize: number;
  confidenceLevel: 'insufficient' | 'preliminary' | 'validated';
  confidenceMessage: string;
}
```

### Confidence Level Thresholds

From architecture document:
- **insufficient**: < 50 samples → Red badge
- **preliminary**: 50-199 samples → Orange badge
- **validated**: >= 200 samples → Green badge

### Bias Interpretation Logic

```typescript
function getBiasText(bias: number, unit: string): string {
  if (Math.abs(bias) < 0.5) {
    return 'No systematic bias';
  } else if (bias > 0) {
    return `Underestimates by ${bias.toFixed(1)} ${unit}`;
  } else {
    return `Overestimates by ${Math.abs(bias).toFixed(1)} ${unit}`;
  }
}
```

**Note:** Positive bias means forecast < observed (underestimation).

### Sorting Logic

```typescript
// Sort by MAE ascending (best accuracy first)
const sortedModels = () => {
  return [...props.models].sort((a, b) => a.mae - b.mae);
};
```

### Table Structure

| Column | Data | Notes |
|--------|------|-------|
| Model | `modelName` | + "Best" badge for first row |
| MAE | `mae.toFixed(1)` | With unit from props |
| Bias | `getBiasText(bias, unit)` | Human-readable |
| Sample Size | `sampleSize` | + " measurements" |
| Confidence | Badge component | Color-coded |

### Solid.js Patterns (CRITICAL)

**Props access (NO destructuring):**
```tsx
const ModelComparisonTable: Component<Props> = (props) => {
  // ✅ GOOD: props.models
  // ❌ BAD: { models } destructuring
}
```

**Reactive sorting with createMemo:**
```tsx
const sortedModels = createMemo(() => {
  return [...props.models].sort((a, b) => a.mae - b.mae);
});
```

**Index access in For:**
```tsx
<For each={sortedModels()}>
  {(model, index) => {
    const isBest = index() === 0; // index is a function!
    // ...
  }}
</For>
```

### Accessibility Requirements

- Table should have proper `<thead>` and `<tbody>`
- Confidence badges need descriptive text (not just color)
- "Best" badge provides text indicator, not just color

### Tailwind Classes

**Table container:**
```tsx
<div class="overflow-x-auto">
  <table class="min-w-full bg-white border border-gray-200 rounded-lg">
```

**Header row:**
```tsx
<thead class="bg-gray-50">
  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
```

**Best row highlight:**
```tsx
<tr class={isBest ? 'bg-green-50' : ''}>
```

**Confidence badge:**
```tsx
<span class={`px-2 py-1 text-xs font-medium rounded ${badge.color}`}>
```

### API Integration Pattern

```tsx
// In Home.tsx
const [accuracyData, setAccuracyData] = createSignal<SiteAccuracyResponse | null>(null);
const [isLoadingAccuracy, setIsLoadingAccuracy] = createSignal(false);

// Refetch when selections change
createEffect(() => {
  const siteId = selectedSiteId();
  const paramId = selectedParameterId();
  const horizon = selectedHorizon();

  if (siteId && paramId) {
    fetchAccuracyData(siteId, paramId, horizon);
  }
});

const fetchAccuracyData = async (siteId: number, paramId: number, horizon: number) => {
  setIsLoadingAccuracy(true);
  try {
    const data = await fetchSiteAccuracy(siteId, paramId, horizon);
    setAccuracyData(data);
  } catch (err) {
    // Handle error
  } finally {
    setIsLoadingAccuracy(false);
  }
};
```

### Previous Story Context

From Story 4-2:
- Home.tsx has signals for selectedSiteId, selectedParameterId, selectedHorizon
- API client established in lib/api.ts with fetchApi<T>() wrapper
- Types in lib/types.ts with Site, Parameter, PaginatedResponse

### File Structure

```
frontend/src/
├── components/
│   ├── ModelComparisonTable.tsx  # NEW
│   ├── SiteSelector.tsx
│   ├── ParameterSelector.tsx
│   └── HorizonSelector.tsx
├── pages/
│   └── Home.tsx                  # MODIFY
└── lib/
    ├── api.ts                    # MODIFY (add fetchSiteAccuracy)
    └── types.ts                  # MODIFY (add accuracy types)
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-4.3]
- [Source: _bmad-output/project-context.md#Solid.js-Patterns]
- [Source: backend/api/schemas/analysis.py - Response schemas]
- [Source: backend/api/routes/analysis.py - API endpoint]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Completion Notes

All acceptance criteria satisfied:

1. **AC1 ✅** ModelComparisonTable component with all columns (Model, MAE, Bias, Sample Size, Confidence)
2. **AC2 ✅** Models sorted by MAE using createMemo
3. **AC3 ✅** Best model highlighted with bg-green-50 and "Best" badge
4. **AC4 ✅** Confidence badges color-coded (red/orange/green)
5. **AC5 ✅** Bias text shows human-readable interpretation
6. **AC6 ✅** Responsive with overflow-x-auto wrapper
7. **AC7 ✅** Empty state with "No data available" message
8. **AC8 ✅** TypeScript compiles, ESLint passes
9. **AC9 ✅** API integration with fetchSiteAccuracy and createEffect for reactive fetching

**Implementation highlights:**
- Uses createMemo for efficient reactive sorting
- createEffect triggers API refetch when selections change
- Separate loading/error states for accuracy data
- Proper Solid.js patterns (index() called in JSX)
- Accessible table with proper thead/tbody and aria-labelledby

### File List

**New files created:**
- `frontend/src/components/ModelComparisonTable.tsx`

**Files modified:**
- `frontend/src/pages/Home.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`

## Change Log

- 2026-01-16: Story created with comprehensive context for dev agent
- 2026-01-16: Implementation complete - all 6 tasks done, all ACs satisfied
- 2026-01-16: Code review completed - 5 issues found and fixed:
  - M1: Replaced non-null assertion with Solid.js Show callback pattern
  - M2: Added exhaustive type check in getConfidenceBadge switch
  - M3: Added table caption for accessibility (sr-only)
  - M4: Extracted bias threshold to named constant
  - L1: Added input validation in fetchSiteAccuracy API function
