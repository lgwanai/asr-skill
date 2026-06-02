"""Core ASR modules.

Public API:
    - create_pipeline: Create FunASR model pipeline (Paraformer or SenseVoice)
    - transcribe: Run transcription on preprocessed audio
    - get_device: Detect optimal compute device
    - get_device_with_fallback: Detect device with fallback indication
    - resolve_model_type: Resolve "auto" model selection based on hardware
    - get_platform_info: Get platform/system/arch information
    - get_model_info: Get metadata about a model type
"""
