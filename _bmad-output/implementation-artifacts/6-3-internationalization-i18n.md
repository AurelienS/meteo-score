# Story 6.3: Internationalization (i18n)

Status: done

## Story

As a user,
I want to view the app in French or English,
So that I can understand the content in my preferred language.

## Acceptance Criteria

1. **AC1: French Default** - App displays in French when browser language is French ("Météo Score" with accent) ✅
2. **AC2: English Support** - App displays in English when browser language is English ("Meteo Score" without accent) ✅
3. **AC3: Language Switcher** - User can switch language via UI toggle ✅
4. **AC4: Instant Switch** - Language updates immediately without page reload ✅
5. **AC5: Persistence** - Language preference is remembered across sessions ✅
6. **AC6: Complete Translation** - All user-facing strings are translated ✅

## Tasks / Subtasks

- [x] Task 1: Setup i18n infrastructure (AC: 1, 2)
  - [x] 1.1: Create i18n context with language state
  - [x] 1.2: Create translation loading mechanism
  - [x] 1.3: Detect browser language on first visit
  - [x] 1.4: Add localStorage persistence

- [x] Task 2: Create translation files (AC: 6)
  - [x] 2.1: Create French translation file (fr.json)
  - [x] 2.2: Create English translation file (en.json)
  - [x] 2.3: Extract all hardcoded strings from components

- [x] Task 3: Create Language Switcher component (AC: 3, 4)
  - [x] 3.1: Create toggle button (FR | EN)
  - [x] 3.2: Add to Navigation header
  - [x] 3.3: Style for both themes

- [x] Task 4: Update components with translations (AC: 6)
  - [x] 4.1: Update Navigation component
  - [x] 4.2: Update Footer component
  - [x] 4.3: Update Home page
  - [x] 4.4: Update About/Methodology page
  - [x] 4.5: Update Admin page
  - [x] 4.6: Update error messages and loading states

- [x] Task 5: Handle brand name (AC: 1, 2)
  - [x] 5.1: "Météo Score" in French (with accent)
  - [x] 5.2: "Meteo Score" in English (without accent)
  - [x] 5.3: Update page title dynamically

- [x] Task 6: Verification
  - [x] 6.1: Run frontend build - no errors
  - [x] 6.2: Test language switcher works
  - [x] 6.3: Test persistence across reload
  - [x] 6.4: Test browser detection
  - [x] 6.5: Verify all strings translated

## Dev Notes

### Architecture

- Simple context-based i18n (no heavy library needed)
- JSON translation files in src/locales/
- useI18n hook for components
- Nested keys for organization (e.g., nav.home, pages.about.title)

### Translation File Structure

```json
{
  "brand": "Météo Score",
  "nav": {
    "home": "Accueil",
    "methodology": "Méthodologie"
  },
  "pages": {
    "home": {
      "title": "Comparaison des Modèles Météo",
      "subtitle": "..."
    }
  },
  "common": {
    "loading": "Chargement...",
    "error": "Une erreur est survenue"
  }
}
```

## Dev Agent Record

### Implementation Plan

1. Create I18nContext with language state, browser detection, and localStorage persistence
2. Create fr.json and en.json translation files with all strings
3. Create LanguageSwitcher component with FR|EN toggle
4. Wrap app with I18nProvider in index.tsx
5. Update Navigation and Footer to use translations
6. Update Home, About, and Admin pages to use translations
7. Update document title dynamically based on language

### Debug Log

- Initial implementation created I18nContext, LanguageSwitcher, fr.json, en.json
- Code review identified missing translations in Home, About, Admin pages
- Extended translation files with comprehensive keys for all pages
- Updated all pages to use t() function for all user-facing strings
- Added dynamic page title updates in I18nContext

### Completion Notes

All acceptance criteria met:
- French and English fully supported with proper brand name handling (accent in French)
- Language switcher added to Navigation header (both desktop and mobile)
- Instant switching via Solid.js reactivity
- Persistence via localStorage with key 'meteo-score-language'
- All user-facing strings translated across Home, About/Methodology, Admin, Navigation, and Footer

## File List

### Created
- frontend/src/locales/fr.json - French translations (169 lines)
- frontend/src/locales/en.json - English translations (169 lines)
- frontend/src/contexts/I18nContext.tsx - I18n context provider with language detection
- frontend/src/components/LanguageSwitcher.tsx - FR|EN toggle component

### Modified
- frontend/src/index.tsx - Wrapped app with I18nProvider
- frontend/src/components/Navigation.tsx - Added LanguageSwitcher and t() usage
- frontend/src/components/Footer.tsx - Added t() usage for all strings
- frontend/src/pages/Home.tsx - Added t() usage for all strings, translated error messages
- frontend/src/pages/About.tsx - Complete rewrite to use t() for all content
- frontend/src/pages/Admin.tsx - Complete rewrite to use t() for all strings

## Change Log

| Date | Change |
|------|--------|
| 2026-01-17 | Story created |
| 2026-01-17 | Initial implementation: I18nContext, LanguageSwitcher, translation files |
| 2026-01-17 | Code review: Extended translations, updated all pages with t() function |
| 2026-01-17 | Story completed: All ACs verified, build passing |
