"""CLI entry point for ASR Skill.

This module provides the command-line interface for transcribing audio files.
It handles user input validation, hardware detection with warnings, and
displays clear error messages for any issues.

Usage:
    asr-skill <input_file> [-o OUTPUT] [-f FORMAT]

Examples:
    asr-skill audio.mp3
    asr-skill meeting.m4a -o ./transcripts -f json
"""

import sys

import click
from rich.console import Console
from rich.panel import Panel

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
    type=click.Choice(["txt", "json"]),
    default="txt",
    help="Output format",
)
@click.version_option(version=__version__, prog_name="asr-skill")
def transcribe_cmd(input_file: str, output: str | None, format: str) -> None:
    """Transcribe audio file to text with timestamps.

    INPUT_FILE is the path to the audio file (MP3, WAV, M4A, FLAC).
    """
    console = Console()

    # Validate Python version
    if sys.version_info < (3, 10):
        console.print("[red]Error: Python 3.10 or higher is required[/red]")
        sys.exit(1)

    # Detect hardware and warn if fallback
    from asr_skill.core.device import get_device_with_fallback

    device, fallback = get_device_with_fallback()
    if fallback:
        console.print(
            "[yellow]Warning: GPU not available, using CPU (slower)[/yellow]"
        )

    # Run transcription
    try:
        from asr_skill import transcribe

        console.print(f"[blue]Transcribing: {input_file}[/blue]")
        result = transcribe(input_file, output, format)
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
