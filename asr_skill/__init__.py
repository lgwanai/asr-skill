"""ASR Skill - Audio Speech Recognition Package.

This package provides a simple Python API for transcribing audio/video files
to text with automatic punctuation, word-level timestamps, and speaker diarization.

Quick Start:
    >>> from asr_skill import transcribe
    >>> result = transcribe("audio.mp3")
    >>> print(result["text"])

Operation Modes:
    - local: Run ASR models locally via FunASR (default, offline, private)
    - api:   Call Xiaomi MiMo ASR API via chat completions (no local GPU needed, requires network)

Local Mode Engines:
    - paraformer: High-accuracy Chinese ASR with speaker diarization (best on GPU)
    - sensevoice:  Lightweight multi-lingual ASR, faster on CPU (no diarization)
    - auto:        Auto-select based on available hardware (default)

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
    - Dual mode: local (FunASR) and API (cloud)
    - Automatic hardware detection (CUDA GPU, Apple MPS, CPU fallback)
    - Platform-aware model selection (SenseVoice for CPU, Paraformer for GPU)
    - Xiaomi MiMo ASR API integration (Base64 data URL, chat completions format)
    - Auto-download and cache models on first use (local mode)
    - Long audio support with VAD-based segmentation
    - Chinese-optimized recognition with punctuation
    - Speaker diarization (Paraformer local / API-dependent)
    - Video file support with automatic audio extraction
"""

import os
import sys
from pathlib import Path
from typing import Callable

from asr_skill.core.device import get_device_with_fallback
from asr_skill.core.models import (
    create_pipeline,
    get_model_info,
    get_platform_info,
    resolve_model_type,
)
from asr_skill.core.pipeline import transcribe as _transcribe_local
from asr_skill.postprocessing.formatters import (
    format_json, format_txt, format_srt, format_ass, format_markdown
)
from asr_skill.postprocessing.speakers import (
    UNIDENTIFIED_SPEAKER,
    format_speaker_label,
    has_diarization_data,
)
from asr_skill.preprocessing.audio import SUPPORTED_FORMATS, preprocess_input
from asr_skill.preprocessing.video import SUPPORTED_VIDEO_FORMATS
from asr_skill.utils.paths import get_output_path
from asr_skill.utils.config import load_config

__version__ = "0.2.0"

__all__ = [
    "transcribe",
    "SUPPORTED_FORMATS",
    "SUPPORTED_VIDEO_FORMATS",
    "load_config",
    "get_model_info",
    "get_platform_info",
    "UNIDENTIFIED_SPEAKER",
    "has_diarization_data",
]


def transcribe(
    input_file: str,
    output_dir: str | None = None,
    format: str | None = None,
    diarize: bool = True,
    model_type: str | None = None,
    mode: str | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, str | list]:
    """Transcribe audio or video file to text with optional speaker diarization.

    This is the main entry point for the ASR Skill package. It supports two
    operation modes:

    **Local mode** (default): Run ASR locally with FunASR models.
    - Requires GPU for best performance (CPU works with SenseVoice)
    - Fully offline, no data leaves your machine
    - Supports speaker diarization with Paraformer

    **API mode**: Call Xiaomi MiMo ASR API (mimo-v2.5-asr).
    - No local GPU/model download needed
    - Requires network access and MiMo API key
    - Audio sent as Base64 data URL via chat completions endpoint
    - Max ~7 MB raw audio (~10 MB Base64); longer audio → use local mode
    - Configure via config.txt "api" section or MIMO_API_KEY env var

    Args:
        input_file: Path to audio or video file.
                    Audio: MP3, WAV, M4A, FLAC
                    Video: MP4, AVI, MKV
        output_dir: Output directory for transcription file.
                    Default: from config.txt or same directory as input file.
        format: Output format - "txt", "json", "srt", "ass", or "md".
                Default: from config.txt or "txt".
        diarize: Enable speaker diarization. Default: True.
                 Note: Local SenseVoice and some APIs don't support this.
        model_type: (Local mode) ASR engine — "paraformer", "sensevoice", or "auto".
                    Default (None): read from config.txt ("auto" if not set).
        mode: Operation mode — "local" or "api".
              Default (None): read from config.txt ("local" if not set).
        progress_callback: Optional callback for progress updates.
                 Signature: callback(current: int, total: int)

    Returns:
        dict with keys:
            - text: Full transcription text (str)
            - segments: List of segment dicts with text, start, end, confidence
            - output_path: Path to the output file (str)
            - speakers: List of speaker labels
            - mode: "local" or "api"
            - model_used: The ASR model used (str)
            - device: The compute device used (local mode) or "api" (API mode)
            - diarization_supported: Whether model supports diarization
            - diarization_enabled: Whether diarization was active

    Raises:
        ValueError: If input file doesn't exist, unsupported format, or bad config.
        RuntimeError: If transcription fails or API returns errors.

    Example:
        >>> from asr_skill import transcribe

        >>> # Local mode (auto-detect model)
        >>> result = transcribe("meeting.mp4")
        >>> print(f"Mode: {result['mode']}, Model: {result['model_used']}")

        >>> # API mode (needs MIMO_API_KEY in config.txt or env var)
        >>> result = transcribe("lecture.mp3", mode="api")
        >>> print(f"Text: {result['text']}")

        >>> # API mode with speaker diarization
        >>> result = transcribe("meeting.wav", mode="api", diarize=True)
    """
    config = load_config()

    # ── Resolve mode ──────────────────────────────────────────────────────
    resolved_mode = mode or config.get("mode", "local")
    if resolved_mode not in ("local", "api"):
        raise ValueError(
            f"Unknown mode: '{resolved_mode}'. Expected 'local' or 'api'."
        )

    # ── Resolve format and output ─────────────────────────────────────────
    format = format or config.get("output_format", "txt")
    output_dir = output_dir or config.get("output_dir") or None

    # ── Route to implementation ───────────────────────────────────────────
    if resolved_mode == "api":
        return _transcribe_via_api(
            input_file=input_file,
            output_dir=output_dir,
            format=format,
            diarize=diarize,
            config=config,
            progress_callback=progress_callback,
        )
    else:
        if model_type is None:
            model_type = config.get("asr_model", "auto")
        return _transcribe_local_mode(
            input_file=input_file,
            output_dir=output_dir,
            format=format,
            diarize=diarize,
            model_type=model_type,
            progress_callback=progress_callback,
        )


# ── Local Mode Implementation ────────────────────────────────────────────────

def _transcribe_local_mode(
    input_file: str,
    output_dir: str | None,
    format: str,
    diarize: bool,
    model_type: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, str | list]:
    """Run transcription using local FunASR models."""
    # Detect device with fallback warning
    device, fallback = get_device_with_fallback()

    # Resolve model type (handles "auto" → platform-aware selection)
    resolved_model, resolution_reason = resolve_model_type(model_type, device)

    # Print model selection info
    print(f"[ASR] Mode: local")
    print(f"[ASR] Platform: {get_platform_info()['system']}/{get_platform_info()['arch']}")
    print(f"[ASR] Device: {device}")
    print(f"[ASR] Model: {resolved_model} ({resolution_reason})")

    model_info = get_model_info(resolved_model)
    diarization_supported = model_info.get("diarization_supported", False)

    # Check diarization support
    if diarize and not diarization_supported:
        print()
        print("=" * 56)
        print("  ⚠️  该模型不支持人声分离（Speaker Diarization）")
        print(f"  当前模型: {model_info.get('name', resolved_model)}")
        print(f"  原因: {model_info.get('description', '模型不支持')}")
        print(f"  所有语音将标记为 \"{UNIDENTIFIED_SPEAKER}\"")
        print(f"  如需人声分离，请使用 Paraformer 模型:")
        print(f"    CLI:  asr-skill input.mp3 -m paraformer")
        print(f"    API:  transcribe('input.mp3', model_type='paraformer')")
        print(f"    Config: 设置 \"asr_model\": \"paraformer\" 在 config.txt")
        print("=" * 56)
        print()
        diarize = False
    elif not diarization_supported:
        print(f"[ASR] 人声分离: 不支持（{model_info.get('name', resolved_model)} 无此功能）")
    else:
        print(f"[ASR] 人声分离: {'已启用' if diarize else '已禁用'}（{model_info.get('name', resolved_model)}）")

    print(
        f"[ASR] Loading {model_info.get('name', resolved_model)} "
        f"({model_info.get('size_approx', 'unknown size')})..."
    )

    # Load model
    model = create_pipeline(device, diarize=diarize, model_type=resolved_model)

    # Preprocess and transcribe
    with preprocess_input(input_file) as audio_path:
        result = _transcribe_local(
            model, audio_path, device,
            progress_callback=progress_callback,
            model_type=resolved_model,
        )

    if result is None:
        raise RuntimeError(f"Transcription returned no results for {input_file}")

    return _finalize_result(
        result=result,
        input_file=input_file,
        output_dir=output_dir,
        format=format,
        diarize=diarize,
        diarization_supported=diarization_supported,
        resolved_model=resolved_model,
        device=device,
        mode="local",
    )


# ── API Mode Implementation ──────────────────────────────────────────────────

def _transcribe_via_api(
    input_file: str,
    output_dir: str | None,
    format: str,
    diarize: bool,
    config: dict,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, str | list]:
    """Run transcription via remote ASR API."""
    from asr_skill.core.api_client import ASRAPIClient

    api_cfg = config.get("api", {})

    # Validate API config - MiMo uses fixed endpoint by default
    # api.url can be empty (defaults to https://api.xiaomimimo.com/v1)
    # Only api.key is required
    api_key = api_cfg.get("key", "")
    if not api_key:
        raise ValueError(
            "API mode requires 'api.key' in config.txt or MIMO_API_KEY env var.\n"
            "Set it in config.txt:\n"
            '  api.key = your-xiaomi-mimo-api-key\n'
            "Or via environment variable:\n"
            "  export MIMO_API_KEY=your-xiaomi-mimo-api-key\n"
            "Get your key at: https://platform.xiaomimimo.com/profile"
        )

    print(f"[ASR] Mode: api (MiMo)")
    base_url = api_cfg.get("url") or "https://api.xiaomimimo.com/v1"
    print(f"[ASR] API: {base_url}")
    print(f"[ASR] Model: {api_cfg.get('model', 'mimo-v2.5-asr')}")
    print(f"[ASR] Language: {api_cfg.get('language', 'auto')}")
    if api_cfg.get("key"):
        print(f"[ASR] API Key: ***{api_cfg['key'][-4:] if len(api_cfg['key']) >= 4 else '****'}")

    # Create API client
    client = ASRAPIClient(config)

    # Preprocess input to 16kHz mono WAV (MiMo supports WAV/MP3)
    with preprocess_input(input_file) as audio_path:
        file_size_mb = os.path.getsize(audio_path) / 1024 / 1024
        print(f"[API] Audio: {file_size_mb:.1f} MB (will be Base64-encoded)")

        # Run API transcription
        result = client.transcribe(audio_path, progress_callback=progress_callback)

    if result is None:
        raise RuntimeError(f"API transcription returned no results for {input_file}")

    # API diarization: check if the API returned speaker info
    diarization_supported = has_diarization_data(result.get("sentence_info", []))

    if diarize and not diarization_supported:
        print()
        print("=" * 56)
        print("  ⚠️  API 返回的结果不包含人声分离信息")
        print(f"  API: {api_cfg.get('url') or 'https://api.xiaomimimo.com/v1'}")
        print(f"  所有语音将标记为 \"{UNIDENTIFIED_SPEAKER}\"")
        print(f"  如需人声分离，请确认 API 是否支持该功能")
        print("=" * 56)
        print()
    elif not diarization_supported:
        print(f"[API] 人声分离: API 返回结果中无说话人信息")
    else:
        print(f"[API] 人声分离: 已启用（API 返回了说话人标注）")

    return _finalize_result(
        result=result,
        input_file=input_file,
        output_dir=output_dir,
        format=format,
        diarize=diarize and diarization_supported,
        diarization_supported=diarization_supported,
        resolved_model=api_cfg.get("model", "api"),
        device="api",
        mode="api",
    )


# ── Shared Result Finalization ───────────────────────────────────────────────

def _finalize_result(
    result: dict,
    input_file: str,
    output_dir: str | None,
    format: str,
    diarize: bool,
    diarization_supported: bool,
    resolved_model: str,
    device: str,
    mode: str,
) -> dict[str, str | list]:
    """Format output, write file, and build the response dict.

    Shared between local and API modes to ensure consistent output.
    """
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
    segments = result.get("sentence_info") or result.get("sentences", [])
    response: dict[str, str | list] = {
        "text": result.get("text", ""),
        "segments": segments,
        "output_path": str(output_file),
        "mode": mode,
        "model_used": resolved_model,
        "device": device,
        "diarization_supported": diarization_supported,
        "diarization_enabled": diarize,
    }

    # Speaker list
    if diarize and has_diarization_data(segments):
        speaker_ids = set(
            seg.get("spk") for seg in segments if "spk" in seg
        )
        response["speakers"] = [format_speaker_label(sid) for sid in sorted(speaker_ids)]
    else:
        response["speakers"] = [UNIDENTIFIED_SPEAKER]

    return response
