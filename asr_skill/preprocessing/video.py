"""Video audio extraction module for ASR pipeline.

This module handles audio extraction from video files using FFmpeg CLI.
Extracted audio is converted to 16kHz mono WAV format for ASR processing.

Video Support:
- Supported formats: MP4, AVI, MKV (most common video containers)
- Extraction: FFmpeg CLI via subprocess module
- Dependency: imageio-ffmpeg provides bundled FFmpeg binary
- Cleanup: Context manager pattern ensures temp file deletion
"""

import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

# Supported video formats (most common containers)
SUPPORTED_VIDEO_FORMATS = [".mp4", ".avi", ".mkv"]


def is_video_file(file_path: str) -> bool:
    """Check if file is a supported video format.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if the file extension matches a supported video format.

    Example:
        >>> is_video_file("video.mp4")
        True
        >>> is_video_file("audio.mp3")
        False
    """
    ext = Path(file_path).suffix.lower()
    return ext in SUPPORTED_VIDEO_FORMATS


def get_ffmpeg_path() -> str:
    """Get FFmpeg executable path.

    Prefers system FFmpeg if available, falls back to imageio-ffmpeg
    bundled binary for automatic installation.

    Returns:
        Path to FFmpeg executable.

    Raises:
        RuntimeError: If FFmpeg is not found in system PATH and
            imageio-ffmpeg is not installed.
    """
    # Try system FFmpeg first
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return "ffmpeg"
    except FileNotFoundError:
        pass

    # Fall back to imageio-ffmpeg bundled binary
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as e:
        raise RuntimeError(
            "FFmpeg not found. Either install FFmpeg on your system, "
            "or install imageio-ffmpeg: pip install imageio-ffmpeg"
        ) from e


@contextmanager
def extract_audio_from_video(video_path: str):
    """Extract audio from video file with automatic cleanup.

    Context manager that extracts audio from a video file and converts
    it to 16kHz mono WAV format suitable for ASR processing. The extracted
    audio file is automatically deleted when the context exits.

    Args:
        video_path: Path to the input video file (MP4, AVI, MKV).

    Yields:
        str: Path to the extracted temporary WAV file (16kHz mono).

    Raises:
        ValueError: If the video file doesn't exist or has unsupported format.
        RuntimeError: If FFmpeg extraction fails.

    Example:
        >>> with extract_audio_from_video("video.mp4") as audio_path:
        ...     # Use audio_path for transcription
        ...     result = transcribe(audio_path)
        >>> # Audio file is automatically deleted after context exit

    Notes:
        - Extracted audio format: 16kHz mono WAV (16-bit PCM)
        - Temp file is created in system temp directory
        - Guaranteed cleanup via try/finally in context manager
    """
    video_path_obj = Path(video_path)

    # Validate file exists
    if not video_path_obj.exists():
        raise ValueError(f"Video file not found: {video_path}")

    # Validate file extension
    if not is_video_file(video_path):
        raise ValueError(
            f"Unsupported video format: {video_path_obj.suffix}. "
            f"Supported formats: {', '.join(SUPPORTED_VIDEO_FORMATS)}"
        )

    # Get FFmpeg path
    ffmpeg_path = get_ffmpeg_path()

    # Create temp file for audio output
    temp_audio = tempfile.mktemp(suffix=".wav")

    try:
        # FFmpeg command: extract audio, convert to 16kHz mono WAV
        cmd = [
            ffmpeg_path,
            "-i",
            video_path,  # Input video file
            "-vn",  # No video output
            "-acodec",
            "pcm_s16le",  # 16-bit PCM codec
            "-ar",
            "16000",  # 16kHz sample rate
            "-ac",
            "1",  # Mono channel
            "-y",  # Overwrite output
            temp_audio,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg audio extraction failed for {video_path}:\n"
                f"stderr: {result.stderr}\n"
                f"stdout: {result.stdout}"
            )

        yield temp_audio

    finally:
        # Guaranteed cleanup of temp file
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
