---
phase: 03-enhanced-outputs
plan: 02
subsystem: api
tags: [progress, callback, json, timestamps, word-level, rich]

# Dependency graph
requires:
  - phase: 03-01
    provides: Output formatters infrastructure (format_json, format_txt)
provides:
  - Progress callback integration with FunASR for real-time transcription progress
  - Visual progress bar in CLI using rich Progress
  - Word-level timestamps and confidence in JSON output
affects: [cli, api, json-output]

# Tech tracking
tech-stack:
  added: []
  patterns: [progress-callback, word-level-timestamps]

key-files:
  created: []
  modified:
    - asr_skill/core/pipeline.py
    - asr_skill/__init__.py
    - asr_skill/cli.py
    - asr_skill/postprocessing/formatters.py

key-decisions:
  - "Progress callback passed to FunASR generate() as 'callback' parameter"
  - "Segment confidence used for word-level confidence (FunASR limitation)"
  - "Callable type from typing module for Python 3.10+ compatibility"

patterns-established:
  - "Progress callback pattern: callable with (current: int, total: int) signature"
  - "Word-level data extracted from FunASR timestamp format: [[word, start_ms, end_ms], ...]"

requirements-completed: [AUDIO-05, TRAN-04]

# Metrics
duration: 3min
completed: 2026-03-14
---

# Phase 3 Plan 02: Progress and Word-level Output Summary

**Progress callback integration with FunASR and word-level timestamps in JSON output, enabling real-time CLI progress display and detailed transcription analytics**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T17:24:39Z
- **Completed:** 2026-03-13T17:27:35Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Progress callback parameter added to pipeline transcribe() function and passed through to FunASR generate()
- Rich Progress bar integration in CLI showing percentage and time remaining during transcription
- Word-level timestamps and confidence scores extracted from FunASR output and included in JSON format

## Task Commits

Each task was committed atomically:

1. **Task 1: Add progress callback to pipeline** - `b76f3a0` (feat)
2. **Task 2: Add progress display to CLI** - `fcc6bed` (feat)
3. **Task 3: Add word-level timestamps to JSON output** - `5d7293e` (feat)

**Plan metadata:** (pending)

_Note: TDD tasks may have multiple commits (test -> feat -> refactor)_

## Files Created/Modified

- `asr_skill/core/pipeline.py` - Added progress_callback parameter to transcribe() function
- `asr_skill/__init__.py` - Added progress_callback parameter to API transcribe() function
- `asr_skill/cli.py` - Added rich Progress bar for transcription progress display
- `asr_skill/postprocessing/formatters.py` - Extended format_json() to include word-level timestamps

## Decisions Made

- Used `Callable` from typing module instead of builtin `callable` for type annotation compatibility with Python 3.10+ union syntax
- Progress callback passed as `callback` keyword argument to FunASR generate() method
- Word-level confidence uses segment confidence since FunASR does not provide per-word confidence scores
- Progress bar only updates when total > 0 (valid progress data from FunASR)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Type annotation `callable | None` caused TypeError in Python 3.10 - resolved by using `Callable[[int, int], None] | None` from typing module

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Progress indication and word-level output complete
- Ready for next plan in enhanced-outputs phase

---
*Phase: 03-enhanced-outputs*
*Completed: 2026-03-14*
