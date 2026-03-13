"""ASR Skill - Audio Speech Recognition Package.

This package provides a simple Python API for transcribing audio/video files
to text with automatic punctuation, word-level timestamps, and speaker diarization.

Quick Start:
    >>> from asr_skill import transcribe
    >>> result = transcribe("audio.mp3")
    >>> print(result["text"])

Supported Formats:
    - Audio: MP3, WAV, M4A, FLAC
    - Video: MP4, AVI, MKV

Output Formats:
    - txt: Plain text with inline timestamps and speaker labels
    - json: Structured JSON with segment-level metadata including speaker IDs
    - srt: SRT subtitle format with speaker labels
    - ass: ASS subtitle format with speaker-specific styling
    - md: Markdown document with speaker sections

Features:
    - Automatic hardware detection (CUDA GPU, Apple MPS, CPU fallback)
    - Auto-download and cache models on first use
    - Long audio support with VAD-based segmentation
    - Chinese-optimized recognition with punctuation
    - Speaker diarization (multi-speaker identification)
    - Video file support with automatic audio extraction
"""

from pathlib import Path
from typing import Callable

from asr_skill.core.device import get_device_with_fallback
from asr_skill.core.models import create_pipeline
from asr_skill.core.pipeline import transcribe as _transcribe
from asr_skill.postprocessing.formatters import (
    format_json, format_txt, format_srt, format_ass, format_markdown
)
from asr_skill.preprocessing.audio import SUPPORTED_FORMATS, preprocess_input
from asr_skill.preprocessing.video import SUPPORTED_VIDEO_FORMATS
from asr_skill.utils.paths import get_output_path

__version__ = "0.1.0"

__all__ = ["transcribe", "SUPPORTED_FORMATS", "SUPPORTED_VIDEO_FORMATS"]


def transcribe(
    input_file: str,
    output_dir: str | None = None,
    format: str = "txt",
    diarize: bool = True,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, str | list]:
    """Transcribe audio or video file to text with optional speaker diarization.

    This is the main entry point for the ASR Skill package. It handles the
    complete transcription pipeline: hardware detection, model loading,
    audio/video preprocessing, transcription, and output formatting.

    Args:
        input_file: Path to audio or video file.
                    Audio: MP3, WAV, M4A, FLAC
                    Video: MP4, AVI, MKV
        output_dir: Output directory for transcription file.
                    Default: same directory as input file.
        format: Output format - "txt", "json", "srt", "ass", or "md". Default: "txt".
        diarize: Enable speaker diarization. Default: True.
                 When enabled, output includes speaker labels (Speaker A, B, C...).
        progress_callback: Optional callback for progress updates.
                 Signature: callback(current: int, total: int)
                 Called with sample counts during processing.

    Returns:
        dict with keys:
            - text: Full transcription text (str)
            - segments: List of segment dicts with text, start, end, confidence (list)
            - output_path: Path to the output file (str)
            - speakers: List of unique speaker labels (when diarize=True)

    Raises:
        ValueError: If input file doesn't exist or has unsupported format.
        RuntimeError: If transcription fails (CUDA OOM, corrupted audio, etc.)

    Example:
        >>> from asr_skill import transcribe
        >>> result = transcribe("meeting.mp4")  # Video file
        >>> print(f"Output saved to: {result['output_path']}")
        >>> print(f"Speakers found: {result.get('speakers', [])}")

        >>> # Disable speaker diarization
        >>> result = transcribe("audio.mp3", diarize=False)
    """
    # Detect device with fallback warning
    device, fallback = get_device_with_fallback()

    # Load model with optional speaker diarization
    model = create_pipeline(device, diarize=diarize)

    # Preprocess input (handles both audio and video)
    with preprocess_input(input_file) as audio_path:
        # Run transcription
        result = _transcribe(model, audio_path, device, progress_callback)

    if result is None:
        raise RuntimeError(f"Transcription returned no results for {input_file}")

    # Determine output path
    output_file = get_output_path(input_file, output_dir, format)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Format and write output
    format_map = {
        "txt": format_txt,
        "json": format_json,
        "srt": format_srt,
        "ass": format_ass,
        "md": format_markdown,
    }

    formatter = format_map.get(format, format_txt)
    output_text = formatter(result)

    output_file.write_text(output_text, encoding="utf-8")

    # Build response
    response = {
        "text": result.get("text", ""),
        "segments": result.get("sentence_info") or result.get("sentences", []),
        "output_path": str(output_file),
    }

    # Add speaker list if diarization was enabled
    if diarize and "sentence_info" in result:
        from asr_skill.postprocessing.speakers import format_speaker_label

        speaker_ids = set(
            seg.get("spk") for seg in result["sentence_info"] if "spk" in seg
        )
        response["speakers"] = [format_speaker_label(sid) for sid in sorted(speaker_ids)]

    return response
