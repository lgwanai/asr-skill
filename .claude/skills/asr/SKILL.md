---
name: asr
description: Transcribe audio and video files to text with speaker diarization. This skill should be used when the user wants to transcribe audio or video files, convert speech to text, or generate subtitles/captions from media files. Supports MP3, WAV, M4A, FLAC audio formats and MP4, AVI, MKV video formats. Outputs include TXT, JSON, SRT, ASS, and Markdown formats with speaker labels and timestamps.
---

# ASR Transcription Skill

Transcribe audio and video files to text using local FunASR models with automatic hardware detection, speaker diarization, and multiple output formats.

## Purpose

Provide high-accuracy Chinese speech recognition with speaker identification, supporting long audio/video files while preserving data privacy through local processing.

## When to Use

Use this skill when the user:
- Wants to transcribe an audio file (MP3, WAV, M4A, FLAC)
- Wants to transcribe a video file (MP4, AVI, MKV)
- Needs subtitles or captions generated from media
- Wants to identify different speakers in audio
- Needs timestamped transcription output

## Usage

### CLI Usage

```bash
# Basic transcription (outputs TXT by default)
asr-skill path/to/audio.mp3

# Specify output format
asr-skill path/to/audio.mp3 -f json
asr-skill path/to/audio.mp3 -f srt   # SubRip subtitles
asr-skill path/to/audio.mp3 -f ass   # ASS/SSA subtitles
asr-skill path/to/audio.mp3 -f md    # Markdown

# Custom output directory
asr-skill path/to/audio.mp3 -o ./output -f json

# Video files are automatically handled
asr-skill path/to/video.mp4 -f srt
```

### Python API Usage

```python
from asr_skill import transcribe

# Basic transcription
result = transcribe("audio.mp3")
print(result["text"])

# With specific format
result = transcribe("audio.mp3", format="json")
print(result["segments"])

# Get speaker information
result = transcribe("meeting.mp4", format="json")
print(f"Speakers: {result.get('speakers', [])}")

# Disable speaker diarization
result = transcribe("audio.mp3", diarize=False)
```

## Output Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| txt | .txt | Plain text with timestamps and speaker labels |
| json | .json | Structured JSON with segments, words, confidence scores |
| srt | .srt | SubRip subtitle format for video |
| ass | .ass | ASS/SSA subtitles with speaker styling |
| md | .md | Markdown with speaker sections |

## Features

### Hardware Auto-Detection
Automatically detects and uses the best available hardware:
- CUDA GPU (NVIDIA)
- Apple MPS (Apple Silicon)
- CPU fallback

### Speaker Diarization
Identifies and labels different speakers:
- Speaker A, Speaker B, Speaker C, etc.
- Per-segment timestamps
- Overlap detection marked with [OVERLAP]

### Long Audio Support
Handles audio files longer than 1 hour through:
- VAD-based intelligent segmentation
- Memory-efficient processing

### Progress Indication
Shows real-time progress during transcription:
- Percentage complete
- Estimated time remaining

## Requirements

The package requires:
- Python >= 3.10
- FunASR models (auto-downloaded on first use)
- FFmpeg (for video file processing, auto-installed via imageio-ffmpeg)

## Notes

- Models are cached locally in `./models/` directory
- First run downloads models (~1GB total)
- Processing speed depends on hardware
- Chinese language optimized for v1

## Bundled Resources

### Scripts
- `scripts/transcribe.py` - Quick transcription script for batch processing

### References
- `references/output-formats.md` - Detailed output format specifications for all formats
