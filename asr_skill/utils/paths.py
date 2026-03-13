"""Path handling utilities for ASR output files.

This module provides utilities for resolving output file paths based on
input file locations and user preferences.

Default Output Behavior:
- Output files are saved in the same directory as the input file by default
- Output filename uses the same basename as the input file
- Only the extension changes based on the output format

Example:
    Input: /path/to/audio.mp3
    Output (txt): /path/to/audio.txt
    Output (json): /path/to/audio.json
"""

from pathlib import Path


def get_output_path(input_path: str, output_dir: str | None, format: str) -> Path:
    """Resolve the output file path for transcription results.

    By default, output files are placed in the same directory as the input file,
    using the same basename with the format as the new extension.

    Args:
        input_path: Path to the input audio file
        output_dir: Optional output directory. If None, uses the input file's
                    parent directory.
        format: Output format extension (e.g., "txt" or "json")

    Returns:
        Path: Resolved output file path

    Example:
        >>> get_output_path('/tmp/test/audio.mp3', None, 'txt')
        PosixPath('/tmp/test/audio.txt')

        >>> get_output_path('/tmp/test/audio.mp3', '/output', 'json')
        PosixPath('/output/audio.json')

    Note:
        This function does not create the output directory. The caller is
        responsible for ensuring the directory exists before writing.
    """
    input_p = Path(input_path)

    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = input_p.parent

    output_file = out_dir / f"{input_p.stem}.{format}"
    return output_file
