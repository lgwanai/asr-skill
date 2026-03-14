# ASR Skill

Local speech recognition with high-accuracy Chinese transcription.

## Installation

### 1. Install Python Package

First, install the core package and dependencies:

```bash
# Clone the repository
git clone https://github.com/your-repo/asr-skill.git
cd asr-skill

# Install in editable mode
pip install -e .
```

### 2. Install FFmpeg

Required for audio/video processing:

- **macOS**: `brew install ffmpeg`
- **Ubuntu**: `sudo apt install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Integration with AI Assistants

This skill is designed to be used by AI agents (Trae, Cursor, Claude) to perform transcription tasks on your behalf.

### � Quick Install via Chat

If you are using **Cursor**, **Claude Code**, or **OpenClaw**, you can simply paste the following into the chat to install the skill:

```
https://github.com/lgwanai/asr-skill help me install asr skill
```

### � Package for Distribution

You can create a versioned zip package of the skill:

```bash
python3 scripts/package_skill.py
# Output: dist/asr-skill-YYYYMMDD.zip
```

### 🤖 IDE Setup

#### Trae

1. **Unzip**: Extract the `asr-skill-*.zip` into your project's `skills/` directory (e.g., `your-project/skills/asr`).
2. **Context**: The `skills/asr/SKILL.md` file defines the skill.
3. **Usage**: In Trae's chat, you can now ask:
   > "Help me transcribe the meeting recording in `audio.mp3`."
   
   Trae will read the `SKILL.md` and use the python scripts to perform the task.

#### Cursor

1. **Unzip**: Extract the skill into your project workspace.
2. **Configure**: Copy the content of `skills/asr/SKILL.md` into your `.cursorrules` file.
3. **Usage**: The `.cursorrules` context will guide Cursor to use the `scripts/transcribe.py` script when you ask for transcription.

#### Claude (Projects)

1. **Upload**: Upload the `skills/asr/scripts/transcribe.py` and `SKILL.md` to your Claude Project.
2. **Instructions**: Copy the content of `SKILL.md` into the **Project Instructions**.
3. **Note**: Claude Web cannot execute local scripts directly. It will generate the correct commands for you to run in your terminal.

## Usage

### CLI

```bash
asr-skill input.mp3              # Transcribe audio file
asr-skill video.mp4              # Transcribe video file
asr-skill input.mp3 -o ./output  # Custom output directory
asr-skill input.mp3 -f json      # JSON output format
```

### Script (for Agents)

The agents will primarily use this script:

```bash
python3 skills/asr/scripts/transcribe.py input.mp3
```

### Python API

```python
from asr_skill import transcribe

result = transcribe("audio.mp3")
print(result["text"])
print(f"Speakers: {result.get('speakers', [])}")
```

## Supported Formats

- Audio: MP3, WAV, M4A, FLAC
- Video: MP4, AVI, MKV

## Features

- Automatic hardware detection (CUDA GPU, Apple MPS, CPU fallback)
- Auto-download and cache models on first use
- Long audio support with VAD-based segmentation
- Chinese-optimized recognition with punctuation
- Speaker diarization (multi-speaker identification)
- Video file support with automatic audio extraction

## Model Storage

The large models (~2-3GB) required for ASR and speaker diarization are automatically downloaded on first use.

**Default Location**: `./models` (relative to your current working directory)

You can customize this by setting the `model_dir` parameter in the Python API, but the CLI/Skill currently uses the default project-local directory.

