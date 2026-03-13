# Stack Research

**Domain:** FunASR-based Speech Recognition Tool
**Researched:** 2026-03-13
**Confidence:** MEDIUM (PyPI version data verified HIGH; FunASR model IDs and compatibility MEDIUM based on existing research; WebSearch/WebFetch blocked for additional verification)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.10+ | Runtime environment | PyTorch 2.10 requires Python 3.10+; provides best balance of modern features and ecosystem compatibility |
| **FunASR** | 1.3.1 | ASR framework | Latest stable release from Alibaba DAMO; includes Paraformer, VAD, speaker diarization, and punctuation models |
| **PyTorch** | 2.9.1 or 2.10.0 | Deep learning backend | Required by FunASR; 2.9.1 is installed and tested; 2.10.0 is latest with CUDA 12.x support |
| **ModelScope** | 1.34.0 | Model hub | Official model distribution for FunASR models; handles model download and caching |
| **FFmpeg** | 6.0+ | Audio/video processing | Industry standard for format conversion, audio extraction, and resampling; required for multi-format input |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **librosa** | 0.11.0 | Audio analysis | Audio loading, resampling to 16kHz, feature extraction |
| **soundfile** | 0.13.1 | Audio I/O | Fast audio file reading/writing; used by FunASR internally |
| **scipy** | 1.16.x or 1.17.x | Signal processing | Audio preprocessing, filtering; required by FunASR |
| **pydub** | 0.25.1 | Audio manipulation | Simple audio format conversion, trimming, channel mixing |
| **srt** | 3.5.3 | SRT subtitle generation | Generate SRT format output for video subtitles |
| **ass** | 1.0.3 | ASS subtitle generation | Generate ASS format output with speaker styling |
| **click** | 8.3.1 | CLI framework | Command-line argument parsing, subcommands |
| **rich** | 14.3.3 | Terminal UI | Progress bars, formatted output, syntax highlighting |
| **PyYAML** | 6.0.3 | Configuration | Hotword config files, model settings |
| **tqdm** | 4.67.x | Progress display | Progress bars for long audio processing |

### FunASR Model IDs (ModelScope)

| Model | ModelScope ID | Purpose | Size |
|-------|---------------|---------|------|
| **Paraformer-Large** | `iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch` | Core ASR model | ~1.2GB |
| **VAD-FSMN** | `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch` | Voice Activity Detection | ~50MB |
| **CAM++** | `iic/speech_campplus_sv_zh-cn_16k-common` | Speaker diarization | ~300MB |
| **Punc-CT-Transformer** | `iic/punc_ct-transformer_cn-en-common-vocab471067-large` | Punctuation restoration | ~1.1GB |

**Total model download:** ~2.6GB

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **pytest** | Testing framework | Unit tests, integration tests |
| **black** | Code formatting | Consistent style |
| **ruff** | Linting | Fast, modern linter |
| **mypy** | Type checking | Optional but recommended for robustness |

## Installation

```bash
# Core dependencies
pip install funasr==1.3.1
pip install torch==2.9.1  # or 2.10.0 for latest CUDA support
pip install modelscope==1.34.0

# Audio processing
pip install librosa==0.11.0
pip install soundfile==0.13.1
pip install scipy>=1.16.0
pip install pydub==0.25.1

# Output formats
pip install srt==3.5.3
pip install ass==1.0.3

# CLI and UI
pip install click==8.3.1
pip install rich==14.3.3
pip install pyyaml==6.0.3
pip install tqdm>=4.67.0

# Development
pip install pytest black ruff mypy
```

**System dependencies:**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
apt-get install ffmpeg

# Verify FFmpeg
ffmpeg -version  # Requires 6.0+
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FunASR | OpenAI Whisper | Multi-language support needed; willing to use cloud API; less Chinese-specific accuracy needed |
| FunASR | vosk | Smaller model size needed; offline-only constraint; less accuracy acceptable |
| Paraformer-Large | SenseVoice | Faster inference needed; speaker diarization NOT required (SenseVoice incompatible with CAM++) |
| PyTorch | ONNX Runtime | Production deployment; smaller footprint; inference-only |
| pydub | ffmpeg-python | More granular FFmpeg control needed; complex audio pipelines |
| click | typer | Simpler CLI with automatic help generation; async support needed |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| FunASR 1.3.0 | Performance regression (10x latency increase vs 1.3.1) | FunASR 1.3.1 |
| SenseVoice with CAM++ | Model incompatibility; no timestamp output for speaker diarization | Paraformer-Large |
| Python 3.8 | PyTorch 2.10+ requires 3.10+; FunASR may have compatibility issues | Python 3.10+ |
| CPU-only torch | 10x slower inference; poor UX for long audio | torch with CUDA/MPS support |
| Global model download | Model conflicts between projects; version pinning issues | Local models/ directory |
| Skipping VAD | Punctuation model disabled; no timestamps; broken pipeline | Always enable VAD |

## Stack Patterns by Variant

**If NVIDIA GPU available:**
- Install `torch` with CUDA 12.x support
- Set device to "cuda:0" in AutoModel
- Monitor GPU memory with `nvidia-smi`

**If Apple Silicon (M1/M2/M3):**
- Install `torch` with MPS support
- Set device to "mps" in AutoModel
- Note: MPS may have tensor operation limitations

**If CPU only:**
- Warn user: "GPU not available, using CPU (10x slower)"
- Reduce `batch_size_s` to 150-200 for memory safety
- Consider ONNX Runtime for better CPU performance

## Version Compatibility Matrix

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| funasr==1.3.1 | torch>=2.0 | PyTorch 2.x required |
| funasr==1.3.1 | modelscope>=1.9.0 | ModelScope provides model downloads |
| torch==2.10.0 | Python>=3.10 | Hard requirement |
| librosa==0.11.0 | Python>=3.8 | Works with 3.10+ |
| scipy>=1.16.0 | Python>=3.10 | Version aligned with Python |
| Paraformer-Large | CAM++ speaker model | Must use together for diarization |
| SenseVoice | NOT CAM++ | Incompatible - no timestamps |

## FunASR-Specific Configuration

### AutoModel Usage Pattern

```python
from funasr import AutoModel

# Recommended initialization (avoids kwargs state mutation)
model = AutoModel(
    model="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    punc_model="iic/punc_ct-transformer_cn-en-common-vocab471067-large",
    spk_model="iic/speech_campplus_sv_zh-cn_16k-common",
    device="cuda:0",  # or "mps" or "cpu"
    disable_update=True,  # Prevents kwargs mutation
)

# For long audio, set batch_size_s explicitly
result = model.generate(
    input="audio.wav",
    batch_size_s=300,  # 300 seconds per batch
)
```

### Critical Parameters

| Parameter | Recommended Value | Why |
|-----------|-------------------|-----|
| `batch_size_s` | 300 | Balance memory vs speed; lower for long audio |
| `device` | Explicit "cuda:0"/"mps"/"cpu" | Avoid auto-detection bugs |
| `disable_update` | True | Prevents kwargs mutation on repeated inference |
| `vad_kwargs.max_single_segment_time` | 30000 | Max 30s per VAD segment |

## Hardware Requirements

| Hardware | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| RAM | 8GB | 16GB+ | Long audio needs more memory |
| GPU VRAM | 4GB | 8GB+ | Paraformer-Large + CAM++ |
| Disk | 5GB free | 10GB+ | Models + temp files |
| CPU | 4 cores | 8+ cores | CPU fallback mode |

## Sources

- PyPI (HIGH confidence): Verified package versions via pip index
- FunASR PyPI dependencies (HIGH confidence): Extracted from pypi.org JSON API
- PITFALLS.md research (MEDIUM confidence): Model compatibility issues, version regressions
- FEATURES.md research (MEDIUM confidence): Model IDs, feature requirements
- Project requirements (HIGH confidence): idea.md, PROJECT.md

---
*Stack research for: FunASR Speech Recognition Tool*
*Researched: 2026-03-13*
