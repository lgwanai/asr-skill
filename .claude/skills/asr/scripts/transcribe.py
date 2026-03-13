#!/usr/bin/env python3
"""Quick transcription script for ASR skill."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from asr_skill import transcribe, SUPPORTED_FORMATS, SUPPORTED_VIDEO_FORMATS


def main():
    if len(sys.argv) < 2:
        print("Usage: transcribe.py <audio_or_video_file> [format] [output_dir]")
        print(f"Supported formats: {SUPPORTED_FORMATS + SUPPORTED_VIDEO_FORMATS}")
        print("Output formats: txt, json, srt, ass, md")
        sys.exit(1)

    input_file = sys.argv[1]
    format_type = sys.argv[2] if len(sys.argv) > 2 else "txt"
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        result = transcribe(input_file, output_dir=output_dir, format=format_type)
        print(f"\nTranscription complete!")
        print(f"Output: {result['output_path']}")
        if 'speakers' in result:
            print(f"Speakers detected: {', '.join(result['speakers'])}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
