---
phase: 01-core-asr-pipeline
plan: 03
subsystem: core
tags: [funasr, pipeline, model-loading, python-api]
requires:
  - 01-PLAN (device detection)
  - 02-PLAN (output formatters)
provides:
  - FunASR model loading with VAD+ASR+Punctuation composition
  - Main transcription pipeline function
  - Python API entry point
affects:
  - asr_skill/core/models.py
  - asr_skill/core/pipeline.py
  - asr_skill/__init__.py
tech-stack:
  added:
    - funasr==1.3.1
    - torchaudio
  patterns:
    - AutoModel composition pattern
    - Explicit device setting pattern
key-files:
  created:
    - asr_skill/core/models.py
    - asr_skill/core/pipeline.py
  modified:
    - asr_skill/__init__.py
decisions:
  - Use project-local ./models directory for model caching
  - disable_update=True to prevent GPU fallback bug
  - batch_size_s=300 for long audio handling
  - max_single_segment_time=30000 for VAD segmentation
metrics:
  duration: 4 min
  tasks: 3
  files: 3
  completed_date: 2026-03-14
---

# Phase 1 Plan 3: Model Pipeline Summary

## One-Liner

FunASR AutoModel pipeline with VAD+ASR+Punctuation composition and explicit device management to prevent GPU-to-CPU fallback bug.

## What Was Done

Created the core FunASR model pipeline integrating VAD (Voice Activity Detection), ASR (Automatic Speech Recognition), and Punctuation models with automatic model download, hardware-adaptive execution, and proper error handling.

### Task 1: Model Loading Module

Created `asr_skill/core/models.py` with:
- `MODEL_DIR = "./models"` for project-local model caching
- `create_pipeline(device, model_dir)` function that creates FunASR AutoModel with:
  - Paraformer-Large ASR model
  - FSMN-VAD for long audio segmentation
  - CT-Transformer for punctuation
  - `disable_update=True` flag to prevent kwargs mutation bug
  - `vad_kwargs={"max_single_segment_time": 30000}` for memory management

### Task 2: Transcription Pipeline

Created `asr_skill/core/pipeline.py` with:
- `transcribe(model, audio_path, device)` function that:
  - Runs model.generate() with explicit device parameter
  - Uses `batch_size_s=300` for long audio handling
  - Provides clear error messages for CUDA OOM and other errors

### Task 3: Python API Entry Point

Updated `asr_skill/__init__.py` with:
- Complete `transcribe(input_file, output_dir, format)` function integrating all components
- Exports `transcribe` and `SUPPORTED_FORMATS` via `__all__`
- Comprehensive package-level docstring with quick start guide
- Returns dict with text, segments, and output_path

## Key Decisions

1. **Project-local model cache**: `./models` directory per locked decision in CONTEXT.md
2. **disable_update=True**: Critical flag to prevent GPU-to-CPU fallback bug (Pitfall 1 from research)
3. **Explicit device on every generate()**: Prevents silent fallback to CPU
4. **batch_size_s=300**: Handles long audio (>1 hour) without memory explosion

## Files Created/Modified

| File | Status | Description |
|------|--------|-------------|
| `asr_skill/core/models.py` | Created | FunASR model loading with VAD+ASR+PUNC composition |
| `asr_skill/core/pipeline.py` | Created | Main transcription pipeline function |
| `asr_skill/__init__.py` | Modified | Python API entry point with full integration |

## Commits

| Commit | Message |
|--------|---------|
| b196e44 | feat(01-03): create model loading module |
| ab35885 | feat(01-03): create transcription pipeline module |
| 3ce4448 | feat(01-03): create Python API entry point |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing funasr and torchaudio dependencies**
- **Found during:** Task 1 verification
- **Issue:** funasr and torchaudio modules were not installed
- **Fix:** Installed funasr==1.3.1 and torchaudio via pip
- **Files modified:** None (environment only)
- **Commit:** N/A (environment setup)

## Success Criteria Verification

- [x] FunASR models auto-download to ./models on first use (model_hub parameter set)
- [x] VAD+ASR+Punctuation pipeline composition works (AutoModel with all three models)
- [x] Python API provides single `transcribe()` function
- [x] Device is passed explicitly to prevent GPU fallback bug
- [x] Long audio handled with batch_size_s=300

## Self-Check: PASSED

All files exist and imports verified:
- `asr_skill/core/models.py` - EXISTS
- `asr_skill/core/pipeline.py` - EXISTS
- `asr_skill/__init__.py` - EXISTS
- All commits present in git log

---

*Completed: 2026-03-14*
*Duration: 4 minutes*
