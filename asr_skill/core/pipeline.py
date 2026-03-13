"""Main transcription pipeline module.

This module provides the core transcription function that runs FunASR
inference on preprocessed audio files.

Key Features:
- Explicit device setting on every generate() call (prevents GPU fallback bug)
- Batch size configuration for long audio handling
- Error handling with clear error messages

Pitfall Mitigation:
- The explicit `device=device` on every generate() call prevents GPU-to-CPU fallback
- The `batch_size_s=300` prevents memory explosion on long audio (>1 hour)
"""

from typing import Any


def transcribe(model: Any, audio_path: str, device: str) -> dict[str, Any] | None:
    """Run transcription on preprocessed audio file.

    This function executes the FunASR model inference on a preprocessed audio
    file. The audio must be 16kHz mono WAV format (use preprocess_audio first).

    Args:
        model: FunASR AutoModel instance (from create_pipeline).
        audio_path: Path to preprocessed 16kHz mono WAV file.
        device: Device string for inference ("cuda:0", "mps", or "cpu").
                MUST be passed explicitly to prevent GPU-to-CPU fallback bug.

    Returns:
        dict | None: Transcription result with keys:
            - text: Full transcription text
            - sentences: List of segment dicts with text, start, end, confidence
            - sentence_info: List of segment dicts with speaker labels (when diarization enabled)
                Each segment has: sentence, start, end, spk (speaker ID), confidence
            Returns None if transcription produces no results.

    Raises:
        RuntimeError: Re-raised with clearer message for CUDA OOM or other errors.

    Notes:
        - Model must be pre-loaded via create_pipeline()
        - Audio must be preprocessed to 16kHz mono (use preprocess_audio)
        - Device must be passed explicitly to prevent silent GPU fallback
        - batch_size_s=300 handles long audio without memory explosion

    Example:
        >>> model = create_pipeline("cuda:0", diarize=True)
        >>> audio_path = preprocess_audio("input.mp3")
        >>> result = transcribe(model, audio_path, "cuda:0")
        >>> print(result["sentence_info"][0]["spk"])  # Speaker ID: 0, 1, 2...
    """
    try:
        result = model.generate(
            input=audio_path,
            batch_size_s=300,  # 300 seconds per batch for long audio
            device=device,  # EXPLICIT: prevents GPU-to-CPU fallback bug
        )
        return result[0] if result else None
    except RuntimeError as e:
        # Re-raise with clearer context for common errors
        error_msg = str(e)
        if "CUDA out of memory" in error_msg:
            raise RuntimeError(
                f"CUDA out of memory while transcribing {audio_path}. "
                "Try using a smaller batch_size_s or process a shorter audio file."
            ) from e
        raise RuntimeError(
            f"Transcription failed for {audio_path}: {error_msg}"
        ) from e
