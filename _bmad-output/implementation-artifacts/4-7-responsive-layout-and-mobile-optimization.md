# Story 4.7: Responsive Layout & Mobile Optimization

Status: ready-for-dev

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

- [ ] Task 1: Add footer to Layout (AC: 1)
  - [ ] 1.1: Create Footer component in `frontend/src/components/Footer.tsx`
  - [ ] 1.2: Add "MétéoScore - Open Source Weather Forecast Accuracy Platform"
  - [ ] 1.3: Add link to GitHub repo (use placeholder or config)
  - [ ] 1.4: Integrate Footer into App.tsx Layout

- [ ] Task 2: Update viewport meta (AC: 2)
  - [ ] 2.1: Add `maximum-scale=5.0` to viewport meta in `index.html`

- [ ] Task 3: Ensure touch-friendly controls (AC: 3)
  - [ ] 3.1: Review HorizonSelector - ensure radio buttons have 44x44px touch targets
  - [ ] 3.2: Review select dropdowns in SiteSelector/ParameterSelector
  - [ ] 3.3: Add spacing/padding where needed

- [ ] Task 4: Responsive typography (AC: 4)
  - [ ] 4.1: Review heading sizes (text-2xl on mobile, text-3xl on md+)
  - [ ] 4.2: Ensure body text is readable (text-sm on mobile, text-base on md+)

- [ ] Task 5: Mobile table optimization (AC: 5)
  - [ ] 5.1: Add mobile-specific styles to ModelComparisonTable
  - [ ] 5.2: Consider hiding less essential columns (Sample Size) on mobile
  - [ ] 5.3: Ensure horizontal scroll works smoothly

- [ ] Task 6: Chart responsiveness (AC: 6)
  - [ ] 6.1: Review AccuracyTimeSeriesChart margins for mobile
  - [ ] 6.2: Ensure legend doesn't overflow on small screens

- [ ] Task 7: Verification (AC: 7)
  - [ ] 7.1: Run `npm run type-check` - no errors
  - [ ] 7.2: Run `npm run lint` - no new warnings
  - [ ] 7.3: Manual test on mobile viewport (Chrome DevTools)

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
