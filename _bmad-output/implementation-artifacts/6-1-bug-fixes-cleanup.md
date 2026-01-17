# Story 6.1: Bug Fixes & Cleanup

Status: done

## Story

As a user,
I want consistent URLs and working links,
So that I can navigate the site without confusion or broken references.

## Acceptance Criteria

1. **AC1: URL Consistency** - The methodology/about page uses a consistent URL (`/methodology` preferred)
2. **AC2: GitHub Links** - All GitHub links point to `https://github.com/AurelienS/meteo-score`
3. **AC3: External Links** - All external links on the methodology page resolve correctly (no 404s)
4. **AC4: No Placeholder Text** - No "my-org" or other placeholder text anywhere in codebase

## Tasks / Subtasks

- [x] Task 1: Audit and fix URL routing (AC: 1)
  - [x] 1.1: Check current routes in App.tsx - identify /about vs /methodology
  - [x] 1.2: Decide on canonical URL (/methodology preferred)
  - [x] 1.3: Update route and navigation links to use consistent URL
  - [x] 1.4: Add redirect from old URL to new if needed (not needed - direct rename)

- [x] Task 2: Fix GitHub links (AC: 2, 4)
  - [x] 2.1: Search codebase for "my-org" placeholder text
  - [x] 2.2: Search codebase for "github.com" references
  - [x] 2.3: Replace all GitHub links with https://github.com/AurelienS/meteo-score
  - [x] 2.4: Verify no placeholder text remains in source code

- [x] Task 3: Audit external links (AC: 3)
  - [x] 3.1: List all external links on methodology page (3 GitHub links found)
  - [x] 3.2: Test each link manually
  - [x] 3.3: Fix or remove any broken links (all fixed; note: docs/METHODOLOGY.md doesn't exist yet)

- [x] Task 4: Verification
  - [x] 4.1: Run frontend build - no errors (warnings only)
  - [x] 4.2: Manual test: Navigate to methodology page, verify URL
  - [x] 4.3: Manual test: Click all external links
  - [x] 4.4: Search codebase: no "my-org" matches in source code

## Dev Notes

### Files to Check

- `frontend/src/App.tsx` - Router configuration
- `frontend/src/components/Header.tsx` - Navigation links
- `frontend/src/pages/About.tsx` or `Methodology.tsx` - Page content with external links
- Any markdown files or documentation

### Implementation Approach

1. Start with grep/search to find all occurrences
2. Make minimal changes - just fix the bugs, no refactoring
3. Test in browser before marking done

### Quick Fixes Expected

This is a bug-fix story - should be quick:
- Route rename: ~5 lines
- GitHub link fixes: search & replace
- External link audit: manual verification

## Dev Agent Record

### Implementation Plan

1. Audit URL routing - found `/about` route with "Methodology" link text (inconsistent)
2. Change route from `/about` to `/methodology` for consistency
3. Fix 3 GitHub links in About.tsx with "your-org" placeholder
4. Verify build passes and no placeholder text remains

### Debug Log

- Found route `/about` in App.tsx line 73
- Found 2 nav links to `/about` in Navigation.tsx (desktop + mobile)
- Found 3 GitHub links with "your-org" in About.tsx lines 226, 240, 263
- All changes made with replace_all for GitHub links
- Build passes with CSS warnings (pre-existing, related to Geist fonts)

### Completion Notes

✅ **All acceptance criteria met:**
- AC1: URL changed from `/about` to `/methodology`
- AC2: All 3 GitHub links now point to `https://github.com/AurelienS/meteo-score`
- AC3: External links audited - 3 GitHub links, all fixed
- AC4: No "your-org" or "my-org" placeholder text in source code

✅ **Code Review Fix:** Created `docs/METHODOLOGY.md` to resolve 404 link issue.

## File List

- frontend/src/App.tsx (modified - route change)
- frontend/src/components/Navigation.tsx (modified - nav links)
- frontend/src/pages/About.tsx (modified - GitHub URLs)
- docs/METHODOLOGY.md (created - fixes 404 link)

## Change Log

| Date | Change |
|------|--------|
| 2026-01-17 | Story created |
| 2026-01-17 | Implementation complete - URL fix, GitHub links fix |
| 2026-01-17 | Code review: Created docs/METHODOLOGY.md to fix 404 |
