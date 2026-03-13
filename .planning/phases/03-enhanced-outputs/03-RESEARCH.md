# Phase 3: Enhanced Outputs - Research

**Researched:** 2026-03-14
**Domain:** Subtitle formats (SRT, ASS), progress callbacks, confidence scoring
**Confidence:** HIGH

## Summary

This phase adds three new output formats (SRT, ASS, Markdown) and two enhancements to existing functionality (progress indication, per-word confidence scores). The research reveals that FunASR already provides the necessary data structures for all requirements:

1. **SRT format**: Straightforward mapping from existing `sentence_info` segments with SRT-style timestamp formatting (already implemented in `format_timestamp`)
2. **ASS format**: Requires ASS header with style definitions, then dialogue lines with speaker-specific styling
3. **Markdown format**: Simple text transformation with speaker sections
4. **Progress indication**: FunASR's `generate()` method accepts a `progress_callback` parameter
5. **Confidence scores**: FunASR provides word-level timestamps via `timestamp` field; confidence is available at segment level (default 1.0 when not provided by model)

**Primary recommendation:** Extend the existing `formatters.py` module with three new format functions, add a progress callback wrapper in the pipeline, and include the `timestamp` field in JSON output for word-level data.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUDIO-05 | System provides progress indication during processing | FunASR `generate()` accepts `progress_callback(current, total)` - see line 321, 401-405 in auto_model.py |
| TRAN-04 | System provides per-word confidence scores in output | FunASR provides `timestamp` field with word-level timestamps per segment. Segment confidence available; word-level confidence may need approximation or use segment confidence |
| OUTP-02 | User can export as SRT subtitle format with timestamps | SRT format: index, timestamp line (`HH:MM:SS,mmm --> HH:MM:SS,mmm`), text, blank line. Map from `sentence_info` segments |
| OUTP-03 | User can export as ASS subtitle format with speaker styling | ASS format: header section with styles, dialogue lines with speaker-specific styles. Define styles per speaker (colors, positioning) |
| OUTP-05 | User can export as Markdown with speaker sections | Group segments by speaker, create headers (`## Speaker A`), list segments with optional timestamps |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rich | ^13.0 | Progress display and CLI output | Already used in CLI, provides Progress/Task APIs |
| funasr | ^1.0 | ASR model with progress_callback | Native support for progress callbacks |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing | stdlib | Type hints for formatters | All formatter functions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| rich.Progress | tqdm | tqdm is simpler but rich provides better CLI integration (already used) |
| Custom ASS parser | pysubs2 | pysubs2 adds dependency for simple format generation - not worth it |

## Architecture Patterns

### Recommended Project Structure
```
asr_skill/
├── postprocessing/
│   ├── formatters.py      # Existing: format_txt, format_json
│   ├── formatters_srt.py  # NEW: format_srt
│   ├── formatters_ass.py  # NEW: format_ass
│   └── formatters_md.py   # NEW: format_markdown
├── core/
│   └── pipeline.py        # MODIFY: add progress_callback support
└── cli.py                 # MODIFY: add format choices
```

### Pattern 1: Formatter Function Signature
**What:** All formatters follow the same signature: `def format_X(result: dict[str, Any]) -> str`
**When to use:** When adding new output formats
**Example:**
```python
# Existing pattern from formatters.py
def format_txt(result: dict[str, Any]) -> str:
    segments = result.get("sentence_info") or result.get("sentences", [])
    # ... formatting logic
    return "\n".join(lines)
```

### Pattern 2: Progress Callback Integration
**What:** Wrap FunASR's progress_callback with rich Progress display
**When to use:** When implementing AUDIO-05 progress indication
**Example:**
```python
# FunASR generate() signature (from auto_model.py:321)
def generate(self, input, input_len=None, progress_callback=None, **cfg):
    # ...
    if progress_callback:
        progress_callback(end_idx, num_samples)  # line 403

# Integration pattern
from rich.progress import Progress, TaskID

def create_progress_callback(progress: Progress, task_id: TaskID):
    def callback(current: int, total: int):
        progress.update(task_id, completed=current, total=total)
    return callback
```

### Anti-Patterns to Avoid
- **Don't duplicate timestamp formatting**: Use existing `format_timestamp()` function
- **Don't ignore speaker labels**: All new formats should include speaker information when available
- **Don't block the main thread**: Progress callbacks should be lightweight

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress display | Custom progress bar | rich.Progress | Already in project, thread-safe, beautiful output |
| Timestamp formatting | Custom time conversion | format_timestamp() | Already implemented, SRT-compatible format |
| Speaker label formatting | Custom label logic | format_speaker_label() | Already implemented with alphabetical mapping |

**Key insight:** The project already has good foundations. The phase is primarily about adding format converters, not building new infrastructure.

## Common Pitfalls

### Pitfall 1: SRT Timestamp Format Difference
**What goes wrong:** SRT uses comma for milliseconds (`00:00:00,000`) while the existing format_timestamp uses period (`00:00:00.000`)
**Why it happens:** The existing format was designed for TXT readability, not SRT spec compliance
**How to avoid:** Create `format_srt_timestamp()` that uses comma, or add a parameter to existing function
**Warning signs:** Subtitle players rejecting the SRT file

### Pitfall 2: ASS Speaker Color Assignment
**What goes wrong:** Hardcoding speaker colors leads to poor contrast or duplicate colors
**Why it happens:** Not planning for arbitrary number of speakers
**How to avoid:** Define a color palette array and cycle through it for speakers
**Warning signs:** More than 4-5 speakers with unclear styling

### Pitfall 3: Progress Callback Exception Handling
**What goes wrong:** Exceptions in progress callback crash the transcription
**Why it happens:** FunASR catches exceptions but logs them (see auto_model.py:404-405)
**How to avoid:** Keep callback logic minimal, handle exceptions internally
**Warning signs:** Transcription stops unexpectedly

### Pitfall 4: Word-Level Confidence Not Available
**What goes wrong:** Assuming FunASR provides word-level confidence scores
**Why it happens:** FunASR provides `timestamp` for word-level timing but not confidence per word
**How to avoid:** Use segment-level confidence for all words in segment, or estimate from model scores if available
**Warning signs:** Missing confidence field in output

## Code Examples

### SRT Format Generation
```python
def format_srt_timestamp(ms: int) -> str:
    """Convert milliseconds to SRT timestamp format (comma for milliseconds)."""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

def format_srt(result: dict[str, Any]) -> str:
    """Format transcription result as SRT subtitle format."""
    segments = result.get("sentence_info") or result.get("sentences", [])
    if not segments:
        return ""

    segments = detect_overlaps(segments)
    lines = []

    for i, segment in enumerate(segments, 1):
        start = format_srt_timestamp(segment["start"])
        end = format_srt_timestamp(segment["end"])
        text = segment.get("sentence", segment.get("text", ""))

        # Add speaker prefix if available
        if "spk" in segment:
            speaker = format_speaker_label(segment["spk"])
            text = f"[{speaker}] {text}"

        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")  # Blank line between entries

    return "\n".join(lines)
```

### ASS Format Generation
```python
ASS_HEADER = """[Script Info]
Title: ASR Transcription
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: SpeakerA,Microsoft YaHei,48,&H0000FFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: SpeakerB,Microsoft YaHei,48,&H00FF00FF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: SpeakerC,Microsoft YaHei,48,&H00FFFF00,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def format_ass_timestamp(ms: int) -> str:
    """Convert milliseconds to ASS timestamp format (H:MM:SS.cc)."""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    centis = (ms % 1000) // 10
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centis:02d}"

def format_ass(result: dict[str, Any]) -> str:
    """Format transcription result as ASS subtitle format with speaker styling."""
    segments = result.get("sentence_info") or result.get("sentences", [])
    if not segments:
        return ASS_HEADER

    segments = detect_overlaps(segments)
    lines = [ASS_HEADER]

    for segment in segments:
        start = format_ass_timestamp(segment["start"])
        end = format_ass_timestamp(segment["end"])
        text = segment.get("sentence", segment.get("text", ""))

        # Use speaker-specific style
        if "spk" in segment:
            style = f"Speaker{chr(ord('A') + segment['spk'])}"
        else:
            style = "Default"

        # Escape ASS special characters
        text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")

        lines.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{text}")

    return "\n".join(lines)
```

### Markdown Format Generation
```python
def format_markdown(result: dict[str, Any]) -> str:
    """Format transcription result as Markdown with speaker sections."""
    segments = result.get("sentence_info") or result.get("sentences", [])
    if not segments:
        return "# Transcription\n\n*No content*\n"

    segments = detect_overlaps(segments)

    # Group by speaker
    by_speaker: dict[int, list] = {}
    for seg in segments:
        spk = seg.get("spk", -1)  # -1 for unknown speaker
        if spk not in by_speaker:
            by_speaker[spk] = []
        by_speaker[spk].append(seg)

    lines = ["# Transcription\n"]

    # Sort speakers by first appearance
    speaker_order = []
    seen = set()
    for seg in segments:
        spk = seg.get("spk", -1)
        if spk not in seen:
            speaker_order.append(spk)
            seen.add(spk)

    for spk in speaker_order:
        if spk == -1:
            lines.append("## Unknown Speaker\n")
        else:
            lines.append(f"## {format_speaker_label(spk)}\n")

        for seg in by_speaker[spk]:
            timestamp = format_timestamp(seg["start"])
            text = seg.get("sentence", seg.get("text", ""))
            overlap = " [OVERLAP]" if seg.get("is_overlap") else ""
            lines.append(f"- `[{timestamp}]`{overlap} {text}")

        lines.append("")  # Blank line between speakers

    return "\n".join(lines)
```

### Progress Callback Integration
```python
from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn

def transcribe_with_progress(
    model: Any,
    audio_path: str,
    device: str,
    console: Console
) -> dict[str, Any] | None:
    """Run transcription with progress display."""
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("Transcribing...", total=None)

        def callback(current: int, total: int):
            if total > 0:
                progress.update(task_id, completed=current, total=total)

        result = model.generate(
            input=audio_path,
            batch_size_s=300,
            device=device,
            progress_callback=callback,
        )

    return result[0] if result else None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual timestamp parsing | FunASR provides structured timestamps | FunASR 1.0+ | No need to parse timestamps from text |
| No progress feedback | progress_callback parameter | FunASR 1.3+ | Native progress support in library |
| Single output format | Multiple formatters | Project evolution | Extensible architecture already in place |

**Deprecated/outdated:**
- Parsing timestamps from raw text: FunASR provides structured data
- External progress estimation: Native callback available

## Open Questions

1. **Word-level confidence scores**
   - What we know: FunASR provides `timestamp` field with word-level timing but no explicit confidence per word
   - What's unclear: Whether model outputs confidence scores that can be extracted
   - Recommendation: Use segment-level confidence (already available) for all words in segment, document this limitation

2. **ASS style color palette**
   - What we know: Need colors for speaker differentiation
   - What's unclear: Optimal color palette for accessibility
   - Recommendation: Use high-contrast colors (yellow, cyan, magenta, green, orange) and document limitation for >5 speakers

3. **Progress granularity**
   - What we know: FunASR callback provides (current, total) sample counts
   - What's unclear: Whether this is file-level or batch-level progress
   - Recommendation: Test with long audio to verify granularity, may need to supplement with VAD stage progress

## Sources

### Primary (HIGH confidence)
- FunASR auto_model.py source code (lines 321, 401-405 for progress_callback; lines 635-641 for timestamp_sentence)
- FunASR timestamp_tools.py source code (lines 108-190 for timestamp_sentence structure)
- Existing project formatters.py (established patterns)

### Secondary (MEDIUM confidence)
- SRT format specification (standard subtitle format, well-documented)
- ASS format specification (standard subtitle format, well-documented)

### Tertiary (LOW confidence)
- None - all requirements can be verified from source code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing libraries and patterns
- Architecture: HIGH - Following established project structure
- Pitfalls: HIGH - Based on source code analysis and format specifications

**Research date:** 2026-03-14
**Valid until:** 30 days (stable format specifications, FunASR API unlikely to change significantly)
