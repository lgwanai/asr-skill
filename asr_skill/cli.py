"""CLI entry point for ASR Skill.

This module provides the command-line interface for transcribing audio
and video files using the ASR Skill package.

Usage:
    # Local mode (default)
    asr-skill input.mp3                           # Auto-select model
    asr-skill input.mp3 --model sensevoice        # Force SenseVoice (faster CPU)
    asr-skill input.mp3 --model paraformer        # Force Paraformer (best accuracy)

    # API mode
    asr-skill input.mp3 --mode api                # Use remote API (from config)
    asr-skill input.mp3 --mode api --api-url=URL  # Override API URL
    asr-skill input.mp3 --mode api --api-key=KEY  # Override API key

    # General options
    asr-skill video.mp4                           # Video file
    asr-skill input.mp3 -o ./output               # Custom output directory
    asr-skill input.mp3 -f json                   # JSON output format
"""

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

from asr_skill import __version__


@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    default=None,
    help="Output directory (default: same as input)",
)
@click.option(
    "-f",
    "--format",
    type=click.Choice(["txt", "json", "srt", "ass", "md"]),
    default="txt",
    help="Output format (txt, json, srt, ass, md)",
)
@click.option(
    "-m",
    "--model",
    "model_type",
    type=click.Choice(["auto", "paraformer", "sensevoice"]),
    default=None,
    help=(
        "ASR engine (local mode only). 'auto' selects based on hardware "
        "(GPU→Paraformer, CPU→SenseVoice)."
    ),
)
@click.option(
    "--mode",
    type=click.Choice(["local", "api"]),
    default=None,
    help="Operation mode: 'local' (default) or 'api' (cloud API).",
)
@click.option(
    "--api-url",
    default=None,
    help="API endpoint URL (overrides config).",
)
@click.option(
    "--api-key",
    default=None,
    help="API authentication key (overrides config/MIMO_API_KEY env var).",
)
@click.version_option(version=__version__, prog_name="asr-skill")
def transcribe_cmd(
    input_file: str,
    output: str | None,
    format: str,
    model_type: str | None,
    mode: str | None,
    api_url: str | None,
    api_key: str | None,
) -> None:
    """Transcribe audio or video file to text with timestamps.

    INPUT_FILE is the path to the audio (MP3, WAV, M4A, FLAC) or video (MP4, AVI, MKV) file.
    """
    import os

    console = Console()

    # Validate Python version
    if sys.version_info < (3, 10):
        console.print("[red]Error: Python 3.10 or higher is required[/red]")
        sys.exit(1)

    # Apply CLI overrides to environment (picked up by config loader)
    if api_url:
        os.environ["MIMO_API_URL"] = api_url
    if api_key:
        os.environ["MIMO_API_KEY"] = api_key

    # Resolve mode early for UI messaging
    from asr_skill.utils.config import load_config
    config = load_config()
    resolved_mode = mode or config.get("mode", "local")

    # Run transcription with progress display
    try:
        from asr_skill import transcribe

        if resolved_mode == "api":
            console.print(f"[blue]Transcribing (API): {input_file}[/blue]")
        else:
            console.print(f"[blue]Transcribing: {input_file}[/blue]")

            # Detect hardware and warn if fallback
            from asr_skill.core.device import get_device_with_fallback
            device, fallback = get_device_with_fallback()
            if fallback:
                console.print(
                    "[yellow]Warning: GPU not available, using CPU (slower)[/yellow]"
                )

        # Create progress bar
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("Transcribing...", total=None)

            def progress_callback(current: int, total: int):
                if total > 0:
                    progress.update(task_id, completed=current, total=total)

            result = transcribe(
                input_file,
                output,
                format,
                model_type=model_type,
                mode=mode,
                progress_callback=progress_callback,
            )

        # Show result summary
        result_mode = result.get("mode", "unknown")
        model_used = result.get("model_used", "unknown")
        device_used = result.get("device", "unknown")

        if result_mode == "api":
            console.print(f"[dim]Mode: API | Model: {model_used}[/dim]")
        else:
            console.print(f"[dim]Mode: Local | Model: {model_used} | Device: {device_used}[/dim]")

        # Show speakers
        speakers = result.get("speakers", [])
        if speakers and speakers != ["未识别人声"]:
            console.print(f"[green]Speakers detected: {', '.join(speakers)}[/green]")
        elif result.get("diarization_supported") is False:
            console.print('[yellow]人声分离: 不支持（所有语音标记为"未识别人声"）[/yellow]')

        console.print(
            Panel(f"[green]Output saved to: {result['output_path']}[/green]")
        )
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


def main() -> None:
    """Entry point for CLI."""
    transcribe_cmd()


if __name__ == "__main__":
    main()
