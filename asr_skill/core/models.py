"""FunASR model loading and caching module.

This module provides the FunASR AutoModel pipeline composition for ASR inference.
The pipeline combines four models:
1. VAD (Voice Activity Detection) - segments audio into speech regions
2. ASR (Automatic Speech Recognition) - transcribes speech to text
3. Punctuation - adds punctuation to the transcription
4. Speaker Diarization (CAM++) - identifies and labels different speakers

Key Features:
- Models are auto-downloaded on first use via ModelScope
- Cache location is project-local `./models/` directory
- VAD is required for timestamps and punctuation to work
- The `disable_update=True` flag prevents GPU-to-CPU fallback bug
- Speaker diarization is enabled by default (diarize=True)

Pitfall Mitigation:
- `disable_update=True`: Prevents kwargs mutation that causes GPU fallback
- `vad_kwargs={"max_single_segment_time": 30000}`: Prevents memory explosion on long audio
- CAM++ requires Paraformer-Large (SenseVoice is incompatible - no timestamp output)

Model IDs (from FunASR Model Zoo):
- ASR: iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch
- VAD: iic/speech_fsmn_vad_zh-cn-16k-common-pytorch
- PUNC: iic/punc_ct-transformer_cn-en-common-vocab471067-large
- SPK: iic/speech_campplus_sv_zh-cn_16k-common (~300MB)
"""

from funasr import AutoModel

# Project-local model cache directory
MODEL_DIR = "./models"


def create_pipeline(device: str, model_dir: str = MODEL_DIR, diarize: bool = True) -> AutoModel:
    """Create FunASR pipeline with VAD + ASR + Punctuation + optional Speaker Diarization.

    This function creates a FunASR AutoModel instance with the recommended
    model composition for Chinese speech recognition. The models are
    automatically downloaded from ModelScope on first use.

    Args:
        device: Device string for inference ("cuda:0", "mps", or "cpu").
                Must be passed explicitly to prevent GPU-to-CPU fallback bug.
        model_dir: Directory for caching downloaded models.
                   Defaults to project-local "./models/".
        diarize: Enable speaker diarization. Default True.
                 When enabled, adds CAM++ speaker model for speaker labeling.

    Returns:
        AutoModel: FunASR model instance ready for inference.

    Notes:
        - Models are auto-downloaded on first use (can take several GB)
        - VAD is REQUIRED for timestamps and punctuation to work
        - `disable_update=True` is CRITICAL to prevent GPU fallback bug
        - For long audio (>1 hour), the VAD kwargs prevent memory issues
        - Speaker diarization requires Paraformer-Large (not SenseVoice)

    Example:
        >>> device = "cuda:0"
        >>> model = create_pipeline(device)
        >>> result = model.generate(input="audio.wav", device=device)
    """
    model_kwargs = {
        "model": "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
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

    return AutoModel(**model_kwargs)
