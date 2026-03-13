# Architecture Research

**Domain:** FunASR-based Speech Recognition System
**Researched:** 2026-03-13
**Confidence:** HIGH (Official FunASR documentation and Model Zoo)

## Standard Architecture

### System Overview

A FunASR-based speech recognition system follows a modular pipeline architecture where specialized models are composed together. The AutoModel class orchestrates the pipeline, chaining models in a specific order.

```
+------------------------------------------------------------------+
|                        User Interface Layer                        |
|  +---------------+  +---------------+  +---------------+          |
|  | Claude Skill  |  |  CLI Tool     |  | Python API    |          |
|  +-------+-------+  +-------+-------+  +-------+-------+          |
|          |                  |                  |                   |
+----------+------------------+------------------+-------------------+
|          |                  |                  |                   |
|  +-------v------------------v------------------v-------+          |
|  |              Audio Preprocessing                      |          |
|  |  - Format detection (ffmpeg)                          |          |
|  |  - Audio extraction from video                        |          |
|  |  - Resampling to 16kHz                                |          |
|  +--------------------------+----------------------------+          |
|                             |                                     |
+-----------------------------+-------------------------------------+
|                             |                                     |
|  +--------------------------v----------------------------+        |
|  |              VAD Model (FSMN-VAD)                      |        |
|  |  - Voice Activity Detection                            |        |
|  |  - Long audio segmentation                             |        |
|  |  - Output: [[beg1, end1], [beg2, end2], ...]          |        |
|  +--------------------------+----------------------------+        |
|                             |                                     |
+-----------------------------+-------------------------------------+
|                             |                                     |
|  +--------------------------v----------------------------+        |
|  |              ASR Model (Paraformer-Large)              |        |
|  |  - Non-autoregressive speech recognition               |        |
|  |  - Timestamp prediction                                 |        |
|  |  - Hotword injection support                            |        |
|  |  - Output: text + timestamps                            |        |
|  +--------------------------+----------------------------+        |
|                             |                                     |
+-----------------------------+-------------------------------------+
|                             |                                     |
|  +--------------------------v----------------------------+        |
|  |         Punctuation Model (CT-Transformer)             |        |
|  |  - Punctuation restoration                              |        |
|  |  - Sentence boundary detection                          |        |
|  +--------------------------+----------------------------+        |
|                             |                                     |
+-----------------------------+-------------------------------------+
|                             |                                     |
|  +--------------------------v----------------------------+        |
|  |         Speaker Model (CAM++)                           |        |
|  |  - Speaker embedding extraction                         |        |
|  |  - Speaker clustering/diarization                       |        |
|  |  - Output: speaker labels per segment                   |        |
|  +--------------------------+----------------------------+        |
|                             |                                     |
+-----------------------------+-------------------------------------+
|                             |                                     |
|  +--------------------------v----------------------------+        |
|  |              Output Formatter                           |        |
|  |  - TXT, SRT, ASS, JSON, Markdown                        |        |
|  |  - Speaker-labeled transcripts                          |        |
|  +---------------------------------------------------------+        |
|                                                                     |
+---------------------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Audio Preprocessing | Format conversion, resampling, video audio extraction | ffmpeg, soundfile, torchaudio |
| VAD Model | Detect speech segments, split long audio | FSMN-VAD (0.4M params) |
| ASR Model | Speech-to-text conversion with timestamps | Paraformer-Large (220M params) |
| Punctuation Model | Add punctuation, sentence boundaries | CT-Transformer (290M params) |
| Speaker Model | Speaker identification and diarization | CAM++ (7.2M params) |
| Output Formatter | Generate various output formats | Custom formatters per format type |
| Model Manager | Load/cache models, device selection | FunASR AutoModel class |

## Recommended Project Structure

```
asr-skill/
+-- src/
|   +-- asr_skill/
|       +-- __init__.py
|       +-- cli.py              # CLI entry point
|       +-- skill.py            # Claude Code skill integration
|       +-- core/
|       |   +-- __init__.py
|       |   +-- pipeline.py     # Main transcription pipeline
|       |   +-- models.py       # Model loading and management
|       |   +-- config.py       # Configuration handling
|       +-- preprocessing/
|       |   +-- __init__.py
|       |   +-- audio.py        # Audio preprocessing utilities
|       |   +-- video.py        # Video audio extraction
|       +-- postprocessing/
|       |   +-- __init__.py
|       |   +-- formatters.py   # Output format generators
|       |   +-- speakers.py     # Speaker label processing
|       +-- utils/
|           +-- __init__.py
|           +-- device.py       # Hardware detection (GPU/CPU/MPS)
|           +-- hotword.py      # Hotword configuration
|           +-- paths.py        # Path handling utilities
+-- tests/
|   +-- test_pipeline.py
|   +-- test_preprocessing.py
|   +-- test_formatters.py
+-- config/
|   +-- default.yaml            # Default configuration
|   +-- hotwords.yaml           # Hotword templates
+-- pyproject.toml
+-- README.md
```

### Structure Rationale

- **core/**: Contains the main pipeline orchestration and model management. This is the heart of the system.
- **preprocessing/**: Isolated audio/video preprocessing logic. Separates concerns for different input types.
- **postprocessing/**: Output formatting and speaker label processing. Allows adding new formats without touching core logic.
- **utils/**: Cross-cutting concerns like device detection and hotword handling.

## Architectural Patterns

### Pattern 1: Pipeline Composition

**What:** Models are composed in a chain through the AutoModel class. Each model receives output from the previous model and passes its output to the next.

**When to use:** Always - this is the standard FunASR pattern.

**Trade-offs:**
- Pros: Modular, easy to enable/disable components, well-tested by FunASR team
- Cons: Sequential processing, no parallelization between models

**Example:**
```python
from funasr import AutoModel

model = AutoModel(
    model="paraformer-zh",       # ASR model
    vad_model="fsmn-vad",        # VAD model
    punc_model="ct-punc",        # Punctuation model
    spk_model="cam++",           # Speaker diarization model
    vad_kwargs={"max_single_segment_time": 30000},
)

res = model.generate(
    input=audio_path,
    batch_size_s=300,            # Dynamic batching (300 seconds)
    hotword="keyword1 keyword2"
)
```

### Pattern 2: Dynamic Batching

**What:** Process audio in batches based on total duration (seconds) rather than fixed batch sizes. The `batch_size_s` parameter controls this.

**When to use:** For long audio processing to optimize GPU utilization and reduce overhead.

**Trade-offs:**
- Pros: Better GPU utilization, lower overhead for long audio
- Cons: Higher memory usage, need to tune based on available VRAM

**Example:**
```python
# Process 300 seconds of audio per batch
res = model.generate(
    input=long_audio_path,
    batch_size_s=300,  # 300 seconds per batch
)
```

### Pattern 3: VAD-Based Long Audio Segmentation

**What:** Use VAD model to split long audio into semantic segments before ASR processing. The `max_single_segment_time` parameter controls maximum segment length.

**When to use:** Required for audio files longer than ~30 seconds. Essential for hour-long recordings.

**Trade-offs:**
- Pros: Handles arbitrary length audio, respects speech boundaries
- Cons: Adds preprocessing overhead, VAD errors can affect downstream quality

**Example:**
```python
model = AutoModel(
    model="paraformer-zh",
    vad_model="fsmn-vad",
    vad_kwargs={"max_single_segment_time": 30000},  # 30 seconds max per segment
)
```

### Pattern 4: Hardware-Adaptive Device Selection

**What:** Automatically detect and use the best available compute device: MPS (Apple Silicon) > CUDA (NVIDIA) > CPU fallback.

**When to use:** Always - ensures portability across different hardware.

**Trade-offs:**
- Pros: Works everywhere, optimal performance on each platform
- Cons: Need to test on all target platforms

**Example:**
```python
import torch

def get_device():
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda:0"
    return "cpu"

model = AutoModel(
    model="paraformer-zh",
    device=get_device(),
)
```

## Data Flow

### Request Flow

```
[User: /asr video.mp4]
         |
         v
[CLI/Skill Parser] --> [Config Loader] --> [Device Detector]
         |
         v
[Audio Preprocessor]
  - Extract audio from video (ffmpeg)
  - Resample to 16kHz
         |
         v
[AutoModel Pipeline]
  |
  +--> [VAD: FSMN-VAD]
  |      - Detect speech segments
  |      - Output: [[start_ms, end_ms], ...]
  |
  +--> [ASR: Paraformer-Large]
  |      - Transcribe each segment
  |      - Output: {text, timestamps}
  |
  +--> [PUNC: CT-Transformer]
  |      - Add punctuation
  |      - Output: punctuated text
  |
  +--> [SPK: CAM++]
         - Extract speaker embeddings
         - Cluster into speakers
         - Output: speaker labels
         |
         v
[Output Formatter]
  - Generate TXT/SRT/ASS/JSON/MD
  - Apply speaker labels
         |
         v
[Result: transcript.srt in source directory]
```

### Key Data Flows

1. **Audio Input Flow:** Raw audio/video -> Preprocessed 16kHz WAV -> VAD segments -> ASR chunks -> Transcribed text
2. **Speaker Flow:** Audio segments -> CAM++ embeddings -> Clustering -> Speaker IDs -> Mapped to transcript segments
3. **Output Flow:** Transcribed text + timestamps + speaker IDs -> Format-specific renderer -> Output file

### State Management

```
[Model Cache]
    | (load once, reuse)
    v
[AutoModel Instance] <-- [Config]
    |
    +--> [VAD State] (per-session cache)
    +--> [ASR State] (per-inference cache)
    +--> [SPK State] (speaker embedding cache)
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Single user, occasional use | Single process, CPU fallback acceptable, models loaded on demand |
| Power user, frequent use | Keep models loaded in memory, use GPU, batch multiple files |
| Team/organization | Add queue system, consider GPU server deployment, use ONNX runtime for efficiency |

### Scaling Priorities

1. **First bottleneck:** Memory when processing long audio. Mitigation: Use VAD with smaller `max_single_segment_time`, implement chunked processing with state management.

2. **Second bottleneck:** GPU memory for concurrent requests. Mitigation: Implement request queuing, use ONNX quantized models, consider CPU fallback for overflow.

### Performance Characteristics

| Model | Parameters | RTF (Real-Time Factor) | Notes |
|-------|------------|------------------------|-------|
| FSMN-VAD | 0.4M | ~0.001 | Very fast, minimal overhead |
| Paraformer-Large | 220M | ~0.02-0.05 | Main processing time |
| CT-Transformer | 290M | ~0.01 | Fast punctuation |
| CAM++ | 7.2M | ~0.005 | Fast speaker embedding |

RTF < 1 means faster than real-time. Paraformer-Large at 0.02 means 50x real-time speed on GPU.

## Anti-Patterns

### Anti-Pattern 1: Processing Long Audio Without VAD

**What people do:** Pass hour-long audio directly to ASR model without VAD segmentation.

**Why it's wrong:** Memory exhaustion, extremely slow processing, potential quality degradation.

**Do this instead:** Always use VAD model for audio > 30 seconds:
```python
model = AutoModel(
    model="paraformer-zh",
    vad_model="fsmn-vad",  # Required for long audio
    vad_kwargs={"max_single_segment_time": 30000},
)
```

### Anti-Pattern 2: Hardcoding Device

**What people do:** Hardcode `device="cuda:0"` assuming NVIDIA GPU availability.

**Why it's wrong:** Fails on Apple Silicon (MPS) and CPU-only machines.

**Do this instead:** Implement adaptive device selection:
```python
def get_device():
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda:0"
    return "cpu"
```

### Anti-Pattern 3: Ignoring Sample Rate

**What people do:** Feed audio at arbitrary sample rates to the model.

**Why it's wrong:** FunASR models are trained on 16kHz audio. Wrong sample rate causes recognition errors.

**Do this instead:** Always resample to 16kHz:
```python
import torchaudio

waveform, sr = torchaudio.load(audio_path)
if sr != 16000:
    resampler = torchaudio.transforms.Resample(sr, 16000)
    waveform = resampler(waveform)
```

### Anti-Pattern 4: Loading Models Repeatedly

**What people do:** Create new AutoModel instance for each transcription request.

**Why it's wrong:** Model loading is expensive (seconds to minutes). Wastes time and memory.

**Do this instead:** Load models once, reuse for multiple requests:
```python
# Global or singleton model instance
_model = None

def get_model():
    global _model
    if _model is None:
        _model = AutoModel(model="paraformer-zh", vad_model="fsmn-vad")
    return _model
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| ModelScope | Model download hub | Default model source, handles caching |
| HuggingFace | Alternative model hub | Use `hub="hf"` parameter |
| ffmpeg | Audio/video processing | Required for video extraction and format conversion |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI <-> Core | Function calls | Direct Python calls |
| Skill <-> Core | Function calls | Direct Python calls |
| Core <-> Preprocessing | Function calls | Sync, blocking |
| Core <-> Postprocessing | Function calls | Sync, blocking |
| Core <-> FunASR | FunASR API | AutoModel.generate() |

## Build Order Implications

Based on component dependencies, the recommended build order is:

1. **Core Infrastructure** (models.py, config.py, device detection)
   - No dependencies, foundation for everything else

2. **Audio Preprocessing** (audio.py, video.py)
   - Depends on: ffmpeg, soundfile
   - Required by: Pipeline

3. **Pipeline Core** (pipeline.py)
   - Depends on: Core Infrastructure, Preprocessing
   - Integrates all models

4. **Output Formatters** (formatters.py, speakers.py)
   - Depends on: Pipeline output format
   - Generates final outputs

5. **CLI Interface** (cli.py)
   - Depends on: Pipeline, Config
   - User-facing entry point

6. **Claude Skill Integration** (skill.py)
   - Depends on: Pipeline, CLI
   - Claude Code specific integration

## Sources

- FunASR GitHub Repository: https://github.com/modelscope/FunASR
- FunASR PyPI Package: https://pypi.org/project/funasr/
- Model Zoo Documentation: https://github.com/alibaba-damo-academy/FunASR/blob/main/docs/model_zoo/modelscope_models.md
- Runtime Documentation: https://github.com/alibaba-damo-academy/FunASR/blob/main/runtime/readme.md

---
*Architecture research for: FunASR-based Speech Recognition System*
*Researched: 2026-03-13*
