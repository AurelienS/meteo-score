# Story 3.5: Minimum Data Threshold Logic

Status: done

## Story

As a user,
I want to see data confidence indicators based on sample size,
So that I know when accuracy metrics are reliable vs. preliminary.

## Acceptance Criteria

1. **AC1: Confidence Level Enum** - Create `ConfidenceLevel` enum with values: `INSUFFICIENT`, `PRELIMINARY`, `VALIDATED`
2. **AC2: Confidence Thresholds** - Implement threshold logic:
   - < 30 days: `insufficient` (red badge)
   - 30-89 days: `preliminary` (orange badge)
   - >= 90 days: `validated` (green badge)
3. **AC3: Confidence Metadata** - Create `ConfidenceMetadata` dataclass with level, sample_size, days_of_data, label, ui_color, show_warning
4. **AC4: Evaluate Confidence** - Implement `evaluate_confidence(sample_size, earliest_timestamp, latest_timestamp)` method
5. **AC5: Warning Messages** - Implement `get_confidence_message(metadata)` with contextual messages for each level
6. **AC6: Test Coverage** - Unit tests cover all boundary cases (29, 30, 89, 90 days)
7. **AC7: Export Service** - ConfidenceService and related types exported from services module

## Tasks / Subtasks

- [x] Task 1: Create ConfidenceLevel enum and ConfidenceMetadata dataclass
  - [x] 1.1: Create `backend/services/confidence_service.py`
  - [x] 1.2: Define `ConfidenceLevel` as str Enum with INSUFFICIENT, PRELIMINARY, VALIDATED
  - [x] 1.3: Define `ConfidenceMetadata` dataclass with all required fields

- [x] Task 2: Write TDD tests FIRST
  - [x] 2.1: Create `backend/tests/test_confidence_service.py`
  - [x] 2.2: Test 29 days returns INSUFFICIENT
  - [x] 2.3: Test 30 days returns PRELIMINARY
  - [x] 2.4: Test 89 days returns PRELIMINARY
  - [x] 2.5: Test 90 days returns VALIDATED
  - [x] 2.6: Test warning message generation for each level
  - [x] 2.7: Test edge cases (0 days, negative, large values)

- [x] Task 3: Implement ConfidenceService
  - [x] 3.1: Define class constants PRELIMINARY_THRESHOLD = 30, VALIDATED_THRESHOLD = 90
  - [x] 3.2: Implement `evaluate_confidence()` method
  - [x] 3.3: Implement `get_confidence_message()` method
  - [x] 3.4: Implement `get_confidence_with_metrics()` combining confidence and metrics

- [x] Task 4: Integration and verification
  - [x] 4.1: Run `pytest tests/test_confidence_service.py -v`
  - [x] 4.2: Update `services/__init__.py` to export ConfidenceService, ConfidenceLevel, ConfidenceMetadata
  - [x] 4.3: Verify all tests pass

## Dev Notes

### Confidence Level Rules

| Sample Size | Confidence Level | Label | UI Indicator |
|-------------|------------------|-------|--------------|
| < 30 days | `insufficient` | Insufficient Data | Red badge |
| 30-89 days | `preliminary` | Preliminary | Orange badge |
| >= 90 days | `validated` | Validated | Green badge |

### Implementation Pattern (from epics)

```python
# backend/services/confidence_service.py
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

class ConfidenceLevel(str, Enum):
    INSUFFICIENT = 'insufficient'
    PRELIMINARY = 'preliminary'
    VALIDATED = 'validated'

@dataclass
class ConfidenceMetadata:
    level: ConfidenceLevel
    sample_size: int
    days_of_data: int
    label: str
    ui_color: str
    show_warning: bool

class ConfidenceService:
    PRELIMINARY_THRESHOLD = 30  # days
    VALIDATED_THRESHOLD = 90    # days

    def evaluate_confidence(
        self,
        sample_size: int,
        earliest_timestamp: datetime,
        latest_timestamp: datetime
    ) -> ConfidenceMetadata:
        """Evaluate data confidence based on sample size and time range."""
        days_of_data = (latest_timestamp - earliest_timestamp).days
        # ... threshold logic
```

### Warning Message Examples

- **Insufficient:** "Insufficient data (15 days). Collect 15 more days to reach preliminary status."
- **Preliminary:** "Results based on 45 days of data. Metrics will stabilize after 45 more days."
- **Validated:** "Validated with 120 days of data. These metrics are statistically reliable."

### Project Structure Notes

**New file to create:**
- `backend/services/confidence_service.py`
- `backend/tests/test_confidence_service.py`

**File to modify:**
- `backend/services/__init__.py` - Export ConfidenceService, ConfidenceLevel, ConfidenceMetadata

### Previous Story Intelligence (3-4)

From story 3-4 TimescaleDB Continuous Aggregates:
- Service pattern established in `backend/services/`
- Dataclass pattern used for AggregateMetrics
- Tests use mock sessions for database-independent testing
- Export pattern in `services/__init__.py`

### Testing Considerations

- No database required for ConfidenceService (pure logic)
- Use datetime objects for timestamp calculations
- Test boundary cases exactly (29, 30, 89, 90 days)
- Test edge cases (0 days, same timestamp)

### References

- [Epic 3 Definition: _bmad-output/planning-artifacts/epics.md#Story-3.5]
- [Project Context: _bmad-output/project-context.md]
- [Previous Story 3-4: _bmad-output/implementation-artifacts/3-4-timescaledb-continuous-aggregates.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Completion Notes

- Implemented ConfidenceLevel enum with INSUFFICIENT, PRELIMINARY, VALIDATED values
- Created ConfidenceMetadata dataclass with all required fields (level, sample_size, days_of_data, label, ui_color, show_warning)
- Implemented ConfidenceService with threshold constants (30 days for preliminary, 90 days for validated)
- evaluate_confidence() calculates days from timestamp range and returns appropriate metadata
- get_confidence_message() generates contextual user-friendly messages
- 23 comprehensive tests covering all boundary cases (29, 30, 89, 90 days) and edge cases
- All tests pass

### File List

- `backend/services/confidence_service.py` (new)
- `backend/tests/test_confidence_service.py` (new)
- `backend/services/__init__.py` (modified - added exports)

## Change Log

- 2026-01-15: Story created with comprehensive context for confidence threshold implementation
- 2026-01-15: Implementation complete - ConfidenceService with 23 passing tests
