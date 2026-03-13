"""Audio preprocessing module for ASR pipeline.

This module handles audio format conversion and preprocessing to ensure
all audio input is properly formatted for the ASR model.

Preprocessing Pipeline:
1. Load audio file (supports MP3, WAV, M4A, FLAC formats)
2. Convert stereo to mono (CRITICAL: prevents dual-channel errors)
3. Resample to 16kHz (required by FunASR models)
4. Write to temporary WAV file for model inference
"""

import tempfile
from pathlib import Path

import librosa
import soundfile as sf

# Supported audio formats
SUPPORTED_FORMATS = [".mp3", ".wav", ".m4a", ".flac"]


def preprocess_audio(input_path: str) -> str:
    """Preprocess audio file for ASR model inference.

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
