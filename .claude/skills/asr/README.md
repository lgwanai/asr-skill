# ASR Transcription Skill

A Claude Code skill for transcribing audio and video files to text with speaker diarization.

## Installation

1. Copy the `asr` directory to your Claude Code skills directory:
   ```bash
   cp -r .claude/skills/asr ~/.claude/skills/
   ```

2. Install the asr-skill package:
   ```bash
   pip install -e .
   ```

## Usage

Once installed, Claude will automatically use this skill when you ask to transcribe audio or video files.

### Example Prompts

- "Transcribe this audio file: meeting.mp3"
- "Convert this video to subtitles: presentation.mp4"
- "Generate SRT subtitles from this recording"
- "Who are the speakers in this audio?"

## Features

- **Multi-format support**: MP3, WAV, M4A, FLAC (audio) and MP4, AVI, MKV (video)
- **Speaker diarization**: Automatically identifies and labels different speakers
- **Multiple output formats**: TXT, JSON, SRT, ASS, Markdown
- **Progress indication**: Shows real-time progress during transcription
- **Local processing**: All processing happens locally for privacy

## Requirements

- Python >= 3.10
- FunASR (auto-installed)
- FFmpeg (auto-installed via imageio-ffmpeg for video processing)
