# Phase 1: Core ASR Pipeline - Research

**Researched:** 2026-03-13
**Domain:** FunASR-based Speech Recognition Pipeline
**Confidence:** MEDIUM

## Summary

Phase 1 delivers the core transcription pipeline using FunASR's AutoModel composition pattern. The implementation centers on Paraformer-Large for ASR, FSMN-VAD for long audio segmentation, and CT-Transformer for punctuation. Hardware auto-detection must support CUDA, MPS (Apple Silicon), and CPU fallback with explicit device management to avoid the known GPU-to-CPU fallback bug.

Critical implementation concerns include memory management for long audio (batch_size_s=300 with explicit cleanup), stereo-to-mono conversion for dual-channel audio, and the `disable_update=True` flag to prevent kwargs mutation. Output follows the locked decisions: TXT with inline timestamps `[HH:MM:SS.mmm]` and JSON with segment-level structure.

**Primary recommendation:** Use FunASR AutoModel with VAD+ASR+PUNC pipeline composition, explicit device setting on every generate() call, and audio preprocessing that resamples to 16kHz mono before model inference.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Invocation style
- CLI-only invocation with minimal required input (just file path)
- Everything else auto-detected: hardware, output format, output location
- Short flags only for optional parameters: `-o` (output), `-f` (format)
- Python API: single function `transcribe("audio.mp3")` returning dict
- No config file required for v1 — keep it simple

#### Output structure
- TXT format: timestamps inline `[00:00:00.000] text`
- JSON format: segment level (array of segments with text, start, end, confidence)
- Timestamp format: standard SRT style `HH:MM:SS.mmm`
- Output filenames: same basename as input (`audio.mp3` → `audio.txt`, `audio.json`)

#### Error handling
- Primary strategy: fail fast with clear error messages
- GPU-to-CPU fallback: auto-fallback with warning message
- Corrupted audio: fail entire file (no graceful degradation for v1)
- Error reporting: console output to stderr with color coding

#### Model management
- Cache location: project-local `./models/` directory
- First-run: auto-download models with progress bar (no prompt)
- Version management: pinned versions from research (funasr==1.3.1)
- Cleanup: keep all downloaded models (no auto-cleanup)

### Claude's Discretion
- Exact error message wording and format
- Progress bar implementation style
- Color scheme for console output
- Specific retry behavior for recoverable errors (if any)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CORE-01 | System auto-detects available hardware (CUDA GPU, Apple MPS, CPU) and selects optimal device | PyTorch device detection pattern documented in Architecture Patterns |
| CORE-02 | System validates Python version (>=3.10) and dependencies before execution | Version requirements in Standard Stack; sys.version_info check |
| CORE-03 | System auto-downloads and caches FunASR models to local `models/` directory | ModelScope caching with `model_hub` parameter; FunASR AutoModel handles download |
| CORE-04 | System handles GPU-to-CPU fallback gracefully with user notification | Pitfall 2 mitigation: explicit device setting, warning message on fallback |
| AUDIO-01 | User can input audio files in MP3, WAV, M4A, FLAC formats | FFmpeg/soundfile preprocessing documented; resample to 16kHz mono |
| AUDIO-03 | System automatically resamples audio to 16kHz for optimal recognition | Audio preprocessing pattern with librosa/torchaudio documented |
| AUDIO-04 | System handles long audio (>1 hour) with VAD-based intelligent segmentation | VAD pattern with batch_size_s=300 and max_single_segment_time=30000 |
| TRAN-01 | User receives text transcription of audio content | FunASR AutoModel generate() returns text |
| TRAN-02 | User receives word-level timestamps for each transcribed segment | Paraformer-Large provides timestamps; segment-level output format |
| TRAN-03 | System adds punctuation using CT-Transformer model | CT-Transformer punc_model integration documented |
| OUTP-01 | User can export transcription as plain TXT file | TXT formatter with inline timestamps pattern |
| OUTP-04 | User can export as structured JSON with full metadata | JSON segment structure documented in output format |
| OUTP-06 | Output files are saved in same directory as input by default | Path handling: extract dirname from input, use same basename |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| funasr | 1.3.1 | ASR framework with integrated models | Alibaba DAMO; Chinese-optimized; includes VAD, ASR, punctuation |
| torch | 2.9.1+ | Deep learning backend | Required by FunASR; supports CUDA 12.x and MPS |
| modelscope | 1.34.0 | Model distribution hub | Handles model download and caching |
| ffmpeg | 6.0+ | Audio/video processing | Format conversion, resampling to 16kHz |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| click | 8.3.1 | CLI framework | Argument parsing, subcommands |
| rich | 14.3.3 | Terminal UI | Progress bars, formatted output, color |
| librosa | 0.11.0 | Audio analysis | Audio loading, resampling validation |
| soundfile | 0.13.1 | Audio I/O | Fast audio file reading |
| pyyaml | 6.0.3 | Configuration | Future config support (not Phase 1) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| click | typer | Simpler API but adds dependency on type hints; click is battle-tested |
| rich | tqdm | tqdm is simpler but rich provides color/formatted output in one package |
| librosa | torchaudio | torchaudio is PyTorch-native but librosa has better format support |

**Installation:**
```bash
pip install funasr==1.3.1 torch==2.9.1 modelscope==1.34.0
pip install click==8.3.1 rich==14.3.3 librosa==0.11.0 soundfile==0.13.1
```

**System dependency:**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
apt-get install ffmpeg
```

## Architecture Patterns

### Recommended Project Structure
```
asr_skill/
├── __init__.py           # Package init, version
├── cli.py                # CLI entry point (click)
├── core/
│   ├── __init__.py
│   ├── pipeline.py       # Main transcription pipeline
│   ├── models.py         # Model loading, device management
│   └── device.py         # Hardware detection
├── preprocessing/
│   ├── __init__.py
│   └── audio.py          # Audio preprocessing (resample, mono)
├── postprocessing/
│   ├── __init__.py
│   └── formatters.py     # TXT/JSON output formatters
└── utils/
    ├── __init__.py
    └── paths.py          # Path handling utilities
```

### Pattern 1: Hardware-Adaptive Device Selection
**What:** Automatically detect and use the best available compute device with explicit setting.
**When to use:** Always - ensures portability across different hardware.

```python
# Source: FunASR documentation + PyTorch device API
import torch

def get_device() -> str:
    """Detect optimal device: MPS > CUDA > CPU"""
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda:0"
    return "cpu"

def get_device_with_fallback() -> tuple[str, bool]:
    """Return device and whether fallback occurred."""
    preferred = get_device()
    if preferred == "cpu":
        return "cpu", True  # Fallback from expected GPU
    return preferred, False
```

### Pattern 2: FunASR AutoModel Pipeline Composition
**What:** Compose VAD + ASR + Punctuation models in a single pipeline.
**When to use:** All transcriptions - this is the standard FunASR pattern.

```python
# Source: FunASR Model Zoo documentation
from funasr import AutoModel

def create_pipeline(device: str, model_dir: str = "./models"):
    """Create ASR pipeline with VAD and punctuation."""
    model = AutoModel(
        model="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        punc_model="iic/punc_ct-transformer_cn-en-common-vocab471067-large",
        device=device,
        disable_update=True,  # CRITICAL: prevents kwargs mutation
        model_hub=model_dir,
        vad_kwargs={"max_single_segment_time": 30000},  # 30s max per segment
    )
    return model
```

### Pattern 3: Explicit Device Setting on generate()
**What:** Pass device explicitly on every generate() call to avoid GPU-to-CPU fallback bug.
**When to use:** Every inference call - prevents Pitfall 2.

```python
# Source: FunASR GitHub issues analysis (Issue #2652)
def transcribe(model, audio_path: str, device: str) -> dict:
    """Run transcription with explicit device setting."""
    result = model.generate(
        input=audio_path,
        batch_size_s=300,  # 300 seconds per batch for long audio
        device=device,     # EXPLICIT: prevents fallback bug
    )
    return result[0] if result else None
```

### Pattern 4: Audio Preprocessing (Resample + Mono)
**What:** Convert any input format to 16kHz mono WAV before processing.
**When to use:** All audio input - prevents Pitfall 6 (dual-channel errors).

```python
# Source: FunASR requirements + librosa documentation
import librosa
import soundfile as sf
import tempfile

def preprocess_audio(input_path: str) -> str:
    """Convert audio to 16kHz mono. Returns temp file path."""
    # Load with librosa (handles all formats)
    y, sr = librosa.load(input_path, sr=None, mono=True)

    # Resample to 16kHz if needed
    if sr != 16000:
        y = librosa.resample(y, orig_sr=sr, target_sr=16000)

    # Write to temp file
    temp_path = tempfile.mktemp(suffix=".wav")
    sf.write(temp_path, y, 16000)
    return temp_path
```

### Pattern 5: TXT Output with Inline Timestamps
**What:** Format transcription as TXT with timestamps inline per segment.
**When to use:** Default output format.

```python
# Source: CONTEXT.md locked decision
def format_txt(result: dict) -> str:
    """Format result as TXT with inline timestamps."""
    lines = []
    for segment in result.get("sentences", []):
        start = format_timestamp(segment["start"])
        text = segment["text"]
        lines.append(f"[{start}] {text}")
    return "\n".join(lines)

def format_timestamp(ms: int) -> str:
    """Convert milliseconds to HH:MM:SS.mmm format."""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
```

### Pattern 6: JSON Output with Segment Structure
**What:** Format transcription as JSON array of segments with metadata.
**When to use:** Programmatic access or when -f json is specified.

```python
# Source: CONTEXT.md locked decision
import json

def format_json(result: dict) -> str:
    """Format result as JSON with segment-level structure."""
    segments = []
    for seg in result.get("sentences", []):
        segments.append({
            "text": seg["text"],
            "start": seg["start"],
            "end": seg["end"],
            "confidence": seg.get("confidence", 1.0),
        })
    return json.dumps(segments, ensure_ascii=False, indent=2)
```

### Anti-Patterns to Avoid
- **Hardcoding device="cuda":** Fails on Apple Silicon and CPU-only machines. Use device detection.
- **Skipping VAD for "short" audio:** VAD is required for timestamps and punctuation. Always enable.
- **Creating new AutoModel per request:** Slow model loading. Reuse model instance.
- **Processing stereo audio directly:** Causes shape mismatch errors. Convert to mono first.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Audio format conversion | Custom FFmpeg wrapper | librosa.load() | Handles edge cases, tested across formats |
| Device detection | Manual CUDA check | torch.backends API | Handles MPS, CUDA version compatibility |
| Timestamp formatting | Custom time math | datetime.timedelta or format function | Edge cases in rollover, negative values |
| Model download | Custom HTTP client | FunASR AutoModel with model_hub | Handles ModelScope auth, caching, resume |
| Progress bar | Custom print loop | rich.progress | Thread-safe, ETA, handles terminal resize |

**Key insight:** FunASR handles model orchestration internally. Don't build separate model pipelines - use AutoModel composition.

## Common Pitfalls

### Pitfall 1: GPU Falls Back to CPU on Subsequent Runs
**What goes wrong:** First inference runs on GPU, subsequent inferences silently fall back to CPU causing 10x slowdown.
**Why it happens:** FunASR AutoModel keeps mutable state in kwargs dictionaries. Long inferences mutate these dicts causing device mismatch.
**How to avoid:**
1. Use `disable_update=True` in AutoModel initialization
2. Explicitly set `device` parameter on every `generate()` call
3. Monitor device usage with `nvidia-smi` during inference
**Warning signs:** First inference fast, subsequent inferences slow; progress bar shows CPU operations.

### Pitfall 2: Memory Explosion on Long Audio
**What goes wrong:** Processing 1+ hour audio causes memory to grow unbounded until OOM crash.
**Why it happens:** FunASR loads entire audio segments into memory without streaming; VAD creates intermediate tensors that accumulate.
**How to avoid:**
1. Set `batch_size_s=300` (300 seconds per batch)
2. Set `vad_kwargs={"max_single_segment_time": 30000}` (30s max per VAD segment)
3. Call `torch.cuda.empty_cache()` after processing
**Warning signs:** Memory usage grows linearly with audio length; GPU memory not released after inference.

### Pitfall 3: Dual-Channel Audio Processing Errors
**What goes wrong:** Stereo/dual-channel audio causes shape mismatch errors: `data.shape=[2, 11520]` but expected `data_len=[11520, 11520]`.
**Why it happens:** FunASR's extract_fbank function assumes mono audio; no automatic channel mixing.
**How to avoid:** Always convert stereo to mono in preprocessing using `librosa.load(..., mono=True)`.
**Warning signs:** Shape mismatch errors in preprocessing; IndexError in audio loading.

### Pitfall 4: VAD Model Configuration Dependencies
**What goes wrong:** Disabling VAD causes punctuation model to also be disabled; VAD with wrong parameters crashes.
**Why it happens:** FunASR pipeline has implicit dependencies between models; VAD output format expected by downstream.
**How to avoid:** Always enable VAD when using punctuation model; use default VAD parameters; set `vad_kwargs` explicitly.
**Warning signs:** Punctuation missing; TypeError or KeyError in timestamp processing.

## Code Examples

### Complete CLI Entry Point
```python
# Source: click documentation + project requirements
import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress

@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output directory (default: same as input)")
@click.option("-f", "--format", type=click.Choice(["txt", "json"]), default="txt", help="Output format")
@click.version_option(version="0.1.0")
def transcribe_cmd(input_file: str, output: str, format: str):
    """Transcribe audio file to text with timestamps."""
    console = Console()

    # Detect hardware
    device, fallback = get_device_with_fallback()
    if fallback:
        console.print("[yellow]Warning: GPU not available, using CPU (10x slower)[/yellow]")

    # Load model (cached)
    model = create_pipeline(device)

    # Preprocess audio
    with Progress() as progress:
        task = progress.add_task("Preprocessing...", total=1)
        audio_path = preprocess_audio(input_file)
        progress.update(task, completed=1)

    # Transcribe
    with Progress() as progress:
        task = progress.add_task("Transcribing...", total=1)
        result = transcribe(model, audio_path, device)
        progress.update(task, completed=1)

    # Format output
    if format == "txt":
        output_text = format_txt(result)
    else:
        output_text = format_json(result)

    # Write output
    input_path = Path(input_file)
    output_dir = Path(output) if output else input_path.parent
    output_file = output_dir / f"{input_path.stem}.{format}"
    output_file.write_text(output_text, encoding="utf-8")

    console.print(f"[green]Output saved to: {output_file}[/green]")
```

### Python API Function
```python
# Source: CONTEXT.md locked decision
def transcribe(input_file: str, output_dir: str = None, format: str = "txt") -> dict:
    """
    Transcribe audio file to text.

    Args:
        input_file: Path to audio file (MP3, WAV, M4A, FLAC)
        output_dir: Output directory (default: same as input)
        format: Output format "txt" or "json"

    Returns:
        dict with keys: text, segments, output_path
    """
    device, fallback = get_device_with_fallback()
    model = create_pipeline(device)
    audio_path = preprocess_audio(input_file)
    result = transcribe(model, audio_path, device)

    # Write output file
    input_path = Path(input_file)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    out_file = out_dir / f"{input_path.stem}.{format}"

    if format == "txt":
        out_file.write_text(format_txt(result), encoding="utf-8")
    else:
        out_file.write_text(format_json(result), encoding="utf-8")

    return {
        "text": result.get("text", ""),
        "segments": result.get("sentences", []),
        "output_path": str(out_file),
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed-size audio chunks | VAD-based segmentation | FunASR default | Better semantic boundaries |
| GPU-only processing | Hardware-adaptive (CUDA/MPS/CPU) | PyTorch 1.12+ | Works on Apple Silicon |
| Manual model download | AutoModel with ModelScope | FunASR 1.0+ | Simpler setup |
| CPU inference only | GPU-accelerated inference | PyTorch 2.0+ | 10-50x speedup |

**Deprecated/outdated:**
- **FunASR 1.3.0:** Performance regression (10x latency increase vs 1.3.1). Use 1.3.1.
- **SenseVoice with CAM++:** Model incompatibility - no timestamp output for speaker diarization. Use Paraformer-Large.

## Open Questions

1. **MPS Tensor Operation Compatibility**
   - What we know: PyTorch MPS backend exists, FunASR works on MPS in some cases
   - What's unclear: Specific tensor operations that may fail on MPS
   - Recommendation: Test on Apple Silicon hardware; implement fallback to CPU if MPS operations fail

2. **Model Download Progress Integration**
   - What we know: ModelScope downloads models, FunASR uses it
   - What's unclear: How to integrate ModelScope download progress with rich progress bar
   - Recommendation: Accept ModelScope's default progress output for v1; enhance in Phase 3

3. **Confidence Score Availability**
   - What we know: Paraformer-Large outputs confidence scores
   - What's unclear: Exact field name in output dict, whether it's per-word or per-segment
   - Recommendation: Test with sample audio and inspect output structure; default to 1.0 if not available

## Sources

### Primary (HIGH confidence)
- FunASR GitHub Repository: https://github.com/modelscope/FunASR - Model IDs, AutoModel patterns
- FunASR PyPI Package: https://pypi.org/project/funasr/ - Version 1.3.1 dependencies
- Model Zoo Documentation: https://github.com/alibaba-damo-academy/FunASR/blob/main/docs/model_zoo/modelscope_models.md - Model IDs

### Secondary (MEDIUM confidence)
- Project research files (STACK.md, ARCHITECTURE.md, PITFALLS.md) - Verified from GitHub issues
- PyTorch documentation - Device detection API
- click and rich documentation - CLI patterns

### Tertiary (LOW confidence)
- Training knowledge for FunASR API specifics - Needs validation with actual code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Versions verified from PyPI, model IDs from official docs
- Architecture: HIGH - FunASR patterns well-documented in project research
- Pitfalls: MEDIUM - Based on GitHub issues analysis; specific mitigation code needs testing

**Research date:** 2026-03-13
**Valid until:** 30 days (stable FunASR/PyTorch versions)
