---
phase: 01-core-asr-pipeline
plan: 03
type: execute
wave: 2
depends_on:
  - 01-PLAN
  - 02-PLAN
files_modified:
  - asr_skill/core/models.py
  - asr_skill/core/pipeline.py
  - asr_skill/__init__.py
autonomous: true
requirements:
  - CORE-03
  - CORE-04
  - TRAN-01
  - TRAN-02
  - TRAN-03

must_haves:
  truths:
    - "User's audio is transcribed to text with punctuation"
    - "User receives word-level timestamps for each segment"
    - "FunASR models are auto-downloaded and cached locally"
    - "GPU-to-CPU fallback is handled gracefully with warning"
    - "Long audio files are processed without memory crash"
  artifacts:
    - path: "asr_skill/core/models.py"
      provides: "FunASR model loading and caching"
      exports: ["create_pipeline", "MODEL_DIR"]
    - path: "asr_skill/core/pipeline.py"
      provides: "Main transcription pipeline"
      exports: ["transcribe"]
    - path: "asr_skill/__init__.py"
      provides: "Python API entry point"
      exports: ["transcribe"]
  key_links:
    - from: "asr_skill/core/models.py"
      to: "FunASR AutoModel"
      via: "Model composition"
      pattern: "AutoModel\\("
    - from: "asr_skill/core/pipeline.py"
      to: "asr_skill/core/device.py"
      via: "Device detection"
      pattern: "get_device"
    - from: "asr_skill/core/pipeline.py"
      to: "asr_skill/preprocessing/audio.py"
      via: "Audio preprocessing"
      pattern: "preprocess_audio"
    - from: "asr_skill/__init__.py"
      to: "asr_skill/core/pipeline.py"
      via: "Python API"
      pattern: "from.*pipeline.*import"
---

<objective>
Create the FunASR model pipeline with VAD+ASR+Punctuation composition and integrate all components into the main transcription function.

Purpose: Deliver the core transcription capability with automatic model download, hardware-adaptive execution, and proper error handling.
Output: Model loading module, pipeline module, and Python API entry point.
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
  <name>Task 1: Create model loading module</name>
  <files>asr_skill/core/models.py</files>
  <action>
Create `asr_skill/core/models.py` with FunASR model loading:

1. Define `MODEL_DIR = "./models"` at module level (per locked decision for project-local cache).

2. Implement `create_pipeline(device: str, model_dir: str = MODEL_DIR)`:
   - Import FunASR: `from funasr import AutoModel`
   - Create pipeline with VAD + ASR + Punctuation:
   ```python
   model = AutoModel(
       model="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
       vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
       punc_model="iic/punc_ct-transformer_cn-en-common-vocab471067-large",
       device=device,
       disable_update=True,  # CRITICAL: prevents kwargs mutation
       model_hub=model_dir,
       vad_kwargs={"max_single_segment_time": 30000},  # 30s max per segment
   )
   return model
   ```
   - The `disable_update=True` flag prevents the GPU-to-CPU fallback bug (Pitfall 1 from research).
   - The `vad_kwargs` prevents memory explosion on long audio (Pitfall 2 from research).

3. Add docstring explaining:
   - Models are auto-downloaded on first use
   - Cache location is project-local `./models/`
   - VAD is required for timestamps and punctuation

DO NOT create AutoModel per request - reuse model instance for performance.
DO NOT skip VAD - it's required for timestamps and punctuation to work.
DO NOT forget `disable_update=True` - this prevents the GPU fallback bug.
</action>
  <verify>
```bash
python -c "from asr_skill.core.models import create_pipeline, MODEL_DIR; print(f'Model dir: {MODEL_DIR}')"
```
</verify>
  <done>
- `asr_skill/core/models.py` exists with `create_pipeline()` function
- Model directory is set to `./models`
- Function creates FunASR AutoModel with VAD+ASR+PUNC composition
</done>
</task>

<task type="auto">
  <name>Task 2: Create transcription pipeline</name>
  <files>asr_skill/core/pipeline.py</files>
  <action>
Create `asr_skill/core/pipeline.py` with the main transcription function:

1. Implement `transcribe(model, audio_path: str, device: str) -> dict`:
   - Run transcription with explicit device setting:
   ```python
   result = model.generate(
       input=audio_path,
       batch_size_s=300,  # 300 seconds per batch for long audio
       device=device,     # EXPLICIT: prevents fallback bug
   )
   return result[0] if result else None
   ```
   - The explicit `device=device` on every generate() call prevents GPU-to-CPU fallback (Pitfall 1).
   - The `batch_size_s=300` prevents memory explosion on long audio (Pitfall 2).

2. Add error handling:
   - Wrap in try/except for RuntimeError (CUDA out of memory, etc.)
   - Re-raise with clearer error message
   - Return None if result is empty (should not happen with valid audio)

3. Add docstring explaining:
   - Model must be pre-loaded via `create_pipeline()`
   - Audio must be preprocessed (16kHz mono)
   - Device must be passed explicitly to prevent fallback bug

DO NOT call model.generate() without device parameter - this causes silent fallback.
DO NOT process audio directly here - preprocessing should be done before calling this.
</action>
  <verify>
```bash
python -c "from asr_skill.core.pipeline import transcribe; print('Pipeline import successful')"
```
</verify>
  <done>
- `asr_skill/core/pipeline.py` exists with `transcribe()` function
- Function runs FunASR generate() with explicit device
- Batch size is set for long audio handling
</done>
</task>

<task type="auto">
  <name>Task 3: Create Python API entry point</name>
  <files>asr_skill/__init__.py</files>
  <action>
Update `asr_skill/__init__.py` with the main Python API:

1. Create the complete `transcribe()` function that integrates all components:
   ```python
   from pathlib import Path
   from asr_skill.core.device import get_device_with_fallback
   from asr_skill.core.models import create_pipeline
   from asr_skill.core.pipeline import transcribe as _transcribe
   from asr_skill.preprocessing.audio import preprocess_audio, SUPPORTED_FORMATS
   from asr_skill.postprocessing.formatters import format_txt, format_json
   from asr_skill.utils.paths import get_output_path

   def transcribe(input_file: str, output_dir: str = None, format: str = "txt") -> dict:
       """
       Transcribe audio file to text.

       Args:
           input_file: Path to audio file (MP3, WAV, M4A, FLAC)
           output_dir: Output directory (default: same as input)
           format: Output format "txt" or "json"

       Returns:
           dict with keys: text, segments, output_path
       """
       # Detect device
       device, fallback = get_device_with_fallback()

       # Load model (cached)
       model = create_pipeline(device)

       # Preprocess audio
       audio_path = preprocess_audio(input_file)

       # Transcribe
       result = _transcribe(model, audio_path, device)

       # Write output
       output_file = get_output_path(input_file, output_dir, format)
       output_file.parent.mkdir(parents=True, exist_ok=True)

       if format == "txt":
           output_file.write_text(format_txt(result), encoding="utf-8")
       else:
           output_file.write_text(format_json(result), encoding="utf-8")

       return {
           "text": result.get("text", ""),
           "segments": result.get("sentences", []),
           "output_path": str(output_file),
       }
   ```

2. Add `__all__ = ["transcribe", "SUPPORTED_FORMATS"]` to control exports.

3. Add package-level docstring explaining the module.

DO NOT add config file support - per locked decision, no config file for v1.
DO NOT add progress callbacks - that's deferred to Phase 3.
</action>
  <verify>
```bash
python -c "from asr_skill import transcribe, SUPPORTED_FORMATS; print(f'API ready, formats: {SUPPORTED_FORMATS}')"
```
</verify>
  <done>
- `asr_skill/__init__.py` exports `transcribe()` function
- Single function call handles full pipeline
- Returns dict with text, segments, output_path
</done>
</task>

</tasks>

<verification>
1. Import the full API:
   ```bash
   python -c "from asr_skill import transcribe, SUPPORTED_FORMATS; from asr_skill.core.models import create_pipeline; from asr_skill.core.pipeline import transcribe as pipeline_transcribe; print('All imports successful')"
   ```
2. Verify model creation function exists
3. Verify transcribe function signature matches locked decision
</verification>

<success_criteria>
- FunASR models auto-download to ./models on first use
- VAD+ASR+Punctuation pipeline composition works
- Python API provides single `transcribe()` function
- Device is passed explicitly to prevent GPU fallback bug
- Long audio handled with batch_size_s=300
</success_criteria>

<output>
After completion, create `.planning/phases/01-core-asr-pipeline/01-03-SUMMARY.md`
</output>
