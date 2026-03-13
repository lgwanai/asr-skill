# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-13)

**Core value:** 在保障数据隐私（本地化处理）的前提下，实现对超长音频/视频的高精度转写，并通过说话人分离技术输出结构化的智能纪要。
**Current focus:** Phase 3: Enhanced Outputs

## Current Position

Phase: 3 of 5 (Enhanced Outputs)
Plan: 1 of 3 in current phase
Status: In Progress
Last activity: 2026-03-14 — Completed 03-01: Output formatters (SRT, ASS, Markdown)

Progress: [=====-----] 44%

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: 2.0 min
- Total execution time: 0.3 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-core-asr-pipeline | 4 | 4 | 2.0 min |
| 02-speaker-diarization | 4 | 4 | 2.0 min |
| 03-enhanced-outputs | 1 | 3 | 3.0 min |

**Recent Trend:**
- Last 5 plans: 2.0 min, 2.0 min, 2.0 min, 4.0 min, 3.0 min
- Trend: Stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

1. MPS detection prioritized over CUDA for Apple Silicon support
2. GPU fallback detection checks for hardware presence vs availability
3. SRT-style HH:MM:SS.mmm timestamp format for all output
4. Chinese text preserved in JSON with ensure_ascii=False
5. Default confidence value 1.0 when model doesn't provide
6. Project-local ./models directory for model caching
7. disable_update=True flag to prevent GPU fallback bug in FunASR
8. batch_size_s=300 for long audio memory management
9. Short flags only (-o, -f) for CLI options
10. Color-coded output via rich (red/yellow/green)
11. FFmpeg CLI via subprocess for video audio extraction
12. Context manager pattern for guaranteed temp file cleanup
13. imageio-ffmpeg fallback for automatic FFmpeg installation
14. Speaker diarization enabled by default (diarize=True)
15. spk_mode="punc_segment" for optimal speaker segmentation
16. Time-based overlap detection with 50% threshold as fallback
17. preprocess_input context manager for unified audio/video handling
18. diarize parameter exposed in transcribe() API with True default
19. SRT timestamp uses comma separator (HH:MM:SS,mmm) per SRT spec
20. ASS timestamp uses centiseconds (H:MM:SS.cc) with non-zero-padded hours
21. ASS speaker colors: Yellow, Cyan, Magenta, Green, Orange for high contrast
22. Markdown groups segments by speaker, ordered by first appearance

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-03-14
Stopped at: Completed 03-01-PLAN.md (Output formatters)
Resume file: .planning/phases/03-enhanced-outputs/03-02-PLAN.md
Next phase: 03-enhanced-outputs (continue execution)

---
*State initialized: 2026-03-13*
