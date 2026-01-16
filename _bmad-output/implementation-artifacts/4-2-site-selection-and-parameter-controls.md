# Story 4.2: Site Selection & Parameter Controls

Status: done

## Story

As a user,
I want to select a flying site and weather parameters,
So that I can view accuracy metrics for my specific use case.

## Acceptance Criteria

1. **AC1: SiteSelector Component** - Dropdown to select flying site from available sites
2. **AC2: ParameterSelector Component** - Radio buttons to select weather parameter (wind_speed, wind_direction, temperature)
3. **AC3: HorizonSelector Component** - Button group to select forecast horizon (+6h, +12h, +24h, +48h)
4. **AC4: State Management** - Solid.js signals for selectedSiteId, selectedParameterId, selectedHorizon
5. **AC5: Responsive Design** - Mobile: vertical layout; Desktop: horizontal grid
6. **AC6: TypeScript** - No compilation errors, proper typing for all components
7. **AC7: API Integration** - Fetch sites and parameters from backend API on mount

## Tasks / Subtasks

- [x] Task 1: Create SiteSelector component (AC: 1, 6)
  - [x] 1.1: Create `frontend/src/components/SiteSelector.tsx`
  - [x] 1.2: Define SiteSelectorProps interface (sites, selectedSiteId, onSiteChange)
  - [x] 1.3: Implement dropdown with `<For>` component for site options
  - [x] 1.4: Style with Tailwind (border, rounded, focus ring)

- [x] Task 2: Create ParameterSelector component (AC: 2, 6)
  - [x] 2.1: Create `frontend/src/components/ParameterSelector.tsx`
  - [x] 2.2: Define ParameterSelectorProps interface (parameters, selectedParameterId, onParameterChange)
  - [x] 2.3: Implement radio buttons with `<For>` component
  - [x] 2.4: Display parameter name with unit (e.g., "Wind Speed (km/h)")

- [x] Task 3: Create HorizonSelector component (AC: 3, 6)
  - [x] 3.1: Create `frontend/src/components/HorizonSelector.tsx`
  - [x] 3.2: Define HorizonSelectorProps interface (horizons, selectedHorizon, onHorizonChange)
  - [x] 3.3: Implement button group with active state styling
  - [x] 3.4: Format buttons as "+6h", "+12h", etc.

- [x] Task 4: Update Home page with selectors (AC: 4, 5)
  - [x] 4.1: Replace placeholder content in `frontend/src/pages/Home.tsx`
  - [x] 4.2: Add createSignal for selectedSiteId, selectedParameterId, selectedHorizon
  - [x] 4.3: Integrate all three selector components
  - [x] 4.4: Add responsive grid layout (mobile: stack, desktop: row)

- [x] Task 5: Add API integration (AC: 7)
  - [x] 5.1: Add fetchSites() and fetchParameters() functions to `frontend/src/lib/api.ts`
  - [x] 5.2: Use createResource or onMount to fetch data on page load
  - [x] 5.3: Handle loading and error states with `<Show>` components
  - [x] 5.4: Update types.ts if needed for Parameter displayName

- [x] Task 6: Verification (AC: 6)
  - [x] 6.1: Run `npm run type-check` - no errors
  - [x] 6.2: Run `npm run dev` - page loads without errors
  - [x] 6.3: Manual test: Verify selector state changes correctly
  - [x] 6.4: Test responsive layout on mobile and desktop widths

## Dev Notes

### Solid.js Best Practices (CRITICAL)

**DO NOT use React patterns - this is Solid.js!**

```tsx
// ❌ BAD - React pattern, breaks reactivity
function SiteSelector({ sites, selectedSiteId }) { ... }

// ✅ GOOD - Solid.js pattern, preserves reactivity
function SiteSelector(props: SiteSelectorProps) {
  return <select value={props.selectedSiteId}>...</select>
}
```

**Use `<For>` instead of `.map()`:**
```tsx
// ❌ BAD - React pattern
{sites.map(site => <option key={site.id}>{site.name}</option>)}

// ✅ GOOD - Solid.js control flow
<For each={props.sites}>
  {(site) => <option value={site.id}>{site.name}</option>}
</For>
```

**Signal naming convention:**
```tsx
// ✅ GOOD - Specific loading states
const [isLoadingSites, setIsLoadingSites] = createSignal(false);
const [isLoadingParameters, setIsLoadingParameters] = createSignal(false);

// ❌ BAD - Generic loading state
const [loading, setLoading] = createSignal(false);
```

### Backend API Endpoints

| Endpoint | Method | Response |
|----------|--------|----------|
| `/api/v1/sites/` | GET | `{ data: Site[], meta: {...} }` |
| `/api/v1/parameters/` | GET | `{ data: Parameter[], meta: {...} }` |

**Site type:**
```typescript
interface Site {
  id: number;
  name: string;
  lat: number;
  lon: number;
  alt: number;
  createdAt: string;
}
```

**Parameter type (needs displayName):**
```typescript
interface Parameter {
  id: number;
  name: string;       // "wind_speed", "wind_direction", "temperature"
  unit: string;       // "km/h", "°", "°C"
  createdAt: string;
}
```

**Note:** The Parameter type in types.ts may need a `displayName` field, or create it client-side from `name`.

### Display Name Mapping

For MVP, map parameter names to display names in frontend:
```typescript
const PARAMETER_DISPLAY_NAMES: Record<string, string> = {
  'wind_speed': 'Wind Speed',
  'wind_direction': 'Wind Direction',
  'temperature': 'Temperature',
};
```

### Forecast Horizons

Standard horizons for MVP: `[6, 12, 24, 48]` hours

These are hardcoded in frontend since they match the backend analysis engine expectations.

### Component File Structure

```
frontend/src/
├── components/
│   ├── Navigation.tsx      # (existing)
│   ├── SiteSelector.tsx    # NEW
│   ├── ParameterSelector.tsx # NEW
│   └── HorizonSelector.tsx # NEW
├── pages/
│   └── Home.tsx            # MODIFY
└── lib/
    ├── api.ts              # MODIFY (add fetch functions)
    └── types.ts            # (existing, may need updates)
```

### Responsive Layout

**Mobile (< 768px):** Stack selectors vertically
```tsx
<div class="flex flex-col gap-6">
  <SiteSelector ... />
  <ParameterSelector ... />
  <HorizonSelector ... />
</div>
```

**Desktop (>= 768px):** Horizontal grid
```tsx
<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
  <SiteSelector ... />
  <ParameterSelector ... />
  <HorizonSelector ... />
</div>
```

### Previous Story Intelligence

From Story 4-1:
- App.tsx uses ErrorBoundary and Router correctly
- Navigation component exists
- API client structure established in lib/api.ts
- Types defined in lib/types.ts with camelCase (matching backend JSON)
- Tailwind CSS configured with primary color palette

From Epic 3 (API):
- Backend returns paginated responses: `{ data: T[], meta: {...} }`
- Endpoints use camelCase in JSON responses
- Analysis API at `/api/v1/analysis/sites/{site_id}/accuracy`

### Git Intelligence

Recent commits show:
- Backend follows TDD pattern
- API endpoints return properly typed responses
- CORS configured for localhost:5173

### Architecture Compliance

- ✅ Use Solid.js signals (NOT React useState)
- ✅ Use `<For>` and `<Show>` components
- ✅ Props via object access (NOT destructuring)
- ✅ TypeScript strict mode
- ✅ API calls through lib/api.ts (NOT direct fetch in components)
- ✅ Tailwind CSS for styling

### Testing Considerations

Manual testing for MVP:
1. Page loads without errors
2. Sites dropdown populates from API
3. Parameters display with units
4. Horizon buttons toggle correctly
5. Console shows no errors
6. Responsive layout works

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-4.2]
- [Source: _bmad-output/project-context.md#Solid.js-Patterns]
- [Source: _bmad-output/project-context.md#Frontend-Stack]
- [Source: frontend/src/lib/types.ts - existing types]
- [Source: backend/api/routes/sites.py - API endpoint]
- [Source: backend/api/routes/parameters.py - API endpoint]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Completion Notes

All acceptance criteria satisfied:

1. **AC1 ✅** SiteSelector component created with dropdown, `<For>` iteration, Tailwind styling
2. **AC2 ✅** ParameterSelector component created with radio buttons, display name mapping, unit display
3. **AC3 ✅** HorizonSelector component created with button group, active state styling, +Xh format
4. **AC4 ✅** State management using Solid.js signals (selectedSiteId, selectedParameterId, selectedHorizon)
5. **AC5 ✅** Responsive grid layout: `grid-cols-1 md:grid-cols-3`
6. **AC6 ✅** TypeScript compiles with no errors, ESLint passes with no warnings
7. **AC7 ✅** API integration via fetchSites() and fetchParameters() with loading/error states

**Implementation highlights:**
- All components follow Solid.js best practices (props object access, `<For>`, `<Show>`)
- Parameter display names mapped client-side from snake_case API names
- Loading skeleton with animate-pulse for better UX
- Error handling with user-friendly error display
- Current selection summary displayed below selectors

### File List

**New files created:**
- `frontend/src/components/SiteSelector.tsx`
- `frontend/src/components/ParameterSelector.tsx`
- `frontend/src/components/HorizonSelector.tsx`

**Files modified:**
- `frontend/src/pages/Home.tsx`
- `frontend/src/lib/api.ts`

### Senior Developer Review (AI)

**Review Date:** 2026-01-16
**Reviewer:** Claude Opus 4.5 (Code Review Workflow)
**Review Outcome:** Approved with fixes

**Issues Found:** 0 High, 3 Medium, 3 Low
**Issues Fixed:** 3 Medium

**Action Items (all resolved):**
- [x] M1: Fixed duplicate type definitions - now uses Pick<Site/Parameter> from types.ts
- [x] M2: Added accessibility attributes - id/for linking, aria-labelledby, aria-pressed
- [x] M3: Added empty state handling - "No sites/parameters available" placeholders

**Verification:** TypeScript compiles, ESLint passes, all ACs satisfied

## Change Log

- 2026-01-16: Story created with comprehensive context for dev agent
- 2026-01-16: Implementation complete - all 6 tasks done, all ACs satisfied
- 2026-01-16: Code review complete - 3 medium issues fixed (accessibility, types, empty states)
