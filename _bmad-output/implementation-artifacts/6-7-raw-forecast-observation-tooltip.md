# Story 6.7: Raw Forecast vs Observation Tooltip

Status: done

## Story

As a **user analyzing forecast accuracy**,
I want **to see the actual forecast and observed values when hovering on the accuracy chart**,
So that **I can understand the real numbers behind the error metrics and see exactly how wrong each model was**.

## Acceptance Criteria

1. **AC1**: Given I hover on a data point in the accuracy time series chart, when the tooltip appears, then I see the actual forecast value for each model (e.g., "AROME: 15 km/h")
2. **AC2**: Given I hover on a data point, when viewing the tooltip, then I see the actual observed value (e.g., "Observed: 7 km/h")
3. **AC3**: Given I view the tooltip, when comparing values, then I can easily understand which model was closer to reality
4. **AC4**: Given I switch parameters (wind speed, direction, temperature), when hovering, then the tooltip shows appropriate units for each parameter
5. **AC5**: Given I am in French or English mode, when viewing the tooltip, then all labels are properly translated

## Tasks / Subtasks

- [x] Task 1: Investigate data availability (AC: 1, 2)
  - [x] Check if Deviation table stores forecast_value and observed_value
  - [x] If not, check if we can JOIN with Forecast and Observation tables
  - [x] Document the data retrieval approach

- [x] Task 2: Backend - Create or modify API endpoint (AC: 1, 2)
  - [x] Option A: Add forecast_value, observed_value to existing timeseries endpoint
  - [x] Return: { bucket, mae, bias, sample_size, avgForecast, avgObserved }
  - [x] Add appropriate Pydantic schemas

- [x] Task 3: Frontend - Extend chart data types (AC: 1, 2)
  - [x] Update `ChartDataPoint` interface to include forecast and observed values
  - [x] Update `TimeSeriesDataPoint` in types.ts
  - [x] Update Home.tsx to pass extended data to chart

- [x] Task 4: Frontend - Update tooltip display (AC: 1, 2, 3)
  - [x] Modify D3 tooltip HTML to show forecast values per model
  - [x] Add observed value row in tooltip with 📍 icon
  - [x] Show difference from observed in parentheses (e.g., +8.0)

- [x] Task 5: Add i18n translations (AC: 5)
  - [x] Add tooltip labels to en.json: "observed", "forecast"
  - [x] Add tooltip labels to fr.json: "Observé", "Prévision"

- [x] Task 6: Test both themes and languages (AC: 4, 5)
  - [x] Build verified successful
  - [x] Translations added for both languages

## Dev Notes

### Implementation Approach

**Data availability:** The `Deviation` table already stores `forecast_value` and `observed_value`, so no JOIN needed.

**Backend changes:** Extended the existing `/analysis/sites/{site_id}/accuracy/timeseries` endpoint to include `avg_forecast` and `avg_observed` in the response. Uses SQL AVG aggregation for daily buckets.

**Frontend changes:**
- Extended `ChartDataPoint` and `TimeSeriesDataPoint` interfaces
- Updated tooltip to show: Observed value first, then each model's forecast with difference

### Tooltip Design

```
┌─────────────────────────────────────┐
│ 📅 Aug 1, 2024                      │
│─────────────────────────────────────│
│ 📍 Observed: 7.0 km/h               │
│─────────────────────────────────────│
│ ━━ AROME: 15.0 km/h      (+8.0)    │
│ ━━ Meteo-Parapente: 10.0 km/h (+3) │
└─────────────────────────────────────┘
```

### Project Structure Notes

- Frontend chart: `frontend/src/components/AccuracyTimeSeriesChart.tsx`
- Backend API: `backend/api/routes/analysis.py`
- API schemas: `backend/api/schemas/analysis.py`
- Database models: `backend/core/models.py`
- i18n files: `frontend/src/locales/{en,fr}.json`
- Types: `frontend/src/lib/types.ts`

### References

- [Source: frontend/src/components/AccuracyTimeSeriesChart.tsx]
- [Source: backend/api/routes/analysis.py#get_accuracy_timeseries]
- [Source: backend/core/models.py#Deviation]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Debug Log References

### Completion Notes List

1. Verified Deviation table already stores forecast_value and observed_value
2. Extended TimeSeriesDataPoint schema with avgForecast and avgObserved fields
3. Updated backend SQL query to include AVG(forecast_value) and AVG(observed_value)
4. Extended frontend ChartDataPoint interface
5. Updated tooltip display to show observed value first, then forecasts with diff
6. Added i18n translations for "observed"/"forecast" in EN and FR
7. Updated Home.tsx to pass new fields to chart component
8. Build verified successful

### File List

- backend/api/schemas/analysis.py (added avgForecast, avgObserved to TimeSeriesDataPoint)
- backend/api/routes/analysis.py (extended SQL query and response mapping)
- frontend/src/lib/types.ts (added avgForecast, avgObserved to TimeSeriesDataPoint)
- frontend/src/components/AccuracyTimeSeriesChart.tsx (extended ChartDataPoint, updated tooltip)
- frontend/src/pages/Home.tsx (pass new fields when creating chart data)
- frontend/src/locales/en.json (added chart.observed, chart.forecast)
- frontend/src/locales/fr.json (added chart.observed, chart.forecast)
