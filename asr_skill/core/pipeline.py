"""Main transcription pipeline module.

This module provides the core transcription function that runs FunASR
inference on preprocessed audio files.

Supported ASR engines:
    - paraformer: Paraformer-Large with VAD + ASR + PUNC + optional SPK
    - sensevoice:  SenseVoiceSmall unified model (ASR + VAD + PUNC in one)

Key Features:
- Explicit device setting on every generate() call (prevents GPU fallback bug)
- Engine-specific generate parameters (batch_size_s for Paraformer, language for SenseVoice)
- Error handling with clear error messages

Pitfall Mitigation:
- The explicit `device=device` on every generate() call prevents GPU-to-CPU fallback
- The `batch_size_s=300` prevents memory explosion on long audio (>1 hour)
"""

from typing import Any, Callable


def transcribe(
    model: Any,
    audio_path: str,
    device: str,
    progress_callback: Callable[[int, int], None] | None = None,
    model_type: str = "paraformer",
) -> dict[str, Any] | None:
    """Run transcription on preprocessed audio file.

    This function executes the FunASR model inference on a preprocessed audio
    file. The audio must be 16kHz mono WAV format (use preprocess_audio first).

    Args:
        model: FunASR AutoModel instance (from create_pipeline).
        audio_path: Path to preprocessed 16kHz mono WAV file.
        device: Device string for inference ("cuda:0", "mps", or "cpu").
                MUST be passed explicitly to prevent GPU-to-CPU fallback bug.
        progress_callback: Optional callback for progress updates.
                Signature: callback(current: int, total: int)
                Called with sample counts during processing.
        model_type: ASR engine type — "paraformer" or "sensevoice".
                   Determines which generate() parameters to use.

    Returns:
        dict | None: Transcription result with keys:
            - text: Full transcription text
            - sentences: List of segment dicts with text, start, end, confidence
            - sentence_info: List of segment dicts with speaker labels (Paraformer only)
                Each segment has: sentence, start, end, spk (speaker ID), confidence
            Returns None if transcription produces no results.

    Raises:
        RuntimeError: Re-raised with clearer message for CUDA OOM or other errors.

    Notes:
        - Model must be pre-loaded via create_pipeline()
        - Audio must be preprocessed to 16kHz mono (use preprocess_audio)
        - Device must be passed explicitly to prevent silent GPU fallback
        - Paraformer: batch_size_s=300 handles long audio without memory explosion
        - SenseVoice: language="zh" for Chinese, no batch_size_s support

    Example:
        >>> model = create_pipeline("cuda:0", diarize=True, model_type="paraformer")
        >>> audio_path = preprocess_audio("input.mp3")
        >>> result = transcribe(model, audio_path, "cuda:0", model_type="paraformer")
        >>> print(result["sentence_info"][0]["spk"])  # Speaker ID: 0, 1, 2...

        >>> # SenseVoice
        >>> model = create_pipeline("cpu", model_type="sensevoice")
        >>> result = transcribe(model, audio_path, "cpu", model_type="sensevoice")
        >>> print(result["text"])  # Plain text, no speaker info
    """
    try:
        if model_type == "sensevoice":
            generate_kwargs = _build_sensevoice_kwargs(audio_path, device, progress_callback)
        else:
            generate_kwargs = _build_paraformer_kwargs(audio_path, device, progress_callback)

        result = model.generate(**generate_kwargs)
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


def _build_paraformer_kwargs(
    audio_path: str,
    device: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Build generate() kwargs for Paraformer-Large pipeline.

    Uses batch_size_s=300 for memory-efficient processing of long audio.
    """
    kwargs: dict[str, Any] = {
        "input": audio_path,
        "batch_size_s": 300,  # 300 seconds per batch for long audio
        "device": device,  # EXPLICIT: prevents GPU-to-CPU fallback bug
    }
    if progress_callback is not None:
        kwargs["callback"] = progress_callback
    return kwargs


def _build_sensevoice_kwargs(
    audio_path: str,
    device: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Build generate() kwargs for SenseVoiceSmall pipeline.

    SenseVoice uses language="zh" for Chinese and does not support
    batch_size_s (the unified model handles segmentation internally).
    """
    kwargs: dict[str, Any] = {
        "input": audio_path,
        "language": "zh",  # Chinese; use "auto" for auto-detection
        "device": device,
    }
    if progress_callback is not None:
        kwargs["callback"] = progress_callback
    return kwargs
