"""Output formatters for transcription results.

This module provides formatting functions to convert ASR transcription results
into user-friendly output formats (TXT and JSON).

Output Format Decisions (from CONTEXT.md):
- TXT format: timestamps inline [HH:MM:SS.mmm] text
- JSON format: segment level (array of segments with text, start, end, confidence)
- Timestamp format: standard SRT style HH:MM:SS.mmm
"""

import json
from typing import Any


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
    """Format transcription result as plain text with inline timestamps.

    Each segment is formatted as: [HH:MM:SS.mmm] transcribed text

    Args:
        result: Transcription result dict with 'sentences' key containing
                list of segment dicts with 'text', 'start', 'end' fields

    Returns:
        str: Formatted text with timestamps, one segment per line

    Example:
        >>> result = {
        ...     "sentences": [
        ...         {"text": "Hello world", "start": 0, "end": 1500},
        ...         {"text": "Goodbye", "start": 2000, "end": 3000}
        ...     ]
        ... }
        >>> print(format_txt(result))
        [00:00:00.000] Hello world
        [00:00:02.000] Goodbye
    """
    sentences = result.get("sentences", [])

    if not sentences:
        return ""

    lines = []
    for segment in sentences:
        timestamp = format_timestamp(segment["start"])
        text = segment["text"]
        lines.append(f"[{timestamp}] {text}")

    return "\n".join(lines)


def format_json(result: dict[str, Any]) -> str:
    """Format transcription result as structured JSON.

    Creates a JSON array of segment objects, each containing:
    - text: The transcribed text
    - start: Start time in milliseconds
    - end: End time in milliseconds
    - confidence: Recognition confidence score (defaults to 1.0 if not present)

    Args:
        result: Transcription result dict with 'sentences' key containing
                list of segment dicts

    Returns:
        str: JSON string with array of segment objects, formatted with indent=2

    Example:
        >>> result = {
        ...     "sentences": [
        ...         {"text": "Hello world", "start": 0, "end": 1500, "confidence": 0.95}
        ...     ]
        ... }
        >>> print(format_json(result))
        [
          {
            "text": "Hello world",
            "start": 0,
            "end": 1500,
            "confidence": 0.95
          }
        ]
    """
    sentences = result.get("sentences", [])

    if not sentences:
        return "[]"

    segments = []
    for seg in sentences:
        segment_data = {
            "text": seg["text"],
            "start": seg["start"],
            "end": seg["end"],
            "confidence": seg.get("confidence", 1.0),
        }
        segments.append(segment_data)

    return json.dumps(segments, ensure_ascii=False, indent=2)
