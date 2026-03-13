"""Audio preprocessing module for ASR pipeline.

This module handles audio format conversion and preprocessing to ensure
all audio input is properly formatted for the ASR model.

Supported Input:
- Audio formats: MP3, WAV, M4A, FLAC
- Video formats: MP4, AVI, MKV (audio extracted automatically)

Preprocessing Pipeline:
1. Video files: Extract audio via FFmpeg
2. Load audio file (supports MP3, WAV, M4A, FLAC formats)
3. Convert stereo to mono (CRITICAL: prevents dual-channel errors)
4. Resample to 16kHz (required by FunASR models)
5. Write to temporary WAV file for model inference
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import librosa
import soundfile as sf

from asr_skill.preprocessing.video import (
    SUPPORTED_VIDEO_FORMATS,
    extract_audio_from_video,
    is_video_file,
)

# Supported audio formats
SUPPORTED_FORMATS = [".mp3", ".wav", ".m4a", ".flac"]


@contextmanager
def preprocess_input(input_path: str) -> Generator[str, None, None]:
    """Preprocess audio or video file for ASR model inference.

    This is a context manager that handles:
    1. Video files: Extract audio, preprocess, auto-cleanup
    2. Audio files: Preprocess to 16kHz mono WAV

    Args:
        input_path: Path to input file (audio or video)

    Yields:
        str: Path to preprocessed 16kHz mono WAV file

    Example:
        >>> with preprocess_input("video.mp4") as audio_path:
        ...     result = transcribe(model, audio_path, device)
    """
    input_path_obj = Path(input_path)

    # Validate file exists
    if not input_path_obj.exists():
        raise ValueError(f"File not found: {input_path}")

    # Handle video files
    if is_video_file(input_path):
        with extract_audio_from_video(input_path) as video_audio:
            # Further preprocess extracted audio
            audio_path = _preprocess_audio_file(video_audio)
            try:
                yield audio_path
            finally:
                # Cleanup preprocessed temp file
                Path(audio_path).unlink(missing_ok=True)
    else:
        # Handle audio files
        audio_path = _preprocess_audio_file(input_path)
        try:
            yield audio_path
        finally:
            # Cleanup preprocessed temp file
            Path(audio_path).unlink(missing_ok=True)


def preprocess_audio(input_path: str) -> str:
    """Preprocess audio file for ASR model inference (legacy function).

    This function is kept for backward compatibility. Prefer using
    preprocess_input() context manager for video support.

    Args:
        input_path: Path to the input audio file. Supports MP3, WAV, M4A, FLAC.

    Returns:
        str: Path to the preprocessed temporary WAV file (16kHz mono).

    Note:
        The caller is responsible for cleaning up the returned temp file.
    """
    return _preprocess_audio_file(input_path)


def _preprocess_audio_file(input_path: str) -> str:
    """Internal: Preprocess audio file to 16kHz mono WAV.

    Converts any supported audio format to 16kHz mono WAV, which is the
    required input format for FunASR models.

    Args:
        input_path: Path to the input audio file. Supports MP3, WAV, M4A, FLAC.

    Returns:
        str: Path to the preprocessed temporary WAV file (16kHz mono).

    Raises:
        ValueError: If the file doesn't exist or has an unsupported format.

    Notes:
        - The returned temp file should be cleaned up by the caller after use
        - librosa.load with mono=True handles stereo-to-mono conversion
        - 16kHz sample rate is required by FunASR Paraformer models
    """
    input_path_obj = Path(input_path)

    # Validate file exists
    if not input_path_obj.exists():
        raise ValueError(f"Audio file not found: {input_path}")

    # Validate file extension
    file_ext = input_path_obj.suffix.lower()
    if file_ext not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported audio format: {file_ext}. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )

    # Load audio with librosa
    # sr=None preserves original sample rate for resampling check
    # mono=True converts stereo to mono (CRITICAL for FunASR)
    y, sr = librosa.load(input_path, sr=None, mono=True)

    # Resample to 16kHz if needed
    if sr != 16000:
        y = librosa.resample(y, orig_sr=sr, target_sr=16000)

    # Write to temporary WAV file
    temp_path = tempfile.mktemp(suffix=".wav")
    sf.write(temp_path, y, 16000)

    return temp_path
