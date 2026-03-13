# Phase 1: Core ASR Pipeline - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can transcribe audio files (MP3, WAV, M4A, FLAC) to text with automatic hardware detection. Output is TXT and JSON files in the same directory as input. This phase delivers the core transcription pipeline — no speaker diarization, no video input, no advanced output formats.

</domain>

<decisions>
## Implementation Decisions

### Invocation style
- CLI-only invocation with minimal required input (just file path)
- Everything else auto-detected: hardware, output format, output location
- Short flags only for optional parameters: `-o` (output), `-f` (format)
- Python API: single function `transcribe("audio.mp3")` returning dict
- No config file required for v1 — keep it simple

### Output structure
- TXT format: timestamps inline `[00:00:00.000] text`
- JSON format: segment level (array of segments with text, start, end, confidence)
- Timestamp format: standard SRT style `HH:MM:SS.mmm`
- Output filenames: same basename as input (`audio.mp3` → `audio.txt`, `audio.json`)

### Error handling
- Primary strategy: fail fast with clear error messages
- GPU-to-CPU fallback: auto-fallback with warning message
- Corrupted audio: fail entire file (no graceful degradation for v1)
- Error reporting: console output to stderr with color coding

### Model management
- Cache location: project-local `./models/` directory
- First-run: auto-download models with progress bar (no prompt)
- Version management: pinned versions from research (funasr==1.3.1)
- Cleanup: keep all downloaded models (no auto-cleanup)

### Claude's Discretion
- Exact error message wording and format
- Progress bar implementation style
- Color scheme for console output
- Specific retry behavior for recoverable errors (if any)

</decisions>

<specifics>
## Specific Ideas

- "Just give me the file path and I'll handle the rest" — minimal friction philosophy
- Output should be immediately usable without post-processing
- Clear error messages that tell users exactly what went wrong

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-core-asr-pipeline*
*Context gathered: 2026-03-13*
