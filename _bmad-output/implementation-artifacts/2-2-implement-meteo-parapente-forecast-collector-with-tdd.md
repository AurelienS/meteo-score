# Story 2.2: Implement Meteo-Parapente Forecast Collector with TDD

Status: done

## Story

As a developer,
I want to implement the Meteo-Parapente forecast collector using TDD approach,
So that the system can automatically retrieve forecast data from Meteo-Parapente API with validated parsing logic.

## Acceptance Criteria

1. **AC1: TDD Test Suite** - Unit tests are written FIRST in `backend/tests/test_meteo_parapente_collector.py`:
   - Test parsing valid JSON response from Meteo-Parapente API
   - Test extracting wind speed, wind direction, temperature
   - Test handling missing data fields gracefully
   - Test handling malformed JSON responses
   - Test forecast horizon calculation (H+0, H+6, H+12, etc.)
   - All tests use mocked HTTP responses (NEVER call real API in tests)

2. **AC2: MeteoParapenteCollector Implementation** - Create `backend/collectors/meteo_parapente.py`:
   - Class `MeteoParapenteCollector(BaseCollector)` implementing Strategy pattern
   - Async `collect_forecast(site_id: int, forecast_run: datetime) -> List[ForecastData]`
   - API endpoint: `https://data0.meteo-parapente.com/data.php`
   - Uses `HttpClient` from `collectors/utils.py` for HTTP requests

3. **AC3: JSON Response Parsing** - The collector correctly parses Meteo-Parapente API responses:
   - Extracts wind speed (km/h) from JSON response
   - Extracts wind direction (degrees 0-360) from JSON response
   - Extracts temperature (°C) from JSON response
   - Calculates forecast horizons (0h, 6h, 12h, 18h, 24h, etc.)
   - Maps site coordinates to Meteo-Parapente location format

4. **AC4: Error Handling** - Robust error handling is implemented:
   - HTTP errors return empty list and log warning
   - JSON parsing errors are caught and logged
   - Invalid/missing data values are skipped with warning
   - Uses `@retry_with_backoff` decorator from utils.py (3 attempts max)
   - Respects timeout: 10 seconds per request

5. **AC5: API Constraints Respected** - The collector follows API best practices:
   - Timeout: 10 seconds per request
   - User-Agent header identifies MétéoScore
   - Graceful handling of rate limiting responses

6. **AC6: Test Coverage** - All tests pass with >80% coverage for new code

7. **AC7: Manual Validation** - Manual validation is performed:
   - Collect forecast for Passy site (coordinates: 45.9167, 6.7000)
   - Verify values are reasonable (wind 0-200 km/h, temp -50 to +50°C)
   - Log sample data for human review (Level 1 validation strategy)

## Tasks / Subtasks

- [x] Task 1: Research Meteo-Parapente API response format (AC: 3)
  - [x] 1.1: Analyze API endpoint and request parameters
  - [x] 1.2: Document JSON response structure (fields, types, units)
  - [x] 1.3: Identify how to map site coordinates to API parameters
  - [x] 1.4: Document forecast horizon structure in response

- [x] Task 2: Write TDD test suite FIRST (AC: 1, 6)
  - [x] 2.1: Create `backend/tests/test_meteo_parapente_collector.py`
  - [x] 2.2: Write test fixtures for mock API responses
  - [x] 2.3: Test `collect_forecast()` with valid response
  - [x] 2.4: Test wind speed/direction/temperature extraction
  - [x] 2.5: Test forecast horizon calculation
  - [x] 2.6: Test handling missing fields
  - [x] 2.7: Test handling malformed JSON
  - [x] 2.8: Test HTTP error scenarios (404, 500, timeout)
  - [x] 2.9: Test retry logic integration

- [x] Task 3: Implement MeteoParapenteCollector class (AC: 2, 3)
  - [x] 3.1: Create `backend/collectors/meteo_parapente.py`
  - [x] 3.2: Define `MeteoParapenteCollector(BaseCollector)` class
  - [x] 3.3: Implement `collect_forecast()` async method
  - [x] 3.4: Implement `_build_api_url()` for request URL construction
  - [x] 3.5: Implement `_parse_response()` for JSON parsing
  - [x] 3.6: Implement `_extract_forecast_data()` for data extraction

- [x] Task 4: Implement error handling and retry logic (AC: 4, 5)
  - [x] 4.1: Apply `@retry_with_backoff` decorator
  - [x] 4.2: Handle HTTP errors (4xx, 5xx responses)
  - [x] 4.3: Handle JSON parsing exceptions
  - [x] 4.4: Handle missing/invalid data fields
  - [x] 4.5: Configure timeout and User-Agent header
  - [x] 4.6: Add logging for errors and warnings

- [x] Task 5: Update module exports (AC: 2)
  - [x] 5.1: Update `backend/collectors/__init__.py` with MeteoParapenteCollector export

- [x] Task 6: Run tests and verify coverage (AC: 6)
  - [x] 6.1: Run `pytest backend/tests/test_meteo_parapente_collector.py -v`
  - [x] 6.2: Run coverage report and verify >80%
  - [x] 6.3: Run mypy type check on new files

- [x] Task 7: Manual validation with real API (AC: 7)
  - [x] 7.1: Create test script for manual API call
  - [x] 7.2: Collect forecast for Passy site
  - [x] 7.3: Verify values are within reasonable ranges
  - [x] 7.4: Log sample data for human review

## Dev Notes

### Architecture Context

This is the first real data collector implementation following the Strategy pattern established in Story 2.1. The `MeteoParapenteCollector` extends `BaseCollector` and uses utilities from `collectors/utils.py`.

**Why Meteo-Parapente First:**
- Simplest data source (JSON API vs GRIB2 binary)
- Validates entire collector pipeline before tackling AROME complexity
- Risk mitigation: "Start with Meteo-Parapente (JSON) to validate pipeline before tackling AROME GRIB2"

### API Information

**Endpoint:** `https://data0.meteo-parapente.com/data.php`

**Request Parameters (to research):**
- Latitude/Longitude for site location
- Time range for forecast data
- Specific parameters requested

**Response Format:** JSON containing:
- Hourly forecast data
- Wind speed (km/h)
- Wind direction (degrees)
- Temperature (°C)
- Forecast run time and valid times

### TDD Approach (CRITICAL)

**Red → Green → Refactor:**
1. Write failing tests FIRST (Red)
2. Implement minimum code to pass tests (Green)
3. Refactor for quality while keeping tests green (Refactor)

**Test Structure:**
```python
# backend/tests/test_meteo_parapente_collector.py
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from backend.collectors.meteo_parapente import MeteoParapenteCollector
from backend.core.data_models import ForecastData

# Fixtures for mock responses
@pytest.fixture
def valid_api_response():
    """Mock valid Meteo-Parapente API response."""
    return {
        # Structure based on API research
    }

@pytest.mark.asyncio
async def test_collect_forecast_valid_response(valid_api_response):
    """Test collecting forecast with valid API response."""
    collector = MeteoParapenteCollector()
    # Mock HTTP client
    # Assert ForecastData returned correctly
```

### Code Patterns to Follow

**Collector Implementation:**
```python
# backend/collectors/meteo_parapente.py
from datetime import datetime
from decimal import Decimal
from typing import List
import logging

from backend.collectors.base import BaseCollector
from backend.collectors.utils import HttpClient, retry_with_backoff, CollectorError
from backend.core.data_models import ForecastData

logger = logging.getLogger(__name__)

class MeteoParapenteCollector(BaseCollector):
    """Collector for Meteo-Parapente JSON API.

    Retrieves weather forecast data from Meteo-Parapente API
    and converts it to ForecastData objects for storage.
    """

    name: str = "MeteoParapenteCollector"
    source: str = "Meteo-Parapente"
    API_ENDPOINT: str = "https://data0.meteo-parapente.com/data.php"
    TIMEOUT: float = 10.0

    async def collect_forecast(
        self,
        site_id: int,
        forecast_run: datetime,
    ) -> List[ForecastData]:
        """Collect forecast data from Meteo-Parapente API.

        Args:
            site_id: Database ID of the site.
            forecast_run: Datetime of the forecast model run.

        Returns:
            List of ForecastData objects, empty list on error.
        """
        ...
```

### Existing Code to Use

From Story 2.1:
- `backend/collectors/base.py` - `BaseCollector` ABC
- `backend/collectors/utils.py` - `HttpClient`, `@retry_with_backoff`, `CollectorError`
- `backend/core/data_models.py` - `ForecastData`, `ObservationData`

**Import pattern:**
```python
from backend.collectors.base import BaseCollector
from backend.collectors.utils import (
    HttpClient,
    HttpClientError,
    retry_with_backoff,
    parse_iso_datetime,
)
from backend.core.data_models import ForecastData
```

### Model ID Mapping

The Meteo-Parapente model ID should be retrieved from database:
- Model name: "Meteo-Parapente"
- This was seeded in Story 1.3

For this collector, `model_id` can be passed as parameter or looked up.

### Parameter ID Mapping

Parameters seeded in Story 1.3:
- Wind Speed (parameter_id to be looked up)
- Wind Direction (parameter_id to be looked up)
- Temperature (parameter_id to be looked up)

### Data Validation Rules

From NFR4 (6-Level Validation Strategy):
- Wind speed: 0-200 km/h (values outside flagged as aberrant)
- Wind direction: 0-360 degrees
- Temperature: -50 to +50°C (values outside flagged as aberrant)

```python
def _validate_value(self, parameter: str, value: Decimal) -> bool:
    """Validate if value is within expected range."""
    ranges = {
        "wind_speed": (Decimal("0"), Decimal("200")),
        "wind_direction": (Decimal("0"), Decimal("360")),
        "temperature": (Decimal("-50"), Decimal("50")),
    }
    min_val, max_val = ranges.get(parameter, (None, None))
    if min_val is not None and max_val is not None:
        return min_val <= value <= max_val
    return True
```

### Passy Site Coordinates

For manual validation testing:
- Site: Passy Plaine Joux
- Latitude: 45.9167
- Longitude: 6.7000
- Altitude: ~1360m

### File Structure

```
backend/
├── collectors/
│   ├── __init__.py          (update with export)
│   ├── base.py              (exists - from 2.1)
│   ├── utils.py             (exists - from 2.1)
│   └── meteo_parapente.py   ← NEW
└── tests/
    ├── test_base_collector.py  (exists - from 2.1)
    └── test_meteo_parapente_collector.py  ← NEW
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2]
- [Source: _bmad-output/planning-artifacts/architecture-meteo-score-2026-01-10.md#External Integrations]
- [Source: _bmad-output/project-context.md#TDD Approach]
- [Source: backend/collectors/base.py - BaseCollector interface]
- [Source: backend/collectors/utils.py - HttpClient, retry decorator]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- **TDD Approach**: 37 tests written FIRST before implementation (Red → Green → Refactor)
- **Test Coverage**: 90.50% total coverage, 86% coverage for meteo_parapente.py (122 statements)
- **Total Tests**: 164 tests passing across entire backend test suite
- **API Research**: Discovered `plot=sounding` parameter provides temperature (tc) + wind components (umet/vmet)
- **Wind Calculations**:
  - Speed: `sqrt(u² + v²) * 3.6` (m/s to km/h)
  - Direction: `atan2(-u, -v)` (meteorological convention - where wind comes FROM)
- **Manual Validation**: Successfully retrieved 105 ForecastData objects from Passy site
  - Wind Speed: 0.5 - 12.1 km/h (within 0-200 range)
  - Temperature: -0.7 to 3.1°C (within -50 to +50 range)
  - Wind Direction: 12 - 347° (within 0-360 range)
- **Required Headers**: origin, referer, user-agent, accept, x-auth (empty) for API authentication

### File List

**New Files:**
- `backend/collectors/meteo_parapente.py` - MeteoParapenteCollector implementation (506 lines)
- `backend/tests/test_meteo_parapente_collector.py` - TDD test suite (37 tests)

**Modified Files:**
- `backend/collectors/__init__.py` - Add MeteoParapenteCollector export

## Change Log

- 2026-01-11: Story created from epics, ready for development
- 2026-01-11: Implementation completed - all tests pass, manual validation successful
