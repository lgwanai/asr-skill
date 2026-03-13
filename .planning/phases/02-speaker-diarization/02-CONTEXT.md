# Phase 2: Speaker Diarization - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can identify and distinguish multiple speakers in transcribed audio. This phase adds speaker diarization to the existing transcription pipeline, including video file input support. Output now includes speaker labels and overlap detection.

</domain>

<decisions>
## Implementation Decisions

### Speaker labeling
- Label format: Alphabetical (Speaker A, Speaker B, Speaker C)
- TXT output: Speaker prefix per line — `[00:00:00] Speaker A: Hello world`
- JSON output: Segment-level `speaker_id` field
- No customization for v1 — fixed Speaker A/B/C labels

### Overlap handling
- TXT output: Explicit `[OVERLAP]` tag before overlapping segments
- JSON output: `is_overlap: true` boolean flag on segment
- Detection: Hybrid approach — model-based if available, fallback to time-based (>50% overlap)
- Timestamps: Per-segment ranges (start/end times per speaker segment)

### Diarization toggle
- Default: Always on — diarization runs for all transcriptions
- Performance: Show progress indicator during diarization processing
- Python API: Optional `diarize=True` parameter (default True)
- Minimum audio length: No minimum — run on any audio length

### Video extraction
- Extraction method: FFmpeg CLI (command-line tool)
- Temp files: Auto-delete extracted audio after transcription completes
- FFmpeg dependency: Auto-install via imageio-ffmpeg if missing
- Supported formats: MP4, AVI, MKV only (most common)

### Claude's Discretion
- Exact progress indicator implementation
- Temp file naming convention
- Error message wording for ffmpeg failures
- Overlap threshold fine-tuning (default 50%)

</decisions>

<specifics>
## Specific Ideas

- "I want to see at a glance who said what" — speaker prefix format
- Overlaps should be clearly marked, not silently merged
- Video support should feel seamless — just pass any file

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-speaker-diarization*
*Context gathered: 2026-03-14*
