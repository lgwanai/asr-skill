"""ASR model loading and caching module.

This module provides model pipeline creation for two ASR engines:
1. Paraformer-Large — High-accuracy Chinese ASR with speaker diarization
2. SenseVoiceSmall — Lightweight multi-lingual ASR, faster on CPU

The pipeline combines up to four models depending on the engine:
    Paraformer: VAD + ASR + Punctuation + optional Speaker Diarization (CAM++)
    SenseVoice: Single unified model (ASR + VAD + punctuation in one)

Key Features:
- Models are auto-downloaded on first use via ModelScope
- Cache location is platform-specific (macOS/Windows/Linux)
- Platform-aware auto-selection chooses the best model for the current hardware
- VAD is required for timestamps and punctuation in Paraformer mode
- The `disable_update=True` flag prevents GPU-to-CPU fallback bug
- Speaker diarization is available only with Paraformer (SenseVoice lacks timestamps)

Model IDs (from FunASR Model Zoo):
- Paraformer: iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch
- VAD:        iic/speech_fsmn_vad_zh-cn-16k-common-pytorch
- PUNC:       iic/punc_ct-transformer_cn-en-common-vocab471067-large
- SPK:        iic/speech_campplus_sv_zh-cn_16k-common (~300MB)
- SenseVoice: iic/SenseVoiceSmall
"""

from funasr import AutoModel
import os
import platform
import sys
from pathlib import Path


# ── Platform Detection ──────────────────────────────────────────────────────

def get_platform_info() -> dict[str, str]:
    """Detect the current platform and return structured info.

    Returns:
        dict with keys:
            - system: "Darwin" (macOS), "Windows", or "Linux"
            - arch: CPU architecture ("arm64", "x86_64", "AMD64", etc.)
            - is_apple_silicon: "true" if macOS on ARM (M1/M2/M3/M4)
    """
    system = platform.system()
    machine = platform.machine()

    is_apple_silicon = (system == "Darwin" and machine == "arm64")

    return {
        "system": system,
        "arch": machine,
        "is_apple_silicon": "true" if is_apple_silicon else "false",
    }


def get_default_model_dir() -> str:
    """Get the default model directory based on the operating system."""
    home = Path.home()
    system = platform.system()

    if system == "Windows":
        # Windows: %APPDATA%/asr-skill/models
        base = os.environ.get("APPDATA")
        if base:
            path = Path(base) / "asr-skill" / "models"
        else:
            path = home / "AppData" / "Roaming" / "asr-skill" / "models"
    elif system == "Darwin":
        # macOS: ~/Library/Application Support/asr-skill/models
        path = home / "Library" / "Application Support" / "asr-skill" / "models"
    else:
        # Linux/Other: ~/.local/share/asr-skill/models
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            path = Path(xdg_data_home) / "asr-skill" / "models"
        else:
            path = home / ".local" / "share" / "asr-skill" / "models"

    # Ensure directory exists
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback to user home subdirectory on permission errors
        # (more stable than CWD-relative ./models, especially on Windows)
        import tempfile
        fallback = Path(tempfile.gettempdir()) / "asr-skill" / "models"
        fallback.mkdir(parents=True, exist_ok=True)
        path = fallback

    return str(path)


# Default persistent model cache directory
MODEL_DIR = get_default_model_dir()


# ── Model Selection ─────────────────────────────────────────────────────────

def resolve_model_type(
    requested: str,
    device: str,
) -> tuple[str, str]:
    """Resolve the ASR model type, handling "auto" selection.

    Auto-selection logic:
        - GPU available (CUDA/MPS) → "paraformer" (best accuracy, GPU-accelerated)
        - CPU only → "sensevoice" (much faster CPU inference)

    Args:
        requested: The user's model preference ("auto", "paraformer", "sensevoice").
        device: The detected compute device ("mps", "cuda:0", "cpu").

    Returns:
        tuple of (resolved_model_type, resolution_reason):
            - resolved_model_type: "paraformer" or "sensevoice"
            - resolution_reason: human-readable explanation of the choice
    """
    if requested not in ("auto", "paraformer", "sensevoice"):
        print(
            f"[WARNING] Unknown asr_model '{requested}', falling back to 'auto'",
            file=sys.stderr,
        )
        requested = "auto"

    if requested != "auto":
        return requested, f"user-specified: {requested}"

    # Auto-detect best model based on available hardware
    platform_info = get_platform_info()
    is_gpu = device in ("mps", "cuda:0")

    if is_gpu:
        choice = "paraformer"
        reason = (
            f"auto: GPU detected ({device}), "
            f"using Paraformer for best accuracy"
        )
    else:
        choice = "sensevoice"
        reason = (
            f"auto: CPU-only detected "
            f"({platform_info['system']}/{platform_info['arch']}), "
            f"using SenseVoice for faster CPU inference"
        )

    return choice, reason


# ── Pipeline Creation ───────────────────────────────────────────────────────

def create_pipeline(
    device: str,
    model_dir: str = MODEL_DIR,
    diarize: bool = True,
    model_type: str = "paraformer",
) -> AutoModel:
    """Create an ASR pipeline with the specified model type.

    Supports two engine backends:

    1. **Paraformer** (paraformer):
       - High-accuracy Chinese ASR with VAD + punctuation + optional speaker diarization
       - Best on GPU (CUDA/MPS), heavy on CPU (~1.3 GB model)
       - Supports speaker labeling via CAM++

    2. **SenseVoice** (sensevoice):
       - Lightweight unified model (ASR + VAD + punctuation in one)
       - Much faster on CPU (~200 MB model)
       - No speaker diarization support (no timestamp output)

    Args:
        device: Device string for inference ("cuda:0", "mps", or "cpu").
        model_dir: Directory for caching downloaded models.
        diarize: Enable speaker diarization. Ignored for SenseVoice (always False).
        model_type: ASR engine to use — "paraformer" or "sensevoice".

    Returns:
        AutoModel: FunASR model instance ready for inference.

    Raises:
        ValueError: If model_type is unrecognized.

    Notes:
        - Models are auto-downloaded on first use (several GB for Paraformer,
          ~200 MB for SenseVoice)
        - `disable_update=True` is CRITICAL to prevent GPU fallback bug
        - Speaker diarization requires Paraformer (SenseVoice has no timestamps)
        - For long audio (>1 hour), Paraformer VAD kwargs prevent memory issues
    """
    if model_type == "sensevoice":
        return _create_sensevoice_pipeline(device, model_dir)
    elif model_type == "paraformer":
        return _create_paraformer_pipeline(device, model_dir, diarize)
    else:
        raise ValueError(
            f"Unknown model_type: '{model_type}'. "
            f"Expected 'paraformer' or 'sensevoice'."
        )


def _create_paraformer_pipeline(
    device: str,
    model_dir: str,
    diarize: bool = True,
) -> AutoModel:
    """Create Paraformer-large pipeline with VAD + ASR + PUNC + optional SPK.

    This is the high-accuracy pipeline for Chinese speech recognition.
    Best used with GPU acceleration (CUDA or MPS).
    """
    model_kwargs = {
        "model": "iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "vad_model": "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        "punc_model": "iic/punc_ct-transformer_cn-en-common-vocab471067-large",
        "device": device,
        "disable_update": True,  # CRITICAL: prevents kwargs mutation causing GPU fallback
        "model_hub": model_dir,
        "vad_kwargs": {"max_single_segment_time": 30000},  # 30s max per VAD segment
    }

    if diarize:
        model_kwargs["spk_model"] = "iic/speech_campplus_sv_zh-cn_16k-common"
        model_kwargs["spk_mode"] = "punc_segment"

    if device == "mps":
        # Force float32 for MPS to avoid "MPS framework doesn't support float64" error
        import torch
        torch.set_default_dtype(torch.float32)

    return AutoModel(**model_kwargs)


def _create_sensevoice_pipeline(
    device: str,
    model_dir: str,
) -> AutoModel:
    """Create SenseVoiceSmall pipeline.

    SenseVoice is a unified model that handles ASR, VAD, and punctuation
    in a single small model (~200 MB). It is significantly faster on CPU
    compared to Paraformer-large.

    Key differences from Paraformer:
        - No separate VAD/PUNC models needed (unified)
        - No speaker diarization support (no timestamp output)
        - Lighter weight, faster CPU inference
        - Multi-lingual support built-in
        - Uses different generate() parameters

    Notes:
        - On macOS MPS: uses float32 to avoid MPS float64 issues
        - On CPU: SenseVoice is optimized for CPU inference
        - language="zh" for Chinese, can be "auto" for auto-detection
    """
    if device == "mps":
        # Force float32 for MPS compatibility
        import torch
        torch.set_default_dtype(torch.float32)

    model_kwargs = {
        "model": "iic/SenseVoiceSmall",
        "device": device,
        "disable_update": True,
        "model_hub": model_dir,
        # SenseVoice-specific: no vad_model, no punc_model, no spk_model
    }

    return AutoModel(**model_kwargs)


# ── Model Info ──────────────────────────────────────────────────────────────

def get_model_info(model_type: str) -> dict:
    """Get information about an ASR model type.

    Args:
        model_type: "paraformer" or "sensevoice"

    Returns:
        dict with keys: name, size_approx, diarization_supported, description
    """
    info = {
        "paraformer": {
            "name": "Paraformer-Large",
            "size_approx": "~1.3 GB",
            "diarization_supported": True,
            "description": (
                "High-accuracy Chinese speech recognition with VAD, punctuation, "
                "and optional speaker diarization. Best on GPU."
            ),
        },
        "sensevoice": {
            "name": "SenseVoiceSmall",
            "size_approx": "~200 MB",
            "diarization_supported": False,
            "description": (
                "Lightweight unified ASR model (VAD + ASR + punctuation in one). "
                "Much faster on CPU, multi-lingual. No speaker diarization."
            ),
        },
    }
    return info.get(model_type, {})
