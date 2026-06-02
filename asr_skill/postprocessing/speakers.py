"""Speaker label utilities for diarization output.

This module provides utilities for formatting speaker labels and detecting
overlapping speech segments.

Output Format Decisions (from CONTEXT.md):
- Speaker labels: Alphabetical (Speaker A, Speaker B, Speaker C)
- TXT output: [HH:MM:SS.mmm] Speaker A: text
- JSON output: speaker_id field per segment
- Overlap TXT: [OVERLAP] tag before segment
- Overlap JSON: is_overlap boolean field

When diarization is unavailable (e.g., SenseVoice):
- All speech is labeled as "未识别人声" (unidentified speaker)
- Overlap detection is skipped (no speaker data to compare)
"""

from typing import Any

# Label used when speaker diarization is not available
UNIDENTIFIED_SPEAKER = "未识别人声"


def format_speaker_label(speaker_id: int) -> str:
    """Convert numeric speaker ID to alphabetical label.

    Args:
        speaker_id: Numeric speaker ID from diarization (0, 1, 2, ...),
                    or -1 for unidentified speaker.

    Returns:
        Alphabetical label: "Speaker A", "Speaker B", etc.
        Returns "未识别人声" for speaker_id == -1.

    Example:
        >>> format_speaker_label(0)
        'Speaker A'
        >>> format_speaker_label(2)
        'Speaker C'
        >>> format_speaker_label(-1)
        '未识别人声'
    """
    if speaker_id < 0:
        return UNIDENTIFIED_SPEAKER
    return f"Speaker {chr(ord('A') + speaker_id)}"


def has_diarization_data(sentence_info: list[dict[str, Any]]) -> bool:
    """Check if any segment in the result has speaker diarization data.

    Args:
        sentence_info: List of segment dicts.

    Returns:
        True if at least one segment has a 'spk' key, False otherwise.
    """
    if not sentence_info:
        return False
    return any("spk" in seg for seg in sentence_info)


def detect_overlaps(sentence_info: list[dict[str, Any]], threshold: float = 0.5) -> list[dict[str, Any]]:
    """Mark overlapping segments based on time overlap.

    Uses time-based detection as fallback when model-based detection unavailable.
    Overlap is detected when two segments from different speakers overlap by >= threshold.

    If the segments have no speaker data (no 'spk' key in any segment), overlap
    detection is skipped and all segments are marked as non-overlapping.

    Args:
        sentence_info: List of segment dicts with start, end, spk fields
        threshold: Overlap ratio threshold (default 0.5 = 50%)

    Returns:
        sentence_info with is_overlap field added to each segment

    Note:
        FunASR's postprocess() handles model-based overlap detection internally.
        This function provides time-based detection for segments not marked by the model.
    """
    # Initialize all segments as non-overlapping
    for seg in sentence_info:
        seg.setdefault("is_overlap", False)

    # Skip overlap detection if no speaker data available (e.g., SenseVoice)
    if not has_diarization_data(sentence_info):
        return sentence_info

    for seg in sentence_info:
        # Skip segments without speaker data
        if "spk" not in seg:
            continue

        for other in sentence_info:
            if seg is other:
                continue
            # Skip other segments without speaker data
            if "spk" not in other:
                continue
            if seg["spk"] == other["spk"]:
                continue

            # Calculate overlap duration
            overlap_start = max(seg["start"], other["start"])
            overlap_end = min(seg["end"], other["end"])
            overlap_duration = max(0, overlap_end - overlap_start)

            if overlap_duration > 0:
                seg_duration = seg["end"] - seg["start"]
                if seg_duration > 0:
                    overlap_ratio = overlap_duration / seg_duration
                    if overlap_ratio >= threshold:
                        seg["is_overlap"] = True
                        break

    return sentence_info
