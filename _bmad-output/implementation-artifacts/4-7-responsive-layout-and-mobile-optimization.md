# Story 4.7: Responsive Layout & Mobile Optimization

Status: done

## Story

As a user,
I want the web interface to work seamlessly on mobile devices,
So that I can check MétéoScore from the field before flying.

## Acceptance Criteria

1. **AC1: Footer Component** - Add footer to Layout with copyright and links
2. **AC2: Viewport Meta** - Update viewport with maximum-scale=5.0 for accessibility
3. **AC3: Touch-Friendly Controls** - Minimum 44x44px tap targets on buttons/links
4. **AC4: Responsive Typography** - Mobile-first text sizes with desktop scaling
5. **AC5: Mobile Table** - Stack or simplify table columns on small screens
6. **AC6: Chart Responsiveness** - Chart margins/legend adapt to screen size
7. **AC7: TypeScript** - No compilation errors

## Tasks / Subtasks

- [x] Task 1: Add footer to Layout (AC: 1)
  - [x] 1.1: Create Footer component in `frontend/src/components/Footer.tsx`
  - [x] 1.2: Add "MétéoScore - Open Source Weather Forecast Accuracy Platform"
  - [x] 1.3: Add link to GitHub repo (use placeholder or config)
  - [x] 1.4: Integrate Footer into App.tsx Layout

- [x] Task 2: Update viewport meta (AC: 2)
  - [x] 2.1: Add `maximum-scale=5.0` to viewport meta in `index.html`

- [x] Task 3: Ensure touch-friendly controls (AC: 3)
  - [x] 3.1: Review HorizonSelector - ensure radio buttons have 44x44px touch targets
  - [x] 3.2: Review select dropdowns in SiteSelector/ParameterSelector
  - [x] 3.3: Add spacing/padding where needed

- [x] Task 4: Responsive typography (AC: 4)
  - [x] 4.1: Review heading sizes (text-2xl on mobile, text-3xl on md+)
  - [x] 4.2: Ensure body text is readable (text-sm on mobile, text-base on md+)

- [x] Task 5: Mobile table optimization (AC: 5)
  - [x] 5.1: Add mobile-specific styles to ModelComparisonTable
  - [x] 5.2: Consider hiding less essential columns (Sample Size) on mobile
  - [x] 5.3: Ensure horizontal scroll works smoothly

- [x] Task 6: Chart responsiveness (AC: 6)
  - [x] 6.1: Review AccuracyTimeSeriesChart margins for mobile
  - [x] 6.2: Ensure legend doesn't overflow on small screens

- [x] Task 7: Verification (AC: 7)
  - [x] 7.1: Run `npm run type-check` - no errors
  - [x] 7.2: Run `npm run lint` - no new warnings
  - [x] 7.3: Manual test on mobile viewport (Chrome DevTools)

## Dev Notes

### Current Responsive State

**Already Implemented:**
1. **Navigation.tsx** - Hamburger menu for mobile (`md:hidden` toggle)
2. **Home.tsx** - Responsive grid (`grid-cols-1 md:grid-cols-3`)
3. **ModelComparisonTable.tsx** - Horizontal scroll (`overflow-x-auto`)
4. **AccuracyTimeSeriesChart.tsx** - ResizeObserver for responsiveness

**Needs Work:**
1. No footer component
2. Viewport missing `maximum-scale=5.0`
3. Touch targets may be too small in some areas
4. Table columns don't adapt on mobile

### Footer Component

```tsx
// src/components/Footer.tsx
const Footer: Component = () => {
  return (
    <footer class="bg-white border-t border-gray-200 mt-12">
      <div class="container mx-auto px-4 py-6">
        <p class="text-sm text-gray-500 text-center">
          MétéoScore - Open Source Weather Forecast Accuracy Platform
        </p>
      </div>
    </footer>
  );
};
```

### Viewport Meta Update

```html
<!-- Current -->
<meta name="viewport" content="width=device-width, initial-scale=1" />

<!-- Updated -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0" />
```

The `maximum-scale=5.0` allows zooming for accessibility (don't use `maximum-scale=1` which breaks accessibility).

### Touch Target Guidelines

- Minimum 44x44px (iOS) or 48x48px (Android Material)
- Use padding to increase touch area without visual changes
- Apply `min-h-[44px] min-w-[44px]` where needed

### Mobile Table Strategy

Option 1: Hide less important columns on mobile:
```tsx
<th class="hidden md:table-cell">Sample Size</th>
<td class="hidden md:table-cell">{model.sampleSize}</td>
```

Option 2: Stack cells vertically on mobile (card layout)

For MVP, Option 1 (hiding columns) is simpler and sufficient.

### Chart Mobile Adjustments

Current chart margins: `{ top: 20, right: 120, bottom: 40, left: 60 }`

For mobile, consider:
- Reduce right margin (legend below chart or smaller)
- Reduce left margin slightly
- Use smaller font sizes for axis labels

The ResizeObserver already handles width changes, but margins may need conditional adjustment.

### Tailwind Responsive Prefixes

- Base (no prefix): Mobile-first
- `sm:` - 640px+
- `md:` - 768px+
- `lg:` - 1024px+
- `xl:` - 1280px+

### File Structure

```
frontend/src/
├── components/
│   ├── Footer.tsx           # NEW
│   ├── Navigation.tsx       # Review touch targets
│   ├── HorizonSelector.tsx  # Review touch targets
│   ├── SiteSelector.tsx     # Review touch targets
│   ├── ParameterSelector.tsx # Review touch targets
│   ├── ModelComparisonTable.tsx # Mobile column hiding
│   └── AccuracyTimeSeriesChart.tsx # Review margins
├── pages/
│   └── Home.tsx             # Review typography
├── App.tsx                  # Add Footer to Layout
└── index.html               # Update viewport meta
```

### Previous Story Learnings

From Story 4-5 and 4-6 code reviews:
1. Use named constants for configuration values
2. Handle edge cases (negative values, empty states)
3. Use `shadow-md` for consistency with existing components

### Testing Approach

1. Chrome DevTools Device Mode:
   - iPhone SE (375px)
   - iPhone 12 Pro (390px)
   - iPad (768px)
   - Desktop (1024px+)

2. Key things to check:
   - Navigation hamburger works
   - Selectors are tappable
   - Table scrolls horizontally
   - Chart renders at narrow widths
   - Text is readable

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-4.7]
- [Source: frontend/src/components/Navigation.tsx - Existing responsive nav]
- [Source: frontend/src/components/ModelComparisonTable.tsx - Table with overflow]
- [Source: frontend/src/App.tsx - Layout component]
- [Tailwind CSS Responsive Design](https://tailwindcss.com/docs/responsive-design)

## Change Log

- 2026-01-16: Story created with comprehensive context for dev agent
- 2026-01-16: Implementation completed, moved to review
- 2026-01-16: Code review completed, 5 issues fixed, status → done

## Dev Agent Record

### Implementation Summary

Successfully implemented responsive layout and mobile optimization for the MétéoScore web interface.

### Files Modified

1. **frontend/src/components/Footer.tsx** - NEW: Footer component with copyright and GitHub link (35 lines)
2. **frontend/src/App.tsx** - MODIFIED: Added Footer import and integration into Layout, flex layout for sticky footer
3. **frontend/index.html** - MODIFIED: Updated viewport meta with maximum-scale=5.0 for accessibility
4. **frontend/src/components/HorizonSelector.tsx** - MODIFIED: Added min-h-[44px] min-w-[44px] for touch targets
5. **frontend/src/components/SiteSelector.tsx** - MODIFIED: Added min-h-[44px] for touch-friendly select
6. **frontend/src/components/ParameterSelector.tsx** - MODIFIED: Added min-h-[44px] and hover state for radio labels
7. **frontend/src/pages/Home.tsx** - MODIFIED: Responsive typography (text-2xl md:text-3xl for h1, text-sm md:text-base for body)
8. **frontend/src/components/ModelComparisonTable.tsx** - MODIFIED: Hide Sample Size column on mobile, responsive heading
9. **frontend/src/components/AccuracyTimeSeriesChart.tsx** - MODIFIED: Responsive margins, responsive heading and padding

### Key Implementation Decisions

1. **Footer Design**: Simple footer with copyright text and GitHub link. Used flex layout in App.tsx (`flex flex-col`, `flex-grow` on main) to ensure footer stays at bottom.

2. **Touch Targets**: Applied `min-h-[44px]` to all interactive elements. Added hover states to radio labels for better feedback.

3. **Responsive Typography**: Mobile-first approach with base sizes scaling up at `md:` breakpoint (768px+).

4. **Mobile Table**: Chose to hide Sample Size column on mobile using `hidden md:table-cell` - simpler than card layout and sufficient for MVP.

5. **Chart Responsiveness**: Created `getResponsiveMargins()` function with mobile/desktop configurations. Reduced right margin (120→100) and left margin (60→45) on mobile to fit legend.

### Verification Results

- **TypeScript**: Passes with no errors (`npm run type-check`)
- **ESLint**: No new warnings (existing false-positive in AccuracyTimeSeriesChart)

### Acceptance Criteria Status

| AC | Description | Status |
|----|-------------|--------|
| AC1 | Footer Component | PASS |
| AC2 | Viewport Meta | PASS |
| AC3 | Touch-Friendly Controls | PASS |
| AC4 | Responsive Typography | PASS |
| AC5 | Mobile Table | PASS |
| AC6 | Chart Responsiveness | PASS |
| AC7 | TypeScript | PASS |

## Senior Developer Review (AI)

**Reviewer:** Claude | **Date:** 2026-01-16 | **Outcome:** APPROVED

### Issues Found and Fixed

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| M1 | MEDIUM | Missing focus ring on GitHub link (accessibility gap) | FIXED |
| M2 | MEDIUM | Legend may overflow on very narrow screens (<320px) | FIXED |
| L1 | LOW | Link text "GitHub" not descriptive enough | FIXED |
| L2 | LOW | Inconsistent shadow on Footer | FIXED |
| L3 | LOW | Hover state on touch devices (sticky hover) | ACCEPTED |
| L4 | LOW | Year calculated on every render | FIXED |

### Fixes Applied

1. **Focus Ring (M1)** - Added `focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded` to GitHub link
2. **Legend Truncation (M2)** - Added `truncateForLegend()` function that truncates model names to 12 chars with ellipsis on mobile; reduced mobile right margin from 100px to 90px
3. **Descriptive Link (L1)** - Changed "GitHub" to "View on GitHub" with `aria-label="View MétéoScore source code on GitHub"`
4. **Shadow Consistency (L2)** - Added `shadow-sm` to footer element
5. **Year Memoization (L4)** - Moved `new Date().getFullYear()` to module-level constant `CURRENT_YEAR`

### Verification

- TypeScript: PASS (no errors)
- ESLint: No new warnings (existing false-positive in AccuracyTimeSeriesChart)
