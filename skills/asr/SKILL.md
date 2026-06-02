---
name: asr
description: This skill should be used when the user asks to "transcribe audio", "transcribe video", "convert speech to text", "generate subtitles", "create captions", "identify speakers in audio", or mentions audio/video transcription needs. Provides local ASR transcription with speaker diarization using FunASR (Paraformer + SenseVoice).
---

# ASR Transcription Skill

Provide local audio/video transcription with speaker diarization, multiple output formats, and progress indication. Supports two ASR engines: **Paraformer** (high accuracy) and **SenseVoice** (fast, lightweight).

## Purpose

Enable users to transcribe audio and video files to text with automatic speaker identification, supporting multiple subtitle formats while preserving privacy through local processing.

## When to Use

This skill triggers when the user:
- Wants to transcribe an audio file (MP3, WAV, M4A, FLAC)
- Wants to transcribe a video file (MP4, AVI, MKV)
- Needs subtitles or captions generated from media
- Wants to identify different speakers in audio
- Needs timestamped transcription output

## Quick Start

### Basic Transcription

```bash
# Transcribe audio file (auto-detects best model for your hardware)
python3 skills/asr/scripts/transcribe.py path/to/audio.mp3

# Transcribe video file
python3 skills/asr/scripts/transcribe.py path/to/video.mp4

# Force SenseVoice for faster CPU transcription
python3 skills/asr/scripts/transcribe.py audio.mp3 -m sensevoice

# Force Paraformer for best accuracy with speaker diarization
python3 skills/asr/scripts/transcribe.py meeting.mp3 -m paraformer
```

### ASR Engine Selection

| Engine | Model | Size | Best For | Diarization |
|--------|-------|------|----------|-------------|
| **auto** (default) | Auto-selected | — | Best for your hardware | Depends on selection |
| **paraformer** | Paraformer-Large | ~1.3 GB | GPU (CUDA/MPS), best accuracy | ✅ Yes |
| **sensevoice** | SenseVoiceSmall | ~200 MB | CPU, fast inference | ❌ No |

- **Auto mode**: GPU available → Paraformer; CPU only → SenseVoice
- **SenseVoice** is ~6x faster on CPU than Paraformer
- **Paraformer** requires GPU for acceptable speed but offers speaker diarization

### Output Formats

```bash
python3 skills/asr/scripts/transcribe.py audio.mp3 -f json   # Structured JSON with metadata
python3 skills/asr/scripts/transcribe.py audio.mp3 -f srt    # SubRip subtitles
python3 skills/asr/scripts/transcribe.py audio.mp3 -f ass    # ASS/SSA subtitles with speaker styling
python3 skills/asr/scripts/transcribe.py audio.mp3 -f md     # Markdown with speaker sections
```

### Python API

```python
from asr_skill import transcribe

# Auto-detect best model for your hardware
result = transcribe("meeting.mp4", format="srt")
print(f"Output: {result['output_path']}")
print(f"Model used: {result['model_used']}")
print(f"Speakers: {result.get('speakers', [])}")

# Force SenseVoice for fast CPU transcription
result = transcribe("lecture.mp3", model_type="sensevoice")

# Paraformer with speaker diarization
result = transcribe("interview.wav", model_type="paraformer", diarize=True)
```

### Configuration (config.txt)

```properties
# ── 运行模式（必选，二选一）──
# local: 本地 ASR 模型 / api: 小米 MiMo ASR API
mode = local

# ── 本地模式 ──
# ASR 引擎: auto（自动）/ paraformer（高精度）/ sensevoice（CPU 友好）
asr_model = auto
# 模型缓存目录（留空 = 平台默认）
model_dir =

# ── 输出配置 ──
output_format = txt
output_dir =

# ── 小米 MiMo API 模式（仅 mode=api 时生效，与 local 互斥）──
# API 密钥从 https://platform.xiaomimimo.com/profile 获取
# api.key = your-xiaomi-mimo-api-key
# api.language = auto        # auto, zh, en
# api.model = mimo-v2.5-asr  # 当前唯一支持的模型
# api.max_file_mb = 7        # Base64 编码前最大 MB（API 限制 10 MB Base64）
# api.timeout = 300
```

- `mode`: `"local"` or `"api"` — 二选一，互斥
- `asr_model`: `"auto"` (default), `"paraformer"`, or `"sensevoice"`
- `model_dir`: Custom model cache directory (blank = platform default)
- `output_format`: Default output format (txt, json, srt, ass, md)
- `output_dir`: Default output directory
- `api.key`: MiMo API key (required for API mode, or set `MIMO_API_KEY` env var)
- `api.language`: Language hint — `auto`, `zh`, `en` (default: `auto`)
- `api.max_file_mb`: Max raw audio file size in MB (API limit: ~10 MB Base64)

### Asynchronous Execution (Recommended for Long Files)

Avoid timeouts by running transcription in the background:

```bash
# Start async task
python3 skills/asr/scripts/transcribe.py long_video.mp4 --async
# Output: {"task_id": "a1b2c3d4", "status": "queued", ...}

# Check status
python3 skills/asr/scripts/transcribe.py --status a1b2c3d4
# Output: {"task_id": "a1b2c3d4", "status": "processing", "progress": 45, ...}

# List recent tasks
python3 skills/asr/scripts/transcribe.py --list
```

## Core Features

### Speaker Diarization (Paraformer Only)

Automatically identifies and labels different speakers:
- Speaker A, Speaker B, Speaker C, etc.
- Per-segment timestamps
- Overlap detection marked with [OVERLAP]

> **Note**: Speaker diarization requires Paraformer. SenseVoice does not output timestamps, so diarization is automatically disabled when using SenseVoice.

### Cross-Platform Hardware Support

Detects and uses the best available hardware:
- **macOS (Apple Silicon)**: MPS acceleration
- **Windows/Linux (NVIDIA GPU)**: CUDA acceleration
- **CPU fallback**: Automatically selects SenseVoice for faster CPU inference

### Platform-Aware Model Selection (New)

On first use, the appropriate model is automatically downloaded:

| Platform | GPU Available | Auto-Selected Model |
|----------|--------------|-------------------|
| macOS (M1-M4) | ✅ MPS | Paraformer (~1.3 GB) |
| Windows (NVIDIA) | ✅ CUDA | Paraformer (~1.3 GB) |
| Windows (no GPU) | ❌ CPU | **SenseVoice** (~200 MB) |
| Linux (NVIDIA) | ✅ CUDA | Paraformer (~1.3 GB) |
| Linux (no GPU) | ❌ CPU | **SenseVoice** (~200 MB) |

### Long Audio Support

Handles audio files longer than 1 hour:
- VAD-based intelligent segmentation
- Memory-efficient processing
- Progress indication during transcription

### Multiple Output Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| txt | .txt | Plain text with timestamps |
| json | .json | Structured data with word-level info |
| srt | .srt | Video subtitles |
| ass | .ass | Styled subtitles |
| md | .md | Documentation with speaker sections |

## Implementation Details

### Processing Pipeline

1. **Input validation** - Check file exists and format supported
2. **Hardware detection** - Auto-detect GPU/MPS/CPU
3. **Model selection** - Choose best ASR engine for current hardware
4. **Model download** - Auto-download from ModelScope on first use
5. **Video extraction** - Extract audio from video files via FFmpeg
6. **Audio preprocessing** - Resample to 16kHz mono
7. **Model loading** - Load selected FunASR model (cached locally)
8. **Transcription** - Run ASR with appropriate parameters
9. **Formatting** - Output in requested format
10. **Cleanup** - Remove temporary files

### Model Components

**Paraformer Pipeline:**
- **ASR Model**: Paraformer-large (Chinese optimized)
- **VAD Model**: FSMN-VAD (voice activity detection)
- **Punctuation**: CT-Transformer
- **Speaker**: CAM++ (speaker diarization)

**SenseVoice Pipeline:**
- **Unified Model**: SenseVoiceSmall (ASR + VAD + punctuation in one)
- No separate VAD/PUNC/SPK models needed
- No speaker diarization (no timestamp output)

### File Locations

- **Models cached in**: Platform-specific directory
  - macOS: `~/Library/Application Support/asr-skill/models/`
  - Windows: `%APPDATA%/asr-skill/models/`
  - Linux: `~/.local/share/asr-skill/models/`
- **Output defaults to**: same directory as input
- **Temp files**: auto-cleaned after processing

## Troubleshooting

### Common Issues

**"FFmpeg not found"**
- FFmpeg auto-installed via imageio-ffmpeg
- Check internet connection for first run

**"CUDA out of memory"**
- System falls back to CPU automatically
- Try SenseVoice model for CPU-friendly transcription: `-m sensevoice`

**"No speakers detected"**
- Speaker diarization requires Paraformer and multi-speaker audio
- SenseVoice does not support speaker diarization
- Single speaker audio shows "Speaker A" only

**Slow on CPU with Paraformer**
- Use SenseVoice instead: set `asr_model = sensevoice` in config.txt
- Or use CLI flag: `-m sensevoice`
- SenseVoice is ~6x faster on CPU

**First run downloads**
- Paraformer: ~1.3 GB download (GPU recommended)
- SenseVoice: ~200 MB download (CPU-friendly)

## Additional Resources

### Reference Files

For detailed format specifications:
- **`references/output-formats.md`** - Complete format documentation

### Scripts

Utility scripts for batch processing:
- **`scripts/transcribe.py`** - Batch transcription script

### Examples

Working examples:
- **`examples/basic_usage.py`** - Python API examples
- **`examples/cli_examples.sh`** - CLI usage examples

## Requirements

- Python >= 3.10
- FunASR (auto-installed)
- FFmpeg (auto-installed via imageio-ffmpeg for video)

## Notes

- First run downloads models (200 MB ~ 1.3 GB depending on engine)
- All processing happens locally for privacy
- Chinese language optimized for v1
- SenseVoice recommended for CPU-only systems
- Paraformer recommended for GPU systems (best accuracy + speaker diarization)

