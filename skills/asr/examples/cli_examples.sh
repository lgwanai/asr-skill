#!/bin/bash
# CLI usage examples for the ASR skill

# Basic transcription (auto-detects best model for your hardware)
asr-skill audio.mp3

# Model selection
asr-skill audio.mp3 -m sensevoice   # Use SenseVoice (faster on CPU)
asr-skill audio.mp3 -m paraformer   # Use Paraformer (best accuracy, needs GPU)
asr-skill audio.mp3 -m auto         # Auto-select (default behavior)

# Transcribe with JSON output
asr-skill audio.mp3 -f json

# Transcribe with SRT subtitles
asr-skill video.mp4 -f srt

# Transcribe with ASS styled subtitles
asr-skill meeting.mp4 -f ass

# Transcribe with Markdown output
asr-skill podcast.mp3 -f md

# Custom output directory
asr-skill audio.mp3 -o ./transcripts -f json

# Video file transcription (audio extracted automatically)
asr-skill presentation.mp4 -f srt -o ./subtitles

# Check version
asr-skill --version

# Get help
asr-skill --help
