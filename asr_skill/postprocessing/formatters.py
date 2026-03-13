"""Output formatters for transcription results.

This module provides formatting functions to convert ASR transcription results
into user-friendly output formats (TXT, JSON, SRT, ASS, Markdown).

Output Format Decisions (from CONTEXT.md):
- TXT format: timestamps inline [HH:MM:SS.mmm] Speaker A: text
- JSON format: segment level (array of segments with text, start, end, confidence, speaker_id, is_overlap)
- SRT format: standard subtitle format with comma-separated timestamps
- ASS format: advanced subtitle format with speaker-specific styling
- Markdown format: readable document with speaker sections
- Timestamp format: standard SRT style HH:MM:SS.mmm (period for TXT/MD, comma for SRT)
- Speaker labels: alphabetical (Speaker A, Speaker B, Speaker C)
- Overlap detection: [OVERLAP] tag in TXT, is_overlap field in JSON
"""

import json
from typing import Any

from asr_skill.postprocessing.speakers import detect_overlaps, format_speaker_label


# ASS subtitle format header with speaker-specific styles
# Colors are in ASS BGR format: &H00BBGGRR (note: BGR, not RGB)
# High-contrast colors for speaker differentiation
ASS_HEADER = """[Script Info]
Title: ASR Transcription
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: SpeakerA,Microsoft YaHei,48,&H0000FFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: SpeakerB,Microsoft YaHei,48,&H00FF00FF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: SpeakerC,Microsoft YaHei,48,&H00FFFF00,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: SpeakerD,Microsoft YaHei,48,&H0000FF00,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: SpeakerE,Microsoft YaHei,48,&H000080FF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


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


def format_srt_timestamp(ms: int) -> str:
    """Convert milliseconds to SRT timestamp format.

    SRT uses comma for milliseconds separator (HH:MM:SS,mmm), unlike the
    standard timestamp format which uses period.

    Args:
        ms: Time in milliseconds

    Returns:
        str: Timestamp in HH:MM:SS,mmm format (comma for milliseconds)

    Example:
        >>> format_srt_timestamp(3661500)
        '01:01:01,500'
        >>> format_srt_timestamp(0)
        '00:00:00,000'
    """
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def format_srt(result: dict[str, Any]) -> str:
    """Format transcription result as SRT subtitle format.

    SRT format consists of numbered subtitle blocks, each containing:
    1. Index number (1-indexed)
    2. Timestamp line: start --> end (comma for milliseconds)
    3. Text (with speaker prefix if available)
    4. Blank line

    Speaker labels are included in brackets: [Speaker A] text

    Args:
        result: Transcription result dict with 'sentence_info' or 'sentences' key
                containing list of segment dicts

    Returns:
        str: SRT formatted subtitle content

    Example:
        >>> result = {
        ...     "sentence_info": [
        ...         {"sentence": "Hello world", "start": 0, "end": 1500, "spk": 0},
        ...         {"sentence": "Goodbye", "start": 2000, "end": 3000, "spk": 1}
        ...     ]
        ... }
        >>> print(format_srt(result))
        1
        00:00:00,000 --> 00:00:01,500
        [Speaker A] Hello world
        <BLANKLINE>
        2
        00:00:02,000 --> 00:00:03,000
        [Speaker B] Goodbye
        <BLANKLINE>
    """
    segments = result.get("sentence_info") or result.get("sentences", [])

    if not segments:
        return ""

    # Detect overlaps (time-based fallback)
    segments = detect_overlaps(segments)

    lines = []
    for i, segment in enumerate(segments, 1):
        start = format_srt_timestamp(segment["start"])
        end = format_srt_timestamp(segment["end"])
        text = segment.get("sentence", segment.get("text", ""))

        # Add speaker prefix if available
        if "spk" in segment:
            speaker = format_speaker_label(segment["spk"])
            text = f"[{speaker}] {text}"

        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")  # Blank line between entries

    return "\n".join(lines)


def format_ass_timestamp(ms: int) -> str:
    """Convert milliseconds to ASS timestamp format.

    ASS uses H:MM:SS.cc format where cc is centiseconds (1/100 second),
    not milliseconds. Hours are not zero-padded.

    Args:
        ms: Time in milliseconds

    Returns:
        str: Timestamp in H:MM:SS.cc format

    Example:
        >>> format_ass_timestamp(3661500)
        '1:01:01.50'
        >>> format_ass_timestamp(0)
        '0:00:00.00'
    """
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    centis = (ms % 1000) // 10
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centis:02d}"


def format_ass(result: dict[str, Any]) -> str:
    """Format transcription result as ASS subtitle format with speaker styling.

    ASS format provides advanced styling capabilities. This implementation
    uses speaker-specific styles with distinct colors for differentiation.

    The output includes:
    - Script Info section with metadata
    - V4+ Styles section with Default and SpeakerA-E styles
    - Events section with Dialogue lines

    Speaker colors (BGR format):
    - SpeakerA: Yellow (&H0000FFFF)
    - SpeakerB: Cyan (&H00FF00FF)
    - SpeakerC: Magenta (&H00FFFF00)
    - SpeakerD: Green (&H0000FF00)
    - SpeakerE: Orange (&H000080FF)

    Args:
        result: Transcription result dict with 'sentence_info' or 'sentences' key
                containing list of segment dicts

    Returns:
        str: ASS formatted subtitle content

    Example:
        >>> result = {
        ...     "sentence_info": [
        ...         {"sentence": "Hello world", "start": 0, "end": 1500, "spk": 0}
        ...     ]
        ... }
        >>> output = format_ass(result)
        >>> '[Script Info]' in output
        True
        >>> 'SpeakerA' in output
        True
    """
    segments = result.get("sentence_info") or result.get("sentences", [])

    if not segments:
        return ASS_HEADER

    # Detect overlaps (time-based fallback)
    segments = detect_overlaps(segments)

    lines = [ASS_HEADER]

    for segment in segments:
        start = format_ass_timestamp(segment["start"])
        end = format_ass_timestamp(segment["end"])
        text = segment.get("sentence", segment.get("text", ""))

        # Use speaker-specific style
        if "spk" in segment:
            style = f"Speaker{chr(ord('A') + segment['spk'])}"
        else:
            style = "Default"

        # Escape ASS special characters
        text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")

        lines.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{text}")

    return "\n".join(lines)
