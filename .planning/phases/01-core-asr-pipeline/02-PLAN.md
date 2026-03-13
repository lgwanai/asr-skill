---
phase: 01-core-asr-pipeline
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - asr_skill/postprocessing/__init__.py
  - asr_skill/postprocessing/formatters.py
  - asr_skill/utils/__init__.py
  - asr_skill/utils/paths.py
autonomous: true
requirements:
  - OUTP-01
  - OUTP-04
  - OUTP-06

must_haves:
  truths:
    - "User receives transcription as plain TXT file with inline timestamps"
    - "User receives transcription as structured JSON with segment metadata"
    - "Output files are saved in same directory as input by default"
    - "Timestamp format follows standard SRT style HH:MM:SS.mmm"
  artifacts:
    - path: "asr_skill/postprocessing/formatters.py"
      provides: "TXT and JSON output formatters"
      exports: ["format_txt", "format_json", "format_timestamp"]
    - path: "asr_skill/utils/paths.py"
      provides: "Path handling utilities"
      exports: ["get_output_path"]
  key_links:
    - from: "asr_skill/postprocessing/formatters.py"
      to: "asr_skill/utils/paths.py"
      via: "Output path resolution"
      pattern: "get_output_path"
    - from: "format_txt"
      to: "FunASR result"
      via: "Result dict with sentences"
      pattern: "sentences"
---

<objective>
Create output formatters for TXT and JSON formats, plus path utilities for output file handling.

Purpose: Enable transcription output in user-friendly formats with proper timestamp formatting and default output location handling.
Output: Formatter module and path utility module ready for pipeline integration.
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
  <name>Task 1: Create output formatters</name>
  <files>asr_skill/postprocessing/formatters.py</files>
  <action>
Create `asr_skill/postprocessing/formatters.py` with output formatting functions:

1. Create the directory structure:
   - `asr_skill/postprocessing/__init__.py` (empty)
   - `asr_skill/postprocessing/formatters.py`

2. Implement `format_timestamp(ms: int) -> str`:
   - Convert milliseconds to `HH:MM:SS.mmm` format
   - hours = ms // 3600000
   - minutes = (ms % 3600000) // 60000
   - seconds = (ms % 60000) // 1000
   - millis = ms % 1000
   - Return `f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"`
   - This matches the locked decision for SRT-style timestamps

3. Implement `format_txt(result: dict) -> str`:
   - Extract sentences from `result.get("sentences", [])`
   - For each segment, format as `[{timestamp}] {text}`
   - Use `format_timestamp(segment["start"])` for timestamp
   - Join with newlines
   - Return the formatted string
   - Handle empty sentences gracefully (return empty string)

4. Implement `format_json(result: dict) -> str`:
   - Extract sentences from `result.get("sentences", [])`
   - For each segment, create object:
     ```python
     {
         "text": seg["text"],
         "start": seg["start"],
         "end": seg["end"],
         "confidence": seg.get("confidence", 1.0)
     }
     ```
   - Use `json.dumps(segments, ensure_ascii=False, indent=2)`
   - Return the JSON string
   - Handle empty sentences gracefully (return "[]")

5. Add type hints and docstrings for all functions.

DO NOT use `ensure_ascii=True` - Chinese text must be preserved properly.
DO NOT hardcode confidence to 1.0 if the field exists - use `seg.get("confidence", 1.0)`.
</action>
  <verify>
```bash
python -c "
from asr_skill.postprocessing.formatters import format_timestamp, format_txt, format_json
print(format_timestamp(3661500))  # Should be 01:01:01.500
print(format_txt({'sentences': [{'text': 'Hello', 'start': 0, 'end': 1000}]}))
"
```
</verify>
  <done>
- `asr_skill/postprocessing/formatters.py` exists with `format_timestamp()`, `format_txt()`, `format_json()` functions
- Timestamp format is HH:MM:SS.mmm
- TXT format is `[HH:MM:SS.mmm] text` per line
- JSON format is array of segment objects with text, start, end, confidence
</done>
</task>

<task type="auto">
  <name>Task 2: Create path utilities</name>
  <files>asr_skill/utils/paths.py</files>
  <action>
Create `asr_skill/utils/paths.py` with path handling utilities:

1. Create the directory structure:
   - `asr_skill/utils/__init__.py` (empty)
   - `asr_skill/utils/paths.py`

2. Implement `get_output_path(input_path: str, output_dir: str | None, format: str) -> Path`:
   - Use `pathlib.Path` for all path operations
   - `input_path` is the path to the input audio file
   - `output_dir` is optional; if None, use same directory as input
   - `format` is the output format ("txt" or "json")
   - Logic:
     ```python
     input_p = Path(input_path)
     if output_dir:
         out_dir = Path(output_dir)
     else:
         out_dir = input_p.parent
     output_file = out_dir / f"{input_p.stem}.{format}"
     return output_file
     ```
   - The function returns a Path object

3. Add docstring explaining the default output behavior (same directory, same basename, different extension).

DO NOT create the output directory - that's the caller's responsibility.
DO NOT hardcode output paths - use the input file's parent directory by default.
</action>
  <verify>
```bash
python -c "
from asr_skill.utils.paths import get_output_path
from pathlib import Path
result = get_output_path('/tmp/test/audio.mp3', None, 'txt')
print(result)  # Should be /tmp/test/audio.txt
result2 = get_output_path('/tmp/test/audio.mp3', '/output', 'json')
print(result2)  # Should be /output/audio.json
"
```
</verify>
  <done>
- `asr_skill/utils/paths.py` exists with `get_output_path()` function
- Default output is same directory as input
- Output filename uses same basename with format extension
</done>
</task>

</tasks>

<verification>
1. Import all modules successfully:
   ```bash
   python -c "from asr_skill.postprocessing.formatters import format_txt, format_json, format_timestamp; from asr_skill.utils.paths import get_output_path; print('All imports successful')"
   ```
2. Verify timestamp format is correct
3. Verify output path handling works correctly
</verification>

<success_criteria>
- TXT formatter produces inline timestamp format
- JSON formatter produces segment-level array structure
- Path utility correctly resolves output paths
- Default output location is same directory as input
</success_criteria>

<output>
After completion, create `.planning/phases/01-core-asr-pipeline/01-02-SUMMARY.md`
</output>
