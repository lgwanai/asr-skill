# Phase 2: Speaker Diarization - Research

**Researched:** 2026-03-14
**Domain:** Speaker Diarization with FunASR CAM++ Model
**Confidence:** HIGH (FunASR source code analysis, existing project codebase, and project research files)

## Summary

Speaker diarization in FunASR is implemented through the CAM++ model, which extracts speaker embeddings from audio segments and clusters them using spectral clustering or UMAP+HDBSCAN. The implementation is fully integrated into FunASR's AutoModel pipeline, requiring only the `spk_model` parameter to enable. The key insight is that speaker diarization requires timestamp output from the ASR model, which is why Paraformer-Large must be used (SenseVoice is incompatible).

For this phase, we also need to implement video file input support via FFmpeg CLI for audio extraction. The user has decided on FFmpeg CLI with imageio-ffmpeg for auto-installation and automatic temp file cleanup.

**Primary recommendation:** Use FunASR's built-in `spk_model="iic/speech_campplus_sv_zh-cn_16k-common"` with `spk_mode="punc_segment"` for optimal speaker segmentation. Implement video extraction via FFmpeg subprocess with automatic cleanup.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Speaker labeling
- Label format: Alphabetical (Speaker A, Speaker B, Speaker C)
- TXT output: Speaker prefix per line — `[00:00:00] Speaker A: Hello world`
- JSON output: Segment-level `speaker_id` field
- No customization for v1 — fixed Speaker A/B/C labels

#### Overlap handling
- TXT output: Explicit `[OVERLAP]` tag before overlapping segments
- JSON output: `is_overlap: true` boolean flag on segment
- Detection: Hybrid approach — model-based if available, fallback to time-based (>50% overlap)
- Timestamps: Per-segment ranges (start/end times per speaker segment)

#### Diarization toggle
- Default: Always on — diarization runs for all transcriptions
- Performance: Show progress indicator during diarization processing
- Python API: Optional `diarize=True` parameter (default True)
- Minimum audio length: No minimum — run on any audio length

#### Video extraction
- Extraction method: FFmpeg CLI (command-line tool)
- Temp files: Auto-delete extracted audio after transcription completes
- FFmpeg dependency: Auto-install via imageio-ffmpeg if missing
- Supported formats: MP4, AVI, MKV only (most common)

#### Claude's Discretion
- Exact progress indicator implementation
- Temp file naming convention
- Error message wording for ffmpeg failures
- Overlap threshold fine-tuning (default 50%)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUDIO-02 | User can input video files in MP4, AVI, MKV formats with automatic audio extraction | FFmpeg CLI via subprocess module; temp file with auto-cleanup; imageio-ffmpeg for auto-install |
| SPKR-01 | System identifies and labels different speakers (Speaker A, B, C...) | FunASR CAM++ model via `spk_model` parameter; output via `sentence_info` field with `spk` labels |
| SPKR-02 | User receives speaker timestamps (start/end times per speaker) | FunASR `postprocess()` returns `[start_sec, end_sec, speaker_id]` tuples; distributed to segments via `distribute_spk()` |
| SPKR-03 | System marks overlapping speech segments in output | FunASR `is_overlapped()` detection in postprocess; hybrid with time-based fallback (>50% overlap) |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FunASR | 1.3.1 | ASR + Speaker Diarization framework | Built-in CAM++ integration; AutoModel handles pipeline composition |
| PyTorch | 2.9.1+ | Deep learning backend | Required by FunASR; supports CUDA and MPS |
| FFmpeg | 6.0+ | Video audio extraction | Industry standard; CLI access via subprocess |
| imageio-ffmpeg | 0.5.1 | FFmpeg auto-install | Bundles FFmpeg binary; auto-installs if missing |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | 1.16.x | Spectral clustering for speaker embeddings | Required by FunASR ClusterBackend |
| scikit-learn | 1.6.x | K-means and HDBSCAN clustering | Required by FunASR speaker clustering |
| tqdm | 4.67.x | Progress indication | Show diarization progress |

### FunASR Speaker Model

| Model | ModelScope ID | Purpose | Size |
|-------|---------------|---------|------|
| **CAM++** | `iic/speech_campplus_sv_zh-cn_16k-common` | Speaker embedding extraction + clustering | ~300MB |

**Installation:**
```bash
pip install funasr==1.3.1
pip install imageio-ffmpeg  # Auto-installs FFmpeg binary
```

## Architecture Patterns

### Recommended Project Structure (Updates)

```
asr_skill/
├── core/
│   ├── __init__.py
│   ├── device.py          # Hardware detection (existing)
│   ├── models.py          # Model loading (UPDATE: add spk_model)
│   └── pipeline.py        # Transcription pipeline (UPDATE: handle speaker output)
├── preprocessing/
│   ├── __init__.py
│   ├── audio.py           # Audio preprocessing (existing)
│   └── video.py           # NEW: Video audio extraction via FFmpeg
├── postprocessing/
│   ├── __init__.py
│   ├── formatters.py      # Output formatters (UPDATE: add speaker labels)
│   └── speakers.py        # NEW: Speaker label processing
└── utils/
    └── paths.py           # Path handling (existing)
```

### Pattern 1: FunASR Speaker Diarization Pipeline

**What:** Enable speaker diarization by adding `spk_model` parameter to AutoModel initialization.

**When to use:** Always for Phase 2 — diarization is always on by default.

**Example:**
```python
from funasr import AutoModel

model = AutoModel(
    model="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    punc_model="iic/punc_ct-transformer_cn-en-common-vocab471067-large",
    spk_model="iic/speech_campplus_sv_zh-cn_16k-common",  # ADD THIS
    spk_mode="punc_segment",  # Use punctuation segments for speaker assignment
    device=device,
    disable_update=True,
    vad_kwargs={"max_single_segment_time": 30000},
)

result = model.generate(input=audio_path, batch_size_s=300, device=device)

# Result structure includes sentence_info with speaker labels:
# result[0]["sentence_info"] = [
#     {"start": 0, "end": 2500, "sentence": "Hello world.", "spk": 0},
#     {"start": 3000, "end": 5500, "sentence": "Good morning.", "spk": 1},
# ]
```

**Source:** FunASR auto_model.py lines 159-186, 592-642

### Pattern 2: Video Audio Extraction via FFmpeg

**What:** Extract audio from video files using FFmpeg CLI via subprocess module.

**When to use:** When input file is MP4, AVI, or MKV format.

**Example:**
```python
import subprocess
import tempfile
import os

SUPPORTED_VIDEO_FORMATS = [".mp4", ".avi", ".mkv"]

def extract_audio_from_video(video_path: str) -> str:
    """Extract audio from video file using FFmpeg.

    Args:
        video_path: Path to video file (MP4, AVI, MKV)

    Returns:
        Path to extracted audio WAV file (16kHz mono)

    Raises:
        RuntimeError: If FFmpeg extraction fails
    """
    # Create temp file for audio output
    temp_audio = tempfile.mktemp(suffix=".wav")

    # FFmpeg command: extract audio, convert to 16kHz mono WAV
    cmd = [
        "ffmpeg",
        "-i", video_path,           # Input video file
        "-vn",                       # No video output
        "-acodec", "pcm_s16le",     # 16-bit PCM codec
        "-ar", "16000",             # 16kHz sample rate
        "-ac", "1",                 # Mono channel
        "-y",                       # Overwrite output
        temp_audio
    ]

    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        return temp_audio
    except subprocess.CalledProcessError as e:
        os.remove(temp_audio) if os.path.exists(temp_audio) else None
        raise RuntimeError(f"FFmpeg audio extraction failed: {e.stderr}")
```

### Pattern 3: Speaker Label Formatting

**What:** Convert numeric speaker IDs to alphabetical labels (Speaker A, B, C...).

**When to use:** When formatting output for user display.

**Example:**
```python
def format_speaker_label(speaker_id: int) -> str:
    """Convert numeric speaker ID to alphabetical label.

    Args:
        speaker_id: Numeric speaker ID from diarization (0, 1, 2, ...)

    Returns:
        Alphabetical label: "Speaker A", "Speaker B", etc.

    Example:
        >>> format_speaker_label(0)
        'Speaker A'
        >>> format_speaker_label(2)
        'Speaker C'
    """
    return f"Speaker {chr(ord('A') + speaker_id)}"


def format_txt_with_speakers(result: dict) -> str:
    """Format transcription with speaker labels.

    Output format: [HH:MM:SS.mmm] Speaker A: Transcribed text
    """
    lines = []
    for segment in result.get("sentence_info", []):
        timestamp = format_timestamp(segment["start"])
        speaker = format_speaker_label(segment["spk"])
        text = segment["sentence"]

        # Check for overlap (to be implemented in Phase 2)
        overlap_tag = "[OVERLAP] " if segment.get("is_overlap", False) else ""

        lines.append(f"[{timestamp}] {overlap_tag}{speaker}: {text}")

    return "\n".join(lines)
```

### Pattern 4: Overlap Detection

**What:** Detect overlapping speech segments using time-based comparison.

**When to use:** Post-processing to mark overlapping segments.

**Example:**
```python
def detect_overlaps(sentence_info: list, threshold: float = 0.5) -> list:
    """Mark overlapping segments based on time overlap.

    Args:
        sentence_info: List of segment dicts with start, end, spk fields
        threshold: Overlap ratio threshold (default 0.5 = 50%)

    Returns:
        sentence_info with is_overlap field added
    """
    for i, seg in enumerate(sentence_info):
        seg["is_overlap"] = False

        for j, other in enumerate(sentence_info):
            if i == j or seg["spk"] == other["spk"]:
                continue

            # Calculate overlap
            overlap_start = max(seg["start"], other["start"])
            overlap_end = min(seg["end"], other["end"])
            overlap_duration = max(0, overlap_end - overlap_start)

            if overlap_duration > 0:
                seg_duration = seg["end"] - seg["start"]
                overlap_ratio = overlap_duration / seg_duration

                if overlap_ratio >= threshold * 1000:  # Convert to ms
                    seg["is_overlap"] = True
                    break

    return sentence_info
```

**Note:** FunASR's built-in overlap detection (in `postprocess()`) distributes overlap regions by splitting at midpoint. For explicit `[OVERLAP]` tagging, we need post-processing.

### Anti-Patterns to Avoid

- **Using SenseVoice with CAM++:** SenseVoice doesn't output timestamps, causing "can not get `timestamp`" error
- **Skipping VAD with speaker model:** VAD is required for speaker diarization to work
- **Not passing device explicitly:** Causes GPU-to-CPU fallback on subsequent runs
- **Leaking temp files:** Must cleanup extracted audio after transcription completes
- **Assuming speaker IDs are consecutive:** Use `correct_labels()` pattern from FunASR

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Speaker embedding extraction | Custom neural network | FunASR CAM++ model | Trained on large dataset; handles edge cases |
| Speaker clustering | Custom K-means | FunASR ClusterBackend | Spectral clustering + UMAP+HDBSCAN for different scales |
| Audio extraction from video | Custom FFmpeg bindings | FFmpeg CLI via subprocess | Proven reliability; handles all edge cases |
| FFmpeg installation | Manual download | imageio-ffmpeg | Auto-downloads platform-specific binary |
| Overlap detection (model-based) | Custom overlap model | FunASR postprocess() | Built-in midpoint splitting logic |

**Key insight:** FunASR's CAM++ integration is mature and well-tested. Custom implementations would require significant effort and likely introduce bugs.

## Common Pitfalls

### Pitfall 1: Speaker Model Incompatibility with SenseVoice

**What goes wrong:** Using CAM++ with SenseVoice causes error: "Only paraformer-large-vad-punc and speech_seaco_paraformer can predict timestamp."

**Why it happens:** Speaker diarization requires word-level timestamps. SenseVoice doesn't output timestamps.

**How to avoid:** Use Paraformer-Large model (already in Phase 1). Verify model compatibility before adding speaker model.

**Warning signs:** KeyError for "timestamp", error messages about timestamp prediction.

### Pitfall 2: Missing VAD Model with Speaker Diarization

**What goes wrong:** Speaker diarization silently fails or produces incorrect results when VAD is disabled.

**Why it happens:** VAD segments are used for speaker embedding extraction. Without VAD, the pipeline cannot properly segment audio for speaker analysis.

**How to avoid:** Always enable VAD when using `spk_model`. Ensure `vad_model` is set in AutoModel initialization.

**Warning signs:** All segments assigned to same speaker; empty speaker results.

### Pitfall 3: Temp File Leaks from Video Extraction

**What goes wrong:** Extracted audio files accumulate in temp directory, consuming disk space.

**Why it happens:** FFmpeg extraction creates temp files that must be explicitly deleted after transcription.

**How to avoid:** Use try/finally block to ensure cleanup. Implement context manager pattern for temp files.

**Warning signs:** Growing temp directory; disk space warnings; stale .wav files in /tmp.

### Pitfall 4: FFmpeg Not Found

**What goes wrong:** Subprocess call fails with "ffmpeg: command not found" error.

**Why it happens:** FFmpeg not installed on user's system.

**How to avoid:** Use imageio-ffmpeg which bundles FFmpeg binary. Check for system FFmpeg first, fall back to imageio-ffmpeg.

**Warning signs:** FileNotFoundError when running ffmpeg command.

### Pitfall 5: Speaker Label Inconsistency

**What goes wrong:** Speaker IDs are non-consecutive or have gaps (e.g., 0, 2, 5 instead of 0, 1, 2).

**Why it happens:** FunASR's clustering may merge speakers, leaving gaps in label sequence.

**How to avoid:** Use FunASR's `correct_labels()` function to renumber speakers consecutively. Already handled in `postprocess()`.

**Warning signs:** Speaker labels skip letters (Speaker A, Speaker D, Speaker F).

## Code Examples

### Complete Speaker Diarization Pipeline

```python
# Source: FunASR auto_model.py, speaker_utils.py

from funasr import AutoModel
from funasr.models.campplus.utils import distribute_spk, postprocess

def create_pipeline_with_diarization(device: str, model_dir: str = "./models") -> AutoModel:
    """Create FunASR pipeline with speaker diarization enabled.

    This extends the Phase 1 pipeline with CAM++ speaker model.
    """
    model = AutoModel(
        model="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        punc_model="iic/punc_ct-transformer_cn-en-common-vocab471067-large",
        spk_model="iic/speech_campplus_sv_zh-cn_16k-common",
        spk_mode="punc_segment",  # Use punctuation boundaries for speaker segments
        device=device,
        disable_update=True,
        model_hub=model_dir,
        vad_kwargs={"max_single_segment_time": 30000},
    )
    return model


def transcribe_with_speakers(model: AutoModel, audio_path: str, device: str) -> dict:
    """Run transcription with speaker diarization.

    Returns:
        dict with keys:
            - text: Full transcription
            - sentence_info: List of segments with speaker labels
    """
    result = model.generate(
        input=audio_path,
        batch_size_s=300,
        device=device,
    )

    if result and len(result) > 0:
        return result[0]
    return None
```

### Video Audio Extraction with Cleanup

```python
# Source: Based on user decision (FFmpeg CLI with auto-cleanup)

import subprocess
import tempfile
import os
from contextlib import contextmanager

SUPPORTED_VIDEO_FORMATS = [".mp4", ".avi", ".mkv"]

@contextmanager
def extract_audio_from_video(video_path: str):
    """Context manager for video audio extraction with auto-cleanup.

    Usage:
        with extract_audio_from_video("video.mp4") as audio_path:
            result = transcribe(audio_path)
        # Audio file is automatically deleted after context exit
    """
    temp_audio = tempfile.mktemp(suffix=".wav")

    try:
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            temp_audio
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to extract audio from {video_path}: {result.stderr}"
            )

        yield temp_audio

    finally:
        if os.path.exists(temp_audio):
            os.remove(temp_audio)


def is_video_file(file_path: str) -> bool:
    """Check if file is a supported video format."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in SUPPORTED_VIDEO_FORMATS
```

### JSON Output with Speaker Labels

```python
# Source: Based on existing formatters.py with speaker extensions

import json

def format_json_with_speakers(result: dict) -> str:
    """Format transcription result as JSON with speaker labels.

    Output format:
    [
      {
        "text": "Hello world.",
        "start": 0,
        "end": 2500,
        "confidence": 0.95,
        "speaker_id": "Speaker A",
        "is_overlap": false
      }
    ]
    """
    segments = []

    for seg in result.get("sentence_info", []):
        segment_data = {
            "text": seg["sentence"],
            "start": seg["start"],
            "end": seg["end"],
            "confidence": seg.get("confidence", 1.0),
            "speaker_id": f"Speaker {chr(ord('A') + seg['spk'])}",
            "is_overlap": seg.get("is_overlap", False),
        }
        segments.append(segment_data)

    return json.dumps(segments, ensure_ascii=False, indent=2)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual speaker clustering | FunASR CAM++ integrated pipeline | FunASR 1.0+ | Simplified implementation; better accuracy |
| Fixed speaker count | Automatic speaker count detection | FunASR 1.2+ | No need to specify speaker count |
| Simple time-based overlap | Model-aware overlap distribution | FunASR 1.3+ | Better handling of overlapping speech |
| System FFmpeg only | imageio-ffmpeg bundled binary | Recent | No system dependency required |

**Deprecated/outdated:**
- **pyannote.audio:** Was alternative for speaker diarization, but FunASR CAM++ is better integrated
- **Manual FFmpeg installation:** Now handled by imageio-ffmpeg

## Open Questions

1. **Progress Indicator Granularity**
   - What we know: FunASR has `disable_pbar` parameter and `progress_callback` support
   - What's unclear: Best way to show diarization-specific progress (separate from transcription)
   - Recommendation: Use FunASR's built-in progress bar for now; can customize later if needed

2. **Overlap Detection Accuracy**
   - What we know: FunASR has built-in overlap detection via midpoint splitting
   - What's unclear: Whether time-based fallback (>50%) is accurate enough for real-world use
   - Recommendation: Start with hybrid approach (model-based + time fallback); tune threshold based on testing

3. **FFmpeg Binary Location**
   - What we know: imageio-ffmpeg provides bundled binary
   - What's unclear: Exact path to binary for subprocess call
   - Recommendation: Use `imageio_ffmpeg.get_ffmpeg_exe()` to get binary path

## Sources

### Primary (HIGH confidence)
- FunASR source code: `/Users/wuliang/.pyenv/versions/3.13.3/lib/python3.13/site-packages/funasr/auto/auto_model.py` - Speaker model integration (lines 159-186, 509-642)
- FunASR source code: `/Users/wuliang/.pyenv/versions/3.13.3/lib/python3.13/site-packages/funasr/models/campplus/cluster_backend.py` - Clustering implementation
- FunASR source code: `/Users/wuliang/.pyenv/versions/3.13.3/lib/python3.13/site-packages/funasr/models/campplus/utils.py` - Speaker utilities (sv_chunk, postprocess, distribute_spk)
- Project research: `.planning/research/STACK.md` - FunASR model IDs, version compatibility
- Project research: `.planning/research/PITFALLS.md` - Speaker model incompatibility issues

### Secondary (MEDIUM confidence)
- Project research: `.planning/research/ARCHITECTURE.md` - Pipeline composition patterns
- Project research: `.planning/research/FEATURES.md` - Feature dependencies for speaker diarization
- Existing codebase: `asr_skill/core/models.py` - Current model initialization pattern
- Existing codebase: `asr_skill/postprocessing/formatters.py` - Current output format patterns

### Tertiary (LOW confidence)
- None - All critical information verified from source code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - FunASR source code analyzed; model IDs verified in project research
- Architecture: HIGH - FunASR auto_model.py shows exact integration pattern
- Pitfalls: HIGH - FunASR source code reveals model compatibility requirements; project PITFALLS.md documents known issues
- Video extraction: MEDIUM - FFmpeg pattern is standard; imageio-ffmpeg usage needs verification

**Research date:** 2026-03-14
**Valid until:** 30 days (stable FunASR API)
