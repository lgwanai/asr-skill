#!/usr/bin/env python3
"""Batch transcription script for ASR skill.

Usage:
    python transcribe.py <input_file> [format] [output_dir]
    python transcribe.py audio.mp3 json ./output
    python transcribe.py video.mp4 srt

Supported input formats:
    Audio: .mp3, .wav, .m4a, .flac
    Video: .mp4, .avi, .mkv

Output formats:
    txt  - Plain text with timestamps (default)
    json - Structured JSON with metadata
    srt  - SubRip subtitles
    ass  - ASS/SSA subtitles
    md   - Markdown with speaker sections
"""

import sys
from pathlib import Path

# Add parent directories to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from asr_skill import transcribe, SUPPORTED_FORMATS, SUPPORTED_VIDEO_FORMATS


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print(f"Supported audio formats: {SUPPORTED_FORMATS}")
        print(f"Supported video formats: {SUPPORTED_VIDEO_FORMATS}")
        sys.exit(1)

    input_file = sys.argv[1]
    format_type = sys.argv[2] if len(sys.argv) > 2 else "txt"
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None

    # Validate input file
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    # Validate format
    valid_formats = ["txt", "json", "srt", "ass", "md"]
    if format_type not in valid_formats:
        print(f"Error: Invalid format '{format_type}'")
        print(f"Valid formats: {valid_formats}")
        sys.exit(1)

    try:
        result = transcribe(input_file, output_dir=output_dir, format=format_type)
        print(f"\n✓ Transcription complete!")
        print(f"  Output: {result['output_path']}")
        if 'speakers' in result and result['speakers']:
            print(f"  Speakers: {', '.join(result['speakers'])}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
