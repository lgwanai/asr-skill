"""Output formatters for transcription results.

This module provides formatting functions to convert ASR transcription results
into user-friendly output formats (TXT and JSON).

Output Format Decisions (from CONTEXT.md):
- TXT format: timestamps inline [HH:MM:SS.mmm] Speaker A: text
- JSON format: segment level (array of segments with text, start, end, confidence, speaker_id, is_overlap)
- Timestamp format: standard SRT style HH:MM:SS.mmm
- Speaker labels: alphabetical (Speaker A, Speaker B, Speaker C)
- Overlap detection: [OVERLAP] tag in TXT, is_overlap field in JSON
"""

import json
from typing import Any

from asr_skill.postprocessing.speakers import detect_overlaps, format_speaker_label


def format_timestamp(ms: int) -> str:
    """Convert milliseconds to SRT-style timestamp format.

    Args:
        ms: Time in milliseconds

    Returns:
        str: Timestamp in HH:MM:SS.mmm format

    Example:
        >>> format_timestamp(3661500)
        '01:01:01.500'
        >>> format_timestamp(0)
        '00:00:00.000'
    """
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def format_txt(result: dict[str, Any]) -> str:
    """Format transcription result as plain text with timestamps and speaker labels.

    Each segment is formatted as: [HH:MM:SS.mmm] Speaker A: transcribed text
    Overlapping segments are prefixed with [OVERLAP].

    Args:
        result: Transcription result dict with 'sentence_info' or 'sentences' key
                containing list of segment dicts with 'text', 'start', 'end', and
                optionally 'spk' fields

    Returns:
        str: Formatted text with timestamps and speaker labels, one segment per line

    Example:
        >>> result = {
        ...     "sentence_info": [
        ...         {"sentence": "Hello world", "start": 0, "end": 1500, "spk": 0},
        ...         {"sentence": "Goodbye", "start": 2000, "end": 3000, "spk": 1}
        ...     ]
        ... }
        >>> print(format_txt(result))
        [00:00:00.000] Speaker A: Hello world
        [00:00:02.000] Speaker B: Goodbye
    """
    # Use sentence_info for speaker data, fall back to sentences
    segments = result.get("sentence_info") or result.get("sentences", [])

    if not segments:
        return ""

    # Detect overlaps (time-based fallback)
    segments = detect_overlaps(segments)

    lines = []
    for segment in segments:
        timestamp = format_timestamp(segment["start"])

        # Speaker label (if available)
        if "spk" in segment:
            speaker = format_speaker_label(segment["spk"])
            text = segment.get("sentence", segment.get("text", ""))
        else:
            speaker = None
            text = segment.get("text", "")

        # Overlap tag
        overlap_tag = "[OVERLAP] " if segment.get("is_overlap") else ""

        # Format line
        if speaker:
            lines.append(f"[{timestamp}] {overlap_tag}{speaker}: {text}")
        else:
            lines.append(f"[{timestamp}] {text}")

    return "\n".join(lines)


def format_json(result: dict[str, Any]) -> str:
    """Format transcription result as structured JSON with speaker labels.

    Creates a JSON array of segment objects, each containing:
    - text: The transcribed text
    - start: Start time in milliseconds
    - end: End time in milliseconds
    - confidence: Recognition confidence score (defaults to 1.0 if not present)
    - speaker_id: Speaker label (e.g., "Speaker A") if diarization enabled
    - is_overlap: Boolean flag for overlapping speech segments

    Args:
        result: Transcription result dict with 'sentence_info' or 'sentences' key
                containing list of segment dicts

    Returns:
        str: JSON string with array of segment objects, formatted with indent=2

    Example:
        >>> result = {
        ...     "sentence_info": [
        ...         {"sentence": "Hello world", "start": 0, "end": 1500, "confidence": 0.95, "spk": 0}
        ...     ]
        ... }
        >>> print(format_json(result))
        [
          {
            "text": "Hello world",
            "start": 0,
            "end": 1500,
            "confidence": 0.95,
            "speaker_id": "Speaker A",
            "is_overlap": false
          }
        ]
    """
    segments_data = result.get("sentence_info") or result.get("sentences", [])

    if not segments_data:
        return "[]"

    # Detect overlaps (time-based fallback)
    segments_data = detect_overlaps(segments_data)

    segments = []
    for seg in segments_data:
        segment_data = {
            "text": seg.get("sentence", seg.get("text", "")),
            "start": seg["start"],
            "end": seg["end"],
            "confidence": seg.get("confidence", 1.0),
        }

        # Add speaker info if available
        if "spk" in seg:
            segment_data["speaker_id"] = format_speaker_label(seg["spk"])

        # Add overlap flag
        segment_data["is_overlap"] = seg.get("is_overlap", False)

        segments.append(segment_data)

    return json.dumps(segments, ensure_ascii=False, indent=2)
