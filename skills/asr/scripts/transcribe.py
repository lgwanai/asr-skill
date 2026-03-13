#!/usr/bin/env python3
"""Batch transcription script for ASR skill.

Usage:
    python3 transcribe.py <input_file> [-f format] [-o output_dir]

Examples:
    python3 transcribe.py audio.mp3
    python3 transcribe.py audio.mp3 -f json -o ./output
    python3 transcribe.py video.mp4 -f srt

Supported input formats:
    Audio: .mp3, .wav, .m4a, .flac, .ogg, .opus
    Video: .mp4, .avi, .mkv, .mov, .webm

Output formats:
    txt  - Plain text with timestamps (default)
    json - Structured JSON with metadata
    srt  - SubRip subtitles
    ass  - ASS/SSA subtitles
    md   - Markdown with speaker sections
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to python path to allow importing asr_skill
# This assumes the script is located at skills/asr/scripts/transcribe.py
# and the package is at asr_skill/
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from asr_skill import transcribe
    from asr_skill.core.device import get_device_with_fallback
except ImportError:
    print("Error: Could not import 'asr_skill' package.")
    print(f"Checked path: {project_root}")
    print("Please ensure you are running this script from within the project or the package is installed.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio/video files using local ASR with speaker diarization.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_file", help="Path to input audio or video file")
    parser.add_argument(
        "-f", "--format", 
        choices=["txt", "json", "srt", "ass", "md"], 
        default="txt",
        help="Output format (default: txt)"
    )
    parser.add_argument(
        "-o", "--output-dir", 
        help="Directory to save output (default: same as input file)"
    )
    
    args = parser.parse_args()
    input_path = Path(args.input_file).resolve()

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    # Check device status
    device, fallback = get_device_with_fallback()
    if fallback:
        print("Warning: GPU not available, using CPU (slower).")
    else:
        print(f"Using device: {device}")

    print(f"Transcribing: {input_path.name}")
    print(f"Output format: {args.format}")
    
    try:
        # Define a simple progress callback since we don't have rich here (or assume we might not)
        # But if the package uses rich, we can't easily hook into it without using the CLI's approach.
        # The transcribe function accepts a progress_callback.
        
        def simple_progress(current, total):
            if total > 0:
                percent = int(current / total * 100)
                sys.stdout.write(f"\rProgress: {percent}%")
                sys.stdout.flush()
        
        result = transcribe(
            str(input_path), 
            output_dir=args.output_dir, 
            format=args.format,
            progress_callback=simple_progress
        )
        
        print("\n\n✓ Transcription complete!")
        print(f"  Output saved to: {result['output_path']}")
        
        if 'speakers' in result and result['speakers']:
            print(f"  Speakers detected: {', '.join(result['speakers'])}")
            
    except Exception as e:
        print(f"\nError during transcription: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
