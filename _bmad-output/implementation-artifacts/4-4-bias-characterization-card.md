# Story 4.4: Bias Characterization Card

Status: done

## Story

As a user,
I want to see a clear explanation of each model's systematic bias,
So that I can mentally adjust forecasts when using that model.

## Acceptance Criteria

1. **AC1: BiasCharacterizationCard Component** - Card displaying bias interpretation for a single model
2. **AC2: Bias Interpretation Logic** - Categorize bias as Excellent/Underestimation/Overestimation
3. **AC3: Color-coded Borders** - Visual distinction (green/blue/orange) based on bias type
4. **AC4: Icon Indicators** - Icons matching bias category (target/up arrow/down arrow)
5. **AC5: Practical Example** - Show adjusted forecast example based on historical bias
6. **AC6: Confidence Warnings** - Warning messages for preliminary/insufficient data
7. **AC7: Integration** - Display cards for all models in Home page
8. **AC8: TypeScript** - No compilation errors, proper typing
9. **AC9: Accessibility** - Proper semantics, color not sole indicator

## Tasks / Subtasks

- [x] Task 1: Create BiasCharacterizationCard component (AC: 1, 2, 3, 4, 8)
  - [x] 1.1: Create `frontend/src/components/BiasCharacterizationCard.tsx`
  - [x] 1.2: Define BiasCharacterizationCardProps interface
  - [x] 1.3: Implement `getBiasInterpretation()` helper function
  - [x] 1.4: Add color-coded left border based on bias type
  - [x] 1.5: Add icon indicators (text-based for accessibility)

- [x] Task 2: Add practical example section (AC: 5)
  - [x] 2.1: Calculate adjusted forecast value
  - [x] 2.2: Display example with wind speed context
  - [x] 2.3: Show formula explanation

- [x] Task 3: Add confidence warnings (AC: 6, 9)
  - [x] 3.1: Add `<Show>` conditional for preliminary data warning
  - [x] 3.2: Add `<Show>` conditional for insufficient data warning
  - [x] 3.3: Use semantic warning colors with text labels

- [x] Task 4: Integrate into Home page (AC: 7)
  - [x] 4.1: Import BiasCharacterizationCard in Home.tsx
  - [x] 4.2: Add section below ModelComparisonTable
  - [x] 4.3: Render card for each model using `<For>`
  - [x] 4.4: Pass correct props from accuracyData

- [x] Task 5: Verification (AC: 8)
  - [x] 5.1: Run `npm run type-check` - no errors
  - [x] 5.2: Run `npm run lint` - no warnings
  - [x] 5.3: Manual test with different bias values

## Dev Notes

### Data Source

The bias data is **already available** from Story 4-3's API integration. The `accuracyData()` signal in Home.tsx contains:

```typescript
interface SiteAccuracyResponse {
  siteId: number;
  siteName: string;
  parameterId: number;
  parameterName: string;
  horizon: number;
  models: ModelAccuracyMetrics[];  // <-- Contains bias data
}

interface ModelAccuracyMetrics {
  modelId: number;
  modelName: string;
  mae: number;
  bias: number;                    // <-- This is what we display
  stdDev: number;
  sampleSize: number;
  confidenceLevel: ConfidenceLevel; // <-- For warnings
  confidenceMessage: string;
}
```

**No new API call needed** - reuse `accuracyData()` from Home.tsx.

### Bias Interpretation Logic

```typescript
/** Threshold below which bias is considered negligible */
const BIAS_EXCELLENT_THRESHOLD = 1.0;

interface BiasInterpretation {
  title: string;
  description: string;
  icon: string;
  borderColor: string;
  textClass: string;
}

function getBiasInterpretation(
  bias: number,
  modelName: string,
  parameterName: string,
  parameterUnit: string
): BiasInterpretation {
  const absBias = Math.abs(bias);

  if (absBias < BIAS_EXCELLENT_THRESHOLD) {
    return {
      title: 'Excellent Calibration',
      description: `${modelName} has minimal systematic bias for ${parameterName}.`,
      icon: '🎯',
      borderColor: 'border-l-green-500',
      textClass: 'text-green-700',
    };
  } else if (bias > 0) {
    return {
      title: 'Systematic Underestimation',
      description: `${modelName} typically underestimates ${parameterName} by ${absBias.toFixed(1)} ${parameterUnit} on average. Expect conditions to be slightly stronger than predicted.`,
      icon: '⬆️',
      borderColor: 'border-l-blue-500',
      textClass: 'text-blue-700',
    };
  } else {
    return {
      title: 'Systematic Overestimation',
      description: `${modelName} typically overestimates ${parameterName} by ${absBias.toFixed(1)} ${parameterUnit} on average. Expect conditions to be slightly weaker than predicted.`,
      icon: '⬇️',
      borderColor: 'border-l-orange-500',
      textClass: 'text-orange-700',
    };
  }
}
```

**Bias Sign Convention:**
- Positive bias = forecast < observed (model underestimates)
- Negative bias = forecast > observed (model overestimates)

### Practical Example Calculation

```typescript
// Example: If model forecasts 25 km/h wind, what to expect?
const exampleForecast = 25;
const adjustedValue = exampleForecast - props.bias;

// If bias = +3 (underestimation): expect 25 - 3 = 22 km/h actual
// If bias = -3 (overestimation): expect 25 - (-3) = 28 km/h actual
```

### Component Structure

```tsx
// src/components/BiasCharacterizationCard.tsx
import type { Component } from 'solid-js';
import { Show } from 'solid-js';
import type { ConfidenceLevel } from '../lib/types';

export interface BiasCharacterizationCardProps {
  modelName: string;
  bias: number;
  parameterName: string;
  parameterUnit: string;
  confidenceLevel: ConfidenceLevel;
}

const BiasCharacterizationCard: Component<BiasCharacterizationCardProps> = (props) => {
  // ... implementation
};

export default BiasCharacterizationCard;
```

### Solid.js Patterns (CRITICAL)

**Props access (NO destructuring):**
```tsx
const BiasCharacterizationCard: Component<Props> = (props) => {
  // ✅ GOOD: props.bias, props.modelName
  // ❌ BAD: { bias, modelName } destructuring
}
```

**Derived values with createMemo:**
```tsx
const interpretation = createMemo(() =>
  getBiasInterpretation(props.bias, props.modelName, props.parameterName, props.parameterUnit)
);
```

**Conditional rendering:**
```tsx
<Show when={props.confidenceLevel === 'preliminary'}>
  <p class="text-sm text-orange-600">
    ⚠️ This bias characterization is preliminary.
  </p>
</Show>
```

### Integration in Home.tsx

```tsx
// After ModelComparisonTable section
<Show when={!isLoadingAccuracy() && !accuracyError() && accuracyData()}>
  {(data) => (
    <>
      {/* Model comparison table */}
      <div class="bg-white rounded-lg shadow-md p-6 mb-6">
        <ModelComparisonTable
          models={data().models}
          parameterUnit={selectedParameterUnit()}
        />
      </div>

      {/* Bias characterization cards */}
      <div class="space-y-4">
        <h2 class="text-lg font-semibold text-gray-900">
          Bias Characterization
        </h2>
        <For each={data().models}>
          {(model) => (
            <BiasCharacterizationCard
              modelName={model.modelName}
              bias={model.bias}
              parameterName={data().parameterName}
              parameterUnit={selectedParameterUnit()}
              confidenceLevel={model.confidenceLevel}
            />
          )}
        </For>
      </div>
    </>
  )}
</Show>
```

### Tailwind Classes

**Card container with colored border:**
```tsx
<div class={`border-l-4 ${interpretation().borderColor} bg-white p-6 rounded-lg shadow-sm`}>
```

**Icon and content layout:**
```tsx
<div class="flex items-start">
  <div class="text-3xl mr-4" aria-hidden="true">{interpretation().icon}</div>
  <div class="flex-1">
    <h3 class="text-lg font-semibold text-gray-900 mb-2">
      {interpretation().title}
    </h3>
    <p class="text-gray-700 mb-3">
      {interpretation().description}
    </p>
  </div>
</div>
```

**Practical example box:**
```tsx
<div class="mt-4 p-4 bg-gray-50 rounded">
  <p class="text-sm font-medium text-gray-700 mb-2">Practical Example:</p>
  <p class="text-sm text-gray-600">
    If {props.modelName} forecasts wind at 25 {props.parameterUnit}, expect actual conditions around{' '}
    <span class="font-semibold">{adjustedValue().toFixed(0)} {props.parameterUnit}</span>
    {' '}based on historical bias.
  </p>
</div>
```

**Confidence warnings:**
```tsx
<Show when={props.confidenceLevel === 'preliminary'}>
  <p class="text-sm text-orange-600 mt-3">
    ⚠️ This bias characterization is preliminary. Results will stabilize with more data.
  </p>
</Show>
<Show when={props.confidenceLevel === 'insufficient'}>
  <p class="text-sm text-red-600 mt-3">
    ⚠️ Insufficient data to reliably characterize bias.
  </p>
</Show>
```

### Accessibility Requirements

- Icon is decorative (`aria-hidden="true"`) - text provides meaning
- Color is not sole indicator - title text describes bias type
- Warning messages use semantic text (not just color)
- Proper heading hierarchy (h3 for card titles)

### File Structure

```
frontend/src/
├── components/
│   ├── BiasCharacterizationCard.tsx  # NEW
│   ├── ModelComparisonTable.tsx      # From Story 4-3
│   ├── SiteSelector.tsx
│   ├── ParameterSelector.tsx
│   └── HorizonSelector.tsx
├── pages/
│   └── Home.tsx                      # MODIFY (add bias cards section)
└── lib/
    ├── api.ts
    └── types.ts                      # Already has ConfidenceLevel
```

### Previous Story Context (4-3)

Story 4-3 established:
- `accuracyData` signal with `SiteAccuracyResponse`
- `createEffect` for reactive API fetching
- `selectedParameterUnit()` helper for unit display
- Pattern of using Show with callback: `<Show when={...}>{(data) => ...}</Show>`
- `ModelAccuracyMetrics` type with all needed fields

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-4.4]
- [Source: _bmad-output/project-context.md#Solid.js-Patterns]
- [Source: frontend/src/lib/types.ts - ModelAccuracyMetrics, ConfidenceLevel]
- [Source: frontend/src/pages/Home.tsx - accuracyData signal]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Completion Notes

All acceptance criteria satisfied:

1. **AC1 ✅** BiasCharacterizationCard component created with full props interface
2. **AC2 ✅** Bias interpretation logic categorizes as Excellent/Underestimation/Overestimation
3. **AC3 ✅** Color-coded borders (green/blue/orange) via Tailwind border-l-{color}
4. **AC4 ✅** Icon indicators with aria-hidden for accessibility
5. **AC5 ✅** Practical example showing adjusted forecast calculation
6. **AC6 ✅** Confidence warnings for preliminary/insufficient data
7. **AC7 ✅** Integrated into Home page using `<For>` to render all models
8. **AC8 ✅** TypeScript compiles, ESLint passes
9. **AC9 ✅** Accessible: icons decorative, text provides meaning, color not sole indicator

**Implementation highlights:**
- Uses createMemo for reactive bias interpretation
- Practical example hidden for insufficient data (no meaningful adjustment)
- Reuses existing `accuracyData()` signal - no new API calls
- Fragment wrapper (`<>`) for multiple elements in Show callback

### File List

**New files created:**
- `frontend/src/components/BiasCharacterizationCard.tsx`

**Files modified:**
- `frontend/src/pages/Home.tsx`

## Change Log

- 2026-01-16: Story created with comprehensive context for dev agent
- 2026-01-16: Implementation complete - all 5 tasks done, all ACs satisfied
- 2026-01-16: Code review completed - 3 issues found and fixed:
  - M1 (CRITICAL): Fixed bias adjustment formula from subtraction to addition
  - M2: Made example forecast value parameter-appropriate using createMemo
  - L1: Added Show guard for empty models array in bias cards section
