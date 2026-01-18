---
title: 'AROME Multi-Site Optimization & Forecast Horizon Management'
slug: 'arome-multisite-optimization'
created: '2026-01-18'
status: 'in-progress'
stepsCompleted: ['step-01-understand']
tech_stack: ['python', 'xarray', 'cfgrib', 'asyncio']
files_to_modify:
  - 'backend/collectors/arome.py'
  - 'backend/services/data_collection.py'
  - 'backend/cli.py'
files_to_create:
  - 'backend/collectors/meteociel.py'
code_patterns: ['collector-pattern', 'retry-with-backoff']
test_patterns: ['integration-test', 'mock-grib']
---

# Tech-Spec: AROME Multi-Site Optimization & Forecast Horizon Management

**Created:** 2026-01-18

## Overview

### Problem Statement

The current AROME collector has several architectural limitations:

1. **Inefficient multi-site downloads**: Downloads one GRIB file per site (~60MB each). For N sites, this means N downloads of the same data, wasting bandwidth and hitting rate limits.

2. **Incomplete forecast horizons**: Only fetches `00H06H` time range (hours 0-6). Missing critical horizons for forecast verification:
   - `07H12H` (hours 7-12)
   - `13H18H` (hours 13-18)
   - `19H24H` (hours 19-24)
   - `25H30H` (hours 25-30)
   - `31H36H` (hours 31-36)

3. **Incorrect time range format**: Code tried `06H12H` which returns 404. The correct format has a gap: `07H12H`, `13H18H`, etc.

4. **No fallback strategy**: If GRIB download fails, there's no alternative data source.

5. **Missing data handling**: No strategy for handling unavailable data in model comparisons.

### Solution

Implement a multi-site GRIB architecture with full forecast horizons and fallback support:

1. **Single GRIB download for all sites**: Download one France-wide GRIB file → extract data for N sites via coordinate interpolation.

2. **All forecast horizons**: Download all 6 time range packages to cover 0-36 hours:
   - `00H06H`, `07H12H`, `13H18H`, `19H24H`, `25H30H`, `31H36H`

3. **21h UTC run preference**: Use the last run of the day for next-day forecasts.

4. **Meteociel fallback**: Scrape Meteociel.fr as backup if Météo-France API fails.

5. **N/A marking**: Mark missing data as unavailable rather than penalizing models in comparisons.

### Scope

**In Scope:**
- Refactor AROME collector for multi-site efficiency
- Add all forecast horizon time ranges (0-36h)
- Fix time range format (`07H12H` not `06H12H`)
- Create Meteociel scraper as fallback collector
- Update data collection service for multi-site GRIB processing
- Update CLI commands for new architecture
- Add integration tests for AROME API

**Out of Scope:**
- ARPEGE model support (separate effort)
- Real-time alerts/notifications
- Historical data backfill
- UI changes

## Context for Development

### Codebase Patterns

The codebase follows these patterns:

1. **Collector Pattern**: All collectors inherit from `BaseCollector` with `collect_forecast()` and `collect_observation()` methods.

2. **Retry with Backoff**: HTTP requests use `@retry_with_backoff` decorator for resilience.

3. **Rate Limiting**: Collectors implement `_enforce_rate_limit()` for API quotas.

4. **Data Models**: Use `ForecastData` and `ObservationData` dataclasses.

5. **Decimal Precision**: All values stored as `Decimal` with explicit precision.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `backend/collectors/arome.py` | Current AROME collector (to refactor) |
| `backend/collectors/base.py` | Base collector interface |
| `backend/collectors/meteo_parapente.py` | Reference for multi-site handling |
| `backend/services/data_collection.py` | Orchestrates collector calls |
| `backend/core/data_models.py` | ForecastData/ObservationData models |
| `backend/collectors/utils.py` | HttpClient, retry decorators |

### Technical Decisions

1. **GRIB Time Range Format**: The Météo-France API uses non-contiguous ranges:
   - `00H06H` (hours 0-6)
   - `07H12H` (hours 7-12) — NOT `06H12H`
   - `13H18H` (hours 13-18)
   - `19H24H` (hours 19-24)
   - `25H30H` (hours 25-30)
   - `31H36H` (hours 31-36)
   - `37H42H` (hours 37-42) — available but beyond our 36h requirement

2. **Package Selection**: Use `SP1` package which contains:
   - `u10`: 10m U wind component (m/s)
   - `v10`: 10m V wind component (m/s)
   - `t2m`: 2m temperature (Kelvin)

3. **Run Time**: Use 21h UTC run for next-day forecasts. Run times available: 00, 03, 06, 09, 12, 15, 18, 21 UTC.

4. **Multi-Site Extraction**: Load GRIB once, interpolate to each site's coordinates using xarray `.interp()`.

5. **Fallback Strategy**: Meteociel provides AROME visualizations we can scrape as text values.

## Implementation Plan

### Tasks

#### Phase 1: Fix Time Range Format (Quick Win)

- [ ] **Task 1.1**: Update `TIME_RANGES` constant with correct format
  ```python
  TIME_RANGES = ["00H06H", "07H12H", "13H18H", "19H24H", "25H30H", "31H36H"]
  ```

- [ ] **Task 1.2**: Add `download_all_horizons()` method to fetch all time ranges

- [ ] **Task 1.3**: Update `_build_api_url()` to accept time_range parameter

#### Phase 2: Multi-Site Architecture

- [ ] **Task 2.1**: Create `AROMEBulkCollector` class for multi-site processing
  - Single GRIB download
  - List of sites with coordinates
  - Extract data for each site via interpolation

- [ ] **Task 2.2**: Refactor `collect_forecast()` to support multi-site mode
  ```python
  async def collect_forecasts_bulk(
      self,
      sites: list[dict],  # [{id, lat, lon}, ...]
      forecast_run: datetime,
  ) -> dict[int, list[ForecastData]]:  # site_id -> forecasts
  ```

- [ ] **Task 2.3**: Update `DataCollectionService` to use bulk collection
  - Group sites by model
  - Call bulk collector once per model
  - Distribute results by site

#### Phase 3: Fallback with Meteociel

- [ ] **Task 3.1**: Create `MeteocielCollector` class
  - Scrape AROME forecasts from meteociel.fr
  - Parse temperature, wind speed, wind direction
  - Map to ForecastData format

- [ ] **Task 3.2**: Integrate fallback in data collection service
  ```python
  try:
      forecasts = await arome_collector.collect_forecasts_bulk(sites)
  except (HttpClientError, RetryExhaustedError):
      forecasts = await meteociel_collector.collect_forecasts(sites)
  ```

- [ ] **Task 3.3**: Add N/A marking for missing data
  - Add `is_available` field to ForecastData (or use None value)
  - Update comparison logic to skip N/A entries

#### Phase 4: Testing & Validation

- [ ] **Task 4.1**: Add integration tests for AROME API
  - Test all time ranges return 200
  - Test GRIB parsing for each range
  - Test multi-site interpolation

- [ ] **Task 4.2**: Add smoke test for full pipeline
  - Verify all horizons collected
  - Verify multi-site extraction works
  - Verify fallback triggers correctly

- [ ] **Task 4.3**: Update CLI commands
  - Add `--horizons` flag for specific ranges
  - Add `--fallback` flag to force Meteociel
  - Add `--bulk` flag for multi-site mode

### Acceptance Criteria

1. **Time Ranges**: All 6 time ranges download successfully:
   - `00H06H`, `07H12H`, `13H18H`, `19H24H`, `25H30H`, `31H36H`

2. **Multi-Site Efficiency**: Single GRIB download serves N sites (not N downloads)

3. **Forecast Horizons**: Data collected for hours 0-36 at 1-hour intervals

4. **Run Selection**: 21h UTC run used by default for next-day forecasts

5. **Fallback**: Meteociel scraping activates on GRIB failure

6. **Missing Data**: N/A values don't penalize model accuracy scores

7. **Tests**: Integration tests pass with real API calls

## Additional Context

### Dependencies

- `xarray>=2024.1.0` - NetCDF/GRIB data handling
- `cfgrib>=0.9.10` - GRIB2 file parsing
- `beautifulsoup4>=4.12.0` - Meteociel HTML scraping (new)
- `httpx>=0.26.0` - Async HTTP client

### Testing Strategy

1. **Unit Tests**: Mock GRIB data for parsing logic
2. **Integration Tests**: Real API calls with `@pytest.mark.integration`
3. **Smoke Tests**: CLI command `python -m cli smoke-test`
4. **Manual Validation**: Compare collected data with Meteociel display

### Notes

**API Documentation Sources:**
- [Météo-France Confluence](https://confluence-meteofrance.atlassian.net/wiki/spaces/OpenDataMeteoFrance/pages/853639487)
- [data.gouv.fr AROME packages](https://www.data.gouv.fr/en/datasets/paquets-arome-resolution-0-025deg/)
- [Architecture-Performance blog](https://www.architecture-performance.fr/ap_blog/fetching-arome-weather-forecasts-and-plotting-temperatures/)

**Rate Limits:**
- Météo-France API: 50 requests/minute
- Each time range is a separate request (6 requests per run)
- Multi-site reduces requests from N*6 to 6 per collection cycle

**GRIB File Size:**
- SP1 package (0.025° resolution): ~60MB per time range
- Total per collection: ~360MB (6 time ranges)
- This is acceptable as it's downloaded once for all sites
