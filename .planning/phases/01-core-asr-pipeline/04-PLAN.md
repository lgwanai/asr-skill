---
phase: 01-core-asr-pipeline
plan: 04
type: execute
wave: 3
depends_on:
  - 03-PLAN
files_modified:
  - asr_skill/cli.py
  - pyproject.toml
autonomous: true
requirements:
  - CORE-02

must_haves:
  truths:
    - "User can invoke transcription via CLI with just file path"
    - "User sees clear error messages for invalid input"
    - "User sees warning when GPU falls back to CPU"
    - "Python version is validated before execution"
    - "User can optionally specify output directory and format"
  artifacts:
    - path: "asr_skill/cli.py"
      provides: "CLI entry point"
      exports: ["main", "transcribe_cmd"]
    - path: "pyproject.toml"
      provides: "Package configuration and dependencies"
      contains: "dependencies"
  key_links:
    - from: "asr_skill/cli.py"
      to: "asr_skill/__init__.py"
      via: "Python API call"
      pattern: "from asr_skill import transcribe"
    - from: "asr_skill/cli.py"
      to: "click"
      via: "CLI framework"
      pattern: "@click\\.(command|option|argument)"
---

<objective>
Create CLI entry point with minimal required input and package configuration with all dependencies.

Purpose: Enable command-line invocation with auto-detection of hardware and output settings, plus proper package installation.
Output: CLI module and pyproject.toml for package installation.
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
  <name>Task 1: Create CLI entry point</name>
  <files>asr_skill/cli.py</files>
  <action>
Create `asr_skill/cli.py` with click-based CLI:

1. Implement CLI with click:
   ```python
   import sys
   import click
   from pathlib import Path
   from rich.console import Console
   from rich.panel import Panel

   @click.command()
   @click.argument("input_file", type=click.Path(exists=True))
   @click.option("-o", "--output", type=click.Path(), default=None, help="Output directory (default: same as input)")
   @click.option("-f", "--format", type=click.Choice(["txt", "json"]), default="txt", help="Output format")
   @click.version_option(version="0.1.0", prog_name="asr-skill")
   def transcribe_cmd(input_file: str, output: str, format: str):
       """Transcribe audio file to text with timestamps."""
       console = Console()

       # Validate Python version
       if sys.version_info < (3, 10):
           console.print("[red]Error: Python 3.10 or higher is required[/red]")
           sys.exit(1)

       # Detect hardware and warn if fallback
       from asr_skill.core.device import get_device_with_fallback
       device, fallback = get_device_with_fallback()
       if fallback:
           console.print("[yellow]Warning: GPU not available, using CPU (slower)[/yellow]")

       # Run transcription
       try:
           from asr_skill import transcribe
           console.print(f"[blue]Transcribing: {input_file}[/blue]")
           result = transcribe(input_file, output, format)
           console.print(Panel(f"[green]Output saved to: {result['output_path']}[/green]"))
       except ValueError as e:
           console.print(f"[red]Error: {e}[/red]")
           sys.exit(1)
       except Exception as e:
           console.print(f"[red]Unexpected error: {e}[/red]")
           sys.exit(1)

   def main():
       """Entry point for CLI."""
       transcribe_cmd()

   if __name__ == "__main__":
       main()
   ```

2. Key CLI features per locked decisions:
   - Minimal input: just file path required
   - Short flags only: `-o` for output, `-f` for format
   - Auto-detect hardware with warning on fallback
   - Fail fast with clear error messages
   - Color-coded output (red for errors, yellow for warnings, green for success)

3. Error handling per locked decisions:
   - Corrupted audio: fail entire file (no graceful degradation for v1)
   - Error reporting: console output to stderr with color coding

DO NOT add config file support - per locked decision, no config file for v1.
DO NOT add progress bar - that's Phase 3.
DO NOT use long flags like --output-dir - use short -o only.
</action>
  <verify>
```bash
python -m asr_skill.cli --help
```
</verify>
  <done>
- `asr_skill/cli.py` exists with click-based CLI
- CLI accepts file path as argument with optional -o and -f flags
- Python version check (>=3.10) is performed
- Hardware fallback warning is displayed
</done>
</task>

<task type="auto">
  <name>Task 2: Create package configuration</name>
  <files>pyproject.toml</files>
  <action>
Create `pyproject.toml` with package configuration:

1. Create pyproject.toml with:
   ```toml
   [build-system]
   requires = ["hatchling"]
   build-backend = "hatchling.build"

   [project]
   name = "asr-skill"
   version = "0.1.0"
   description = "Local speech recognition with high-accuracy Chinese transcription"
   readme = "README.md"
   requires-python = ">=3.10"
   license = "MIT"
   authors = [
       { name = "Your Name", email = "your@email.com" }
   ]
   dependencies = [
       "funasr==1.3.1",
       "torch>=2.0.0",
       "modelscope>=1.34.0",
       "click>=8.1.0",
       "rich>=13.0.0",
       "librosa>=0.10.0",
       "soundfile>=0.12.0",
   ]

   [project.scripts]
   asr-skill = "asr_skill.cli:main"

   [project.optional-dependencies]
   dev = [
       "pytest>=7.0.0",
       "pytest-cov>=4.0.0",
   ]

   [tool.hatch.build.targets.wheel]
   packages = ["asr_skill"]
   ```

2. Key dependencies from RESEARCH.md:
   - funasr==1.3.1 (pinned version to avoid performance regression)
   - torch>=2.0.0 (supports CUDA 12.x and MPS)
   - modelscope for model download
   - click for CLI
   - rich for colored output
   - librosa and soundfile for audio preprocessing

3. The `requires-python = ">=3.10"` enforces CORE-02.

DO NOT pin torch to exact version - let user install CUDA/MPS variant as needed.
DO NOT add pyyaml dependency - no config file for v1.
</action>
  <verify>
```bash
pip show toml 2>/dev/null && python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))" 2>/dev/null || python -c "import toml; toml.load('pyproject.toml')" 2>/dev/null || echo "pyproject.toml created"
cat pyproject.toml | head -20
```
</verify>
  <done>
- `pyproject.toml` exists with package metadata
- Dependencies include funasr, torch, click, rich, librosa, soundfile
- CLI entry point registered as `asr-skill` command
- Python version requirement set to >=3.10
</done>
</task>

</tasks>

<verification>
1. Verify CLI help works:
   ```bash
   python -m asr_skill.cli --help
   ```
2. Verify pyproject.toml is valid:
   ```bash
   python -c "import tomllib; d = tomllib.load(open('pyproject.toml', 'rb')); print(f'Package: {d[\"project\"][\"name\"]}')"
   ```
3. Verify version check would fail on Python < 3.10 (logic is in place)
</verification>

<success_criteria>
- CLI accepts file path with minimal required input
- Short flags -o and -f work for optional parameters
- Hardware detection with fallback warning is displayed
- Python version validation (>=3.10) is enforced
- pyproject.toml has all required dependencies
- CLI entry point is registered as `asr-skill` command
</success_criteria>

<output>
After completion, create `.planning/phases/01-core-asr-pipeline/01-04-SUMMARY.md`
</output>
