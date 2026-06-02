"""ASR model loading and caching module.

This module provides model pipeline creation for two ASR engines:
1. Paraformer-Large — High-accuracy Chinese ASR with speaker diarization
2. SenseVoiceSmall — Lightweight multi-lingual ASR, faster on CPU

Model cache resolution (in priority order):
    1. config.txt ``model_dir`` — user-specified directory (e.g., ``./models``)
    2. ModelScope default: ``~/.cache/modelscope/`` (macOS/Linux) or
       ``%USERPROFILE%/.cache/modelscope/`` (Windows)
    3. If neither has the required models, download to directory from step 1.

The pipeline combines up to four models depending on the engine:
    Paraformer: VAD + ASR + Punctuation + optional Speaker Diarization (CAM++)
    SenseVoice: Single unified model (ASR + VAD + punctuation in one)

Model IDs (from FunASR Model Zoo):
- Paraformer: iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch
- VAD:        iic/speech_fsmn_vad_zh-cn-16k-common-pytorch
- PUNC:       iic/punc_ct-transformer_cn-en-common-vocab471067-large
- SPK:        iic/speech_campplus_sv_zh-cn_16k-common (~300MB)
- SenseVoice: iic/SenseVoiceSmall
"""

import os
import platform
import sys
from pathlib import Path

# Delayed FunASR import — we need to set MODELSCOPE_CACHE first
AutoModel = None


# ── Platform Detection ──────────────────────────────────────────────────────

def get_platform_info() -> dict[str, str]:
    """Detect the current platform and return structured info."""
    system = platform.system()
    machine = platform.machine()
    is_apple_silicon = (system == "Darwin" and machine == "arm64")
    return {
        "system": system,
        "arch": machine,
        "is_apple_silicon": "true" if is_apple_silicon else "false",
    }


def get_default_model_dir() -> str:
    """Get the default model cache directory for the current platform.

    Returns (by OS):
        Windows:  ``%APPDATA%\\asr-skill\\models``
        macOS:    ``~/Library/Application Support/asr-skill/models``
        Linux:    ``~/.local/share/asr-skill/models``
    """
    home = Path.home()
    system = platform.system()

    if system == "Windows":
        base = os.environ.get("APPDATA")
        if base:
            path = Path(base) / "asr-skill" / "models"
        else:
            path = home / "AppData" / "Roaming" / "asr-skill" / "models"
    elif system == "Darwin":
        path = home / "Library" / "Application Support" / "asr-skill" / "models"
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        path = Path(xdg) / "asr-skill" / "models" if xdg else home / ".local" / "share" / "asr-skill" / "models"

    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        path = Path(os.path.join(os.path.expanduser("~"), ".asr-skill-models"))
        path.mkdir(parents=True, exist_ok=True)

    return str(path)


def get_modelscope_cache_dir() -> str:
    """Get the ModelScope default cache directory for the current platform."""
    home = str(Path.home())
    if platform.system() == "Windows":
        return os.path.join(os.environ.get("USERPROFILE", home), ".cache", "modelscope")
    return os.path.join(home, ".cache", "modelscope")


# ── Model Cache Resolution ──────────────────────────────────────────────────

# Required model directories (under <cache>/hub/models/iic/<id>/)
PARAFORMER_MODEL_ID = "speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
VAD_MODEL_ID = "speech_fsmn_vad_zh-cn-16k-common-pytorch"
PUNC_MODEL_ID = "punc_ct-transformer_cn-en-common-vocab471067-large"
SPK_MODEL_ID = "speech_campplus_sv_zh-cn_16k-common"
SENSEVOICE_MODEL_ID = "SenseVoiceSmall"

# Key file to check for model existence
_MODEL_KEY_FILE = "model.pt"
_SENSEVOICE_KEY_FILE = "model.pt"


def _is_model_present(cache_dir: str, model_id: str, key_file: str = _MODEL_KEY_FILE) -> bool:
    """Check if a specific ModelScope model exists in the given cache directory.

    ModelScope may store models under two possible paths depending on how
    MODELSCOPE_CACHE was set:
        1. ``<cache_dir>/hub/models/iic/<model_id>/<key_file>``  (legacy/default)
        2. ``<cache_dir>/models/iic/<model_id>/<key_file>``      (when env var set)
        3. ``<cache_dir>/._____temp/models/iic/<model_id>/<key_file>`` (temp download)
    """
    base = Path(cache_dir)
    candidates = [
        base / "hub" / "models" / "iic" / model_id / key_file,
        base / "models" / "iic" / model_id / key_file,
    ]
    # Also check for partial/temp downloads
    for cand in candidates:
        if cand.exists():
            return True
    return False


def resolve_model_cache_dir(config_model_dir: str | None = None) -> str:
    """Resolve the model cache directory with the following priority:

    1. User-configured ``model_dir`` from config.txt (if non-empty)
    2. Existing ModelScope cache (``~/.cache/modelscope``) — only if
       the required models are already present there
    3. User-configured ``model_dir`` (empty → fall back to platform default)

    This ensures:
    - If the user specified a directory, it is always used as the download target
    - If models already exist in ModelScope cache, we use them directly
    - If models need to be downloaded, they go to the user's preferred directory

    Args:
        config_model_dir: Value of ``model_dir`` from config.txt (may be empty/None).

    Returns:
        Absolute path to the resolved cache directory.
    """
    user_dir = str(config_model_dir).strip() if config_model_dir else ""
    if user_dir:
        user_dir = str(Path(user_dir).resolve())

    default_dir = get_default_model_dir()
    modelscope_dir = get_modelscope_cache_dir()

    # ── Priority 1: User-specified directory exists and has models ──────
    if user_dir and _is_model_present(user_dir, PARAFORMER_MODEL_ID):
        print(f"[ASR] Using configured model_dir: {user_dir} (models found)")
        return user_dir

    # ── Priority 2: ModelScope cache already has models ────────────────
    if _is_model_present(modelscope_dir, PARAFORMER_MODEL_ID):
        print(f"[ASR] Using ModelScope cache: {modelscope_dir} (models found)")
        if user_dir:
            print(f"[ASR]   (config model_dir={user_dir} is empty — will use cache)")
        return modelscope_dir

    # ── Priority 3: User dir → download there ─────────────────────────
    target = user_dir if user_dir else default_dir
    print(f"[ASR] Target model directory: {target}")
    print(f"[ASR] Models not found — will download on first use.")
    return target


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
    diarize: bool = True,
    model_type: str = "paraformer",
    cache_dir: str | None = None,
) -> "AutoModel":  # type: ignore[name-defined] # imported lazily
    """Create an ASR pipeline with the specified model type.

    Models are resolved via :func:`resolve_model_cache_dir`. If not present,
    they are auto-downloaded from ModelScope to the resolved directory.

    Args:
        device: Device string for inference ("cuda:0", "mps", or "cpu").
        diarize: Enable speaker diarization (Paraformer only).
        model_type: ASR engine — "paraformer" or "sensevoice".
        cache_dir: Resolved cache directory (from resolve_model_cache_dir).

    Returns:
        FunASR AutoModel instance ready for inference.
    """
    global AutoModel

    # Resolve and set the model cache directory
    cache_dir = resolve_model_cache_dir(cache_dir)
    os.environ["MODELSCOPE_CACHE"] = cache_dir
    print(f"[ASR] MODELSCOPE_CACHE={cache_dir}")

    # Lazy import FunASR AFTER setting MODELSCOPE_CACHE
    # This ensures ModelScope downloads to our preferred directory
    if AutoModel is None:
        from funasr import AutoModel as _AutoModel
        AutoModel = _AutoModel

    if model_type == "sensevoice":
        return _create_sensevoice_pipeline(device, cache_dir)
    elif model_type == "paraformer":
        return _create_paraformer_pipeline(device, cache_dir, diarize)
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
