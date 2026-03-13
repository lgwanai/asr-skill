"""ASR Skill - Audio Speech Recognition Package.

This package provides a simple Python API for transcribing audio files
to text with automatic punctuation and word-level timestamps.

Quick Start:
    >>> from asr_skill import transcribe
    >>> result = transcribe("audio.mp3")
    >>> print(result["text"])

Supported Formats:
    - MP3, WAV, M4A, FLAC

Output Formats:
    - txt: Plain text with inline timestamps [HH:MM:SS.mmm]
    - json: Structured JSON with segment-level metadata

Features:
    - Automatic hardware detection (CUDA GPU, Apple MPS, CPU fallback)
    - Auto-download and cache models on first use
    - Long audio support with VAD-based segmentation
    - Chinese-optimized recognition with punctuation
"""

from pathlib import Path

from asr_skill.core.device import get_device_with_fallback
from asr_skill.core.models import create_pipeline
from asr_skill.core.pipeline import transcribe as _transcribe
from asr_skill.postprocessing.formatters import format_json, format_txt
from asr_skill.preprocessing.audio import SUPPORTED_FORMATS, preprocess_audio
from asr_skill.utils.paths import get_output_path

__version__ = "0.1.0"

__all__ = ["transcribe", "SUPPORTED_FORMATS"]


def transcribe(
    input_file: str, output_dir: str | None = None, format: str = "txt"
) -> dict[str, str | list]:
    """Transcribe audio file to text.

    This is the main entry point for the ASR Skill package. It handles the
    complete transcription pipeline: hardware detection, model loading,
    audio preprocessing, transcription, and output formatting.

    Args:
        input_file: Path to audio file. Supports MP3, WAV, M4A, FLAC formats.
        output_dir: Output directory for transcription file.
                    Default: same directory as input file.
        format: Output format - "txt" or "json". Default: "txt".

    Returns:
        dict with keys:
            - text: Full transcription text (str)
            - segments: List of segment dicts with text, start, end, confidence (list)
            - output_path: Path to the output file (str)

    Raises:
        ValueError: If input file doesn't exist or has unsupported format.
        RuntimeError: If transcription fails (CUDA OOM, corrupted audio, etc.)

    Notes:
        - Models are auto-downloaded on first use (several GB)
        - GPU-to-CPU fallback triggers a warning
        - Output file is written even if transcription fails mid-way

    Example:
        >>> from asr_skill import transcribe
        >>> result = transcribe("meeting.mp3")
        >>> print(f"Output saved to: {result['output_path']}")
        >>> print(f"Transcribed text: {result['text'][:100]}...")

        >>> # Custom output location and JSON format
        >>> result = transcribe("audio.mp3", output_dir="./transcripts", format="json")
        >>> print(result["segments"][0])  # First segment with timestamps
    """
    # Detect device with fallback warning
    device, fallback = get_device_with_fallback()

    # Load model (cached after first load)
    model = create_pipeline(device)

    # Preprocess audio to 16kHz mono WAV
    audio_path = preprocess_audio(input_file)

    # Run transcription
    result = _transcribe(model, audio_path, device)

    if result is None:
        raise RuntimeError(f"Transcription returned no results for {input_file}")

    # Determine output path
    output_file = get_output_path(input_file, output_dir, format)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Format and write output
    if format == "txt":
        output_text = format_txt(result)
    else:
        output_text = format_json(result)

    output_file.write_text(output_text, encoding="utf-8")

    return {
        "text": result.get("text", ""),
        "segments": result.get("sentences", []),
        "output_path": str(output_file),
    }
