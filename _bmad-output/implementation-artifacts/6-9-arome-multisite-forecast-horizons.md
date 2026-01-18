# Story 6.9: AROME Multi-Site Optimization & Forecast Horizon Management

Status: ready-for-dev

## Story

As a **paragliding pilot checking forecasts**,
I want **AROME forecasts to cover the full 36-hour horizon (not just 6 hours) and be collected efficiently for multiple sites**,
So that **I can compare AROME accuracy at different forecast horizons (+6h, +12h, +24h, +36h) and the system can scale to 50+ sites without hitting API rate limits**.

## Problem Statement

Critical issues discovered in AROME collector after story 6-8 implementation:

1. **Incomplete forecast horizons**: Only downloads `00H06H` time range (hours 0-6). Missing hours 7-36 of forecast data.
2. **Wrong time range format**: Code used `06H12H` which returns HTTP 404. Correct format is `07H12H` (non-contiguous boundaries).
3. **Inefficient multi-site**: Downloads one GRIB per site (~60MB each). For N sites = N*6 downloads, wasting bandwidth and hitting 50 req/min rate limit.
4. **No fallback**: If Météo-France API fails, no alternative data source.
5. **Missing data handling**: No strategy for unavailable data in model comparisons.

## Acceptance Criteria

1. **AC1: All Forecast Horizons Downloaded**
   - **Given** the AROME collector runs
   - **When** it downloads forecast data
   - **Then** it downloads all 6 time ranges: `00H06H`, `07H12H`, `13H18H`, `19H24H`, `25H30H`, `31H36H`
   - **And** forecast data covers hours 0-36 at 1-hour intervals (37 data points per parameter)

2. **AC2: Correct Time Range Format**
   - **Given** the AROME collector builds API URLs
   - **When** it specifies time ranges
   - **Then** it uses the correct non-contiguous format (`07H12H` not `06H12H`)
   - **And** all 6 API requests return HTTP 200

3. **AC3: Multi-Site Efficiency**
   - **Given** there are N sites configured (N >= 2)
   - **When** forecast collection runs
   - **Then** only 6 GRIB files are downloaded total (one per time range)
   - **And** data is extracted for all N sites from each GRIB via coordinate interpolation
   - **And** API requests reduced from N*6 to 6 per collection cycle

4. **AC4: Multi-Run Collection for Fair Horizon Comparison**
   - **Given** we want to compare model accuracy at different forecast horizons (H+6, H+12, H+24, H+36)
   - **When** collecting forecasts
   - **Then** multiple runs are collected per day (at minimum 00h, 06h, 12h, 18h UTC)
   - **And** each forecast record stores its `forecast_run` timestamp
   - **And** horizon is calculated as: `horizon = observation_time - forecast_run`
   - **And** both AROME and Meteo-Parapente use the same run schedule for fair comparison
   - **And** accuracy comparison groups forecasts by (observation_time, horizon) across models

   **Example - Comparing H+6 vs H+12 for observation at 12h Jan 19:**
   | Horizon | AROME Run | Meteo-Parapente Run | Both predict 12h |
   |---------|-----------|---------------------|------------------|
   | H+6     | 06h Jan 19 | 06h Jan 19 | Fair comparison |
   | H+12    | 00h Jan 19 | 00h Jan 19 | Fair comparison |
   | H+24    | 12h Jan 18 | 12h Jan 18 | Fair comparison |

5. **AC5: Meteociel Fallback**
   - **Given** the Météo-France API fails (HTTP error, timeout, rate limit)
   - **When** AROME collection is attempted
   - **Then** the system falls back to scraping Meteociel.fr for AROME data
   - **And** logs indicate fallback was triggered

6. **AC6: N/A for Missing Data**
   - **Given** forecast data is unavailable for a specific horizon
   - **When** accuracy analysis runs
   - **Then** the missing data is marked as N/A (null value)
   - **And** missing data does not penalize model accuracy scores
   - **And** UI shows "N/A" instead of 0 or hiding the data point

7. **AC7: Rate Limit Compliance**
   - **Given** Météo-France API has 50 req/min limit
   - **When** downloading multiple time ranges
   - **Then** requests are spaced by at least 1.2 seconds
   - **And** rate limiting is enforced across the collection session

8. **AC8: Integration Tests Pass**
   - **Given** integration tests with real API calls
   - **When** I run `pytest -m integration`
   - **Then** all AROME time ranges return HTTP 200
   - **And** GRIB parsing succeeds for each range
   - **And** multi-site interpolation extracts correct coordinates

9. **AC9: Methodology Page Documents Horizon Comparison**
   - **Given** a user visits the methodology page
   - **When** they read the data collection section
   - **Then** they understand what H+6, H+12, H+24, H+36 means
   - **And** they understand that multiple runs are collected daily
   - **And** they understand how models are compared fairly at same horizons
   - **And** the run schedule (00h, 06h, 12h, 18h UTC) is documented

## Tasks / Subtasks

- [ ] Task 1: Fix time range format (AC: 1, 2)
  - [ ] 1.1: Add `TIME_RANGES` constant with correct format: `["00H06H", "07H12H", "13H18H", "19H24H", "25H30H", "31H36H"]`
  - [ ] 1.2: Update `_download_grib2()` to accept `time_range` parameter
  - [ ] 1.3: Update `collect_forecast()` to loop through all 6 time ranges
  - [ ] 1.4: Add `from datetime import timedelta` import (missing)
  - [ ] 1.5: Add debug logging for each time range download

- [ ] Task 2: Multi-site architecture (AC: 3, 7)
  - [ ] 2.1: Create `collect_forecasts_bulk(sites: list[dict], forecast_run: datetime) -> dict[int, list[ForecastData]]` method
  - [ ] 2.2: Download GRIB once per time range (not per site)
  - [ ] 2.3: Extract data for each site via xarray `.interp(latitude=, longitude=)`
  - [ ] 2.4: Return dict mapping `site_id -> list[ForecastData]`
  - [ ] 2.5: Update `DataCollectionService.collect_forecasts()` to use bulk collection
  - [ ] 2.6: Ensure `_enforce_rate_limit()` applies across all downloads (1.2s spacing)

- [ ] Task 3: Multi-run collection for fair horizon comparison (AC: 4)
  - [ ] 3.1: Update scheduler to collect forecasts 4x daily (00h, 06h, 12h, 18h UTC runs)
  - [ ] 3.2: Ensure both AROME and Meteo-Parapente collect at same run times
  - [ ] 3.3: Store `forecast_run` timestamp with each ForecastData record
  - [ ] 3.4: Update matching logic: group by (observation_time, horizon) for fair comparison
  - [ ] 3.5: Update `_get_latest_run_time()` to return the target run time (not "latest available")
  - [ ] 3.6: Document run schedule in methodology page

- [ ] Task 4: Meteociel fallback collector (AC: 5)
  - [ ] 4.1: Create `backend/collectors/meteociel.py` implementing `BaseCollector`
  - [ ] 4.2: Scrape AROME forecasts from `https://www.meteociel.fr/modeles/arome.php?lat={lat}&lon={lon}`
  - [ ] 4.3: Parse temperature, wind speed, wind direction tables with BeautifulSoup4
  - [ ] 4.4: Map scraped values to `ForecastData` format with correct horizons
  - [ ] 4.5: Integrate fallback in data collection service with try/except wrapper

- [ ] Task 5: N/A handling for missing data (AC: 6)
  - [ ] 5.1: Update `ForecastData` to allow `value: Decimal | None` (currently non-nullable)
  - [ ] 5.2: Update `storage_service.save_forecasts()` to persist null values correctly
  - [ ] 5.3: Update accuracy analysis `matching_service.py` to skip N/A entries in MAE calculation
  - [ ] 5.4: Update API responses to include `isAvailable: bool` field or handle null gracefully

- [ ] Task 6: Integration tests (AC: 8)
  - [ ] 6.1: Add `@pytest.mark.integration` decorator to new tests
  - [ ] 6.2: Create `test_arome_time_ranges()` - verify all 6 ranges return HTTP 200
  - [ ] 6.3: Create `test_arome_grib_parsing()` - verify GRIB parsing extracts valid data
  - [ ] 6.4: Create `test_arome_multisite_interpolation()` - verify coordinate extraction
  - [ ] 6.5: Update `smoke_test.py` to verify all horizons collected
  - [ ] 6.6: Update `pytest.ini` to exclude integration tests by default: `addopts = -m "not integration"`

- [ ] Task 7: Update methodology page (AC: 9)
  - [ ] 7.1: Add new section "Forecast Horizons Explained" in locale files (en.json, fr.json)
  - [ ] 7.2: Explain what H+6, H+12, H+24, H+36 means in practical terms
  - [ ] 7.3: Document run schedule: forecasts collected 4x daily (00h, 06h, 12h, 18h UTC)
  - [ ] 7.4: Explain fair comparison: same run time across models for same horizon
  - [ ] 7.5: Add diagram/table showing how horizons map to observations
  - [ ] 7.6: Update About.tsx if needed to display new section

- [ ] Task 8: Verify all ACs (AC: 1-9)
  - [ ] 8.1: Run smoke test: `python -m cli smoke-test`
  - [ ] 8.2: Run integration tests: `pytest -m integration -v`
  - [ ] 8.3: Verify 36 hours of forecasts collected (check DB record count)
  - [ ] 8.4: Verify multi-site efficiency (6 downloads for N sites in logs)
  - [ ] 8.5: Verify fallback triggers on simulated API failure
  - [ ] 8.6: Verify methodology page displays horizon explanation correctly

## Dev Notes

### Critical Technical Details

**Fair Model Comparison - Multi-Run Strategy (CRITICAL)**

To compare forecast accuracy at different horizons (H+6, H+12, H+24, H+36), we MUST collect multiple runs:

**Why single-run doesn't work:**
- If we only collect 21h UTC run, an observation at 8h = horizon H+11 only
- We would NEVER have H+6 or H+24 data points to compare!

**Multi-run collection strategy:**
- Collect forecasts 4x daily: 00h, 06h, 12h, 18h UTC runs
- Each run provides different horizons for the same observation time
- Store `forecast_run` with each forecast record

**Example - How horizons work for observation at 12h:**
```
Observation: 12h Jan 19

To get H+6:  Need run at 06h Jan 19  (12h - 06h = 6h horizon)
To get H+12: Need run at 00h Jan 19  (12h - 00h = 12h horizon)
To get H+24: Need run at 12h Jan 18  (12h + 24h - 12h = 24h horizon)
To get H+36: Need run at 00h Jan 18  (12h + 24h - 00h = 36h horizon)
```

**Fair comparison requires:**
- Both AROME and Meteo-Parapente collected at same run times
- Matching by (observation_time, horizon) across models
- E.g., Compare AROME H+12 vs Meteo-Parapente H+12 for same target observation

**GRIB Time Range Format (Météo-France API)**

The API uses **non-contiguous** time boundaries - this is the root cause of the 404 errors:

| Time Range | Hours Covered | Notes |
|------------|---------------|-------|
| `00H06H` | 0-6 | ✅ Currently works |
| `07H12H` | 7-12 | ❌ Code tried `06H12H` (wrong!) |
| `13H18H` | 13-18 | ❌ Code tried `12H18H` (wrong!) |
| `19H24H` | 19-24 | |
| `25H30H` | 25-30 | |
| `31H36H` | 31-36 | Maximum for 0.025° resolution |

**API Endpoint Pattern:**
```
https://public-api.meteofrance.fr/previnum/DPPaquetAROME/v1/models/AROME/grids/0.025/packages/SP1/productARO
  ?referencetime=2026-01-18T21:00:00Z
  &time=00H06H
  &format=grib2

Headers:
  apikey: {METEOFRANCE_API_TOKEN}  # NOT "Authorization: Bearer"
```

**SP1 Package Contents (surface parameters):**
- `u10`: 10m U wind component (m/s)
- `v10`: 10m V wind component (m/s)
- `t2m`: 2m temperature (Kelvin)

### Code Patterns from Story 6-8

**Storage Service Pattern** (from `storage_service.py`):
```python
async def save_forecasts(db: AsyncSession, forecasts: list[ForecastData]) -> int:
    """Save forecasts to database using INSERT ... ON CONFLICT DO NOTHING."""
    saved = 0
    for f in forecasts:
        stmt = insert(Forecast).values(...).on_conflict_do_nothing()
        result = await db.execute(stmt)
        if result.rowcount > 0:
            saved += 1
    await db.commit()
    return saved
```

**Collector Interface** (from `base.py`):
```python
class BaseCollector(ABC):
    @abstractmethod
    async def collect_forecast(
        self,
        site_id: int,
        forecast_run: datetime,
        **kwargs,
    ) -> list[ForecastData]:
        pass
```

**Retry Decorator** (from `utils.py`):
```python
@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
async def _download_grib2(...) -> bytes:
```

### Multi-Site GRIB Extraction

```python
# Load GRIB once (expensive - 60MB per time range)
grib_bytes = await self._download_grib2(forecast_run, time_range)
datasets = self._parse_grib2_bytes(grib_bytes)  # Returns {wind: Dataset, temp: Dataset}

# Extract for each site (cheap - coordinate lookup)
results: dict[int, list[ForecastData]] = {}
for site in sites:
    site_data = datasets["wind"].interp(
        latitude=site["latitude"],
        longitude=site["longitude"],
        method="linear"
    )
    results[site["id"]] = self._extract_forecasts(site_data, site["id"], ...)

# Close datasets to free memory
for ds in datasets.values():
    ds.close()
```

### Meteociel Scraping Notes

**URL Pattern:**
```
https://www.meteociel.fr/modeles/arome.php?lat=45.916&lon=6.700
```

**Expected HTML Structure (research needed):**
- Temperature table with hourly values
- Wind speed/direction table
- Match horizon columns to forecast hours

**Parser Pattern:**
```python
from bs4 import BeautifulSoup

async def _scrape_arome_forecast(self, lat: float, lon: float) -> list[ForecastData]:
    url = f"https://www.meteociel.fr/modeles/arome.php?lat={lat}&lon={lon}"
    async with HttpClient() as client:
        html = await client.get(url)
    soup = BeautifulSoup(html, 'html.parser')
    # Parse tables...
```

### Project Structure Notes

**Files to Modify:**
- `backend/collectors/arome.py` - Main refactor target
- `backend/services/data_collection.py` - Bulk collection integration (if exists)
- `backend/cli.py` - Add `--horizons`, `--bulk` flags (optional)
- `backend/tests/integration/test_collectors_real.py` - Add AROME integration tests

**Files to Create:**
- `backend/collectors/meteociel.py` - Fallback collector

**Related Files (read-only reference):**
- `backend/collectors/base.py` - BaseCollector interface
- `backend/collectors/meteo_parapente.py` - Multi-source pattern reference
- `backend/collectors/utils.py` - HttpClient, retry decorators
- `backend/core/data_models.py` - ForecastData dataclass
- `backend/services/storage_service.py` - save_forecasts() pattern

### Testing Approach

**Unit Tests (mock GRIB):**
- Mock `_download_grib2()` return value
- Test time range URL building
- Test multi-site data extraction

**Integration Tests (real API):**
```python
@pytest.mark.integration
async def test_arome_all_time_ranges():
    """Verify all 6 time ranges return HTTP 200."""
    collector = AROMECollector()
    for time_range in collector.TIME_RANGES:
        grib_bytes = await collector._download_grib2(
            forecast_run=datetime.now(timezone.utc),
            time_range=time_range,
        )
        assert len(grib_bytes) > 0
```

**Smoke Test CLI:**
```bash
python -m cli smoke-test --verbose
# Should show:
# AROME: 00H06H ✓ (7 forecasts)
# AROME: 07H12H ✓ (6 forecasts)
# ...
# AROME: 31H36H ✓ (6 forecasts)
# Total: 37 horizons for site Passy Plaine Joux
```

### References

- [Tech-Spec: AROME Multi-Site Optimization](_bmad/docs/wip/tech-spec-arome-multisite.md)
- [Story 6-8: Fix Data Collection Pipeline](_bmad-output/implementation-artifacts/6-8-fix-data-collection-pipeline.md)
- [Source: backend/collectors/arome.py]
- [Source: backend/collectors/base.py]
- [Source: backend/services/storage_service.py]
- [External: data.gouv.fr AROME packages](https://www.data.gouv.fr/en/datasets/paquets-arome-resolution-0-025deg/)
- [External: Architecture-Performance blog](https://www.architecture-performance.fr/ap_blog/fetching-arome-weather-forecasts-and-plotting-temperatures/)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
