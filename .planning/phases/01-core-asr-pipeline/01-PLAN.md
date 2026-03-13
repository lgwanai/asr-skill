---
phase: 01-core-asr-pipeline
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - asr_skill/__init__.py
  - asr_skill/core/__init__.py
  - asr_skill/core/device.py
  - asr_skill/preprocessing/__init__.py
  - asr_skill/preprocessing/audio.py
autonomous: true
requirements:
  - CORE-01
  - CORE-04
  - AUDIO-01
  - AUDIO-03
  - AUDIO-04

must_haves:
  truths:
    - "User's hardware is automatically detected (CUDA, MPS, or CPU)"
    - "User receives warning when GPU falls back to CPU"
    - "Audio files in MP3, WAV, M4A, FLAC formats are accepted"
    - "Audio is automatically resampled to 16kHz mono"
    - "Long audio files (>1 hour) are processed without memory crash"
  artifacts:
    - path: "asr_skill/core/device.py"
      provides: "Hardware detection with CUDA/MPS/CPU fallback"
      exports: ["get_device", "get_device_with_fallback"]
    - path: "asr_skill/preprocessing/audio.py"
      provides: "Audio preprocessing (resample, mono conversion)"
      exports: ["preprocess_audio", "SUPPORTED_FORMATS"]
  key_links:
    - from: "asr_skill/core/device.py"
      to: "torch.backends"
      via: "PyTorch device API"
      pattern: "torch\\.backends\\.(cuda|mps)\\.is_available"
    - from: "asr_skill/preprocessing/audio.py"
      to: "librosa"
      via: "Audio loading and resampling"
      pattern: "librosa\\.(load|resample)"
---

<objective>
Create hardware detection module with automatic device selection and audio preprocessing module that handles format conversion and resampling.

Purpose: Enable portable execution across CUDA GPU, Apple MPS, and CPU environments, and ensure all audio input is properly formatted for the ASR model.
Output: Device detection module and audio preprocessing module ready for pipeline integration.
</objective>

<execution_context>
@/Users/wuliang/.claude/get-shit-done/workflows/execute-plan.md
@/Users/wuliang/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-core-asr-pipeline/01-CONTEXT.md
@.planning/phases/01-core-asr-pipeline/01-RESEARCH.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create hardware detection module</name>
  <files>asr_skill/core/device.py</files>
  <action>
Create `asr_skill/core/device.py` with hardware detection functions:

1. Create the directory structure:
   - `asr_skill/__init__.py` (empty for now, just package marker)
   - `asr_skill/core/__init__.py` (empty)
   - `asr_skill/core/device.py`

2. Implement `get_device() -> str`:
   - Check `torch.backends.mps.is_available()` first (Apple Silicon)
   - Then check `torch.cuda.is_available()` (NVIDIA GPU)
   - Fallback to "cpu"
   - Return device string: "mps", "cuda:0", or "cpu"

3. Implement `get_device_with_fallback() -> tuple[str, bool]`:
   - Call `get_device()` to get preferred device
   - Return tuple of (device, fallback_occurred)
   - Fallback is True if device is "cpu" AND (CUDA or MPS was expected but unavailable)
   - Note: For Phase 1, consider CPU as fallback only if GPU was expected

4. Add docstrings explaining the detection priority (MPS > CUDA > CPU per research recommendation for Apple Silicon support).

DO NOT hardcode device="cuda" - this breaks on Apple Silicon and CPU-only machines.
DO NOT skip MPS detection - it's the primary device for Apple Silicon.
</action>
  <verify>
```bash
python -c "from asr_skill.core.device import get_device, get_device_with_fallback; d, f = get_device_with_fallback(); print(f'Device: {d}, Fallback: {f}')"
```
</verify>
  <done>
- `asr_skill/core/device.py` exists with `get_device()` and `get_device_with_fallback()` functions
- Device detection returns "mps", "cuda:0", or "cpu" based on available hardware
- Import works without errors
</done>
</task>

<task type="auto">
  <name>Task 2: Create audio preprocessing module</name>
  <files>asr_skill/preprocessing/audio.py</files>
  <action>
Create `asr_skill/preprocessing/audio.py` with audio preprocessing functions:

1. Create the directory structure:
   - `asr_skill/preprocessing/__init__.py` (empty)
   - `asr_skill/preprocessing/audio.py`

2. Define `SUPPORTED_FORMATS = [".mp3", ".wav", ".m4a", ".flac"]` at module level.

3. Implement `preprocess_audio(input_path: str) -> str`:
   - Use `librosa.load(input_path, sr=None, mono=True)` to load audio
   - `sr=None` preserves original sample rate (we'll resample if needed)
   - `mono=True` converts stereo to mono (CRITICAL: prevents dual-channel errors)
   - If `sr != 16000`, resample using `librosa.resample(y, orig_sr=sr, target_sr=16000)`
   - Write to temp file using `soundfile.write(temp_path, y, 16000)`
   - Use `tempfile.mktemp(suffix=".wav")` for temp path
   - Return the temp file path

4. Add input validation:
   - Check file exists using `pathlib.Path(input_path).exists()`
   - Check extension is in SUPPORTED_FORMATS
   - Raise `ValueError` with clear message if validation fails

5. Add docstring explaining the preprocessing pipeline (load, mono, resample to 16kHz, write temp).

DO NOT process stereo audio directly - always convert to mono first (librosa.load with mono=True handles this).
DO NOT skip the 16kHz resampling - FunASR models require 16kHz input.
</action>
  <verify>
```bash
python -c "from asr_skill.preprocessing.audio import SUPPORTED_FORMATS, preprocess_audio; print(f'Supported: {SUPPORTED_FORMATS}')"
```
</verify>
  <done>
- `asr_skill/preprocessing/audio.py` exists with `SUPPORTED_FORMATS` and `preprocess_audio()` function
- Supported formats include .mp3, .wav, .m4a, .flac
- Import works without errors
- Validation raises ValueError for unsupported formats or missing files
</done>
</task>

</tasks>

<verification>
1. Import all modules successfully:
   ```bash
   python -c "from asr_skill.core.device import get_device, get_device_with_fallback; from asr_skill.preprocessing.audio import preprocess_audio, SUPPORTED_FORMATS; print('All imports successful')"
   ```
2. Verify device detection returns valid device string
3. Verify SUPPORTED_FORMATS contains expected formats
</verification>

<success_criteria>
- Device detection module detects CUDA, MPS, or CPU correctly
- Audio preprocessing module accepts MP3, WAV, M4A, FLAC formats
- Audio is converted to 16kHz mono WAV for model input
- All imports work without errors
</success_criteria>

<output>
After completion, create `.planning/phases/01-core-asr-pipeline/01-01-SUMMARY.md`
</output>
