# Output Format Specifications

## TXT Format

Plain text with inline timestamps and speaker labels:

```
[00:00:01.234] Speaker A: Hello, welcome to the meeting.
[00:00:05.678] Speaker B: Thank you for joining today.
[OVERLAP] [00:00:10.123] Speaker A: Let's get started.
```

## JSON Format

Structured JSON with full metadata:

```json
[
  {
    "text": "Hello, welcome to the meeting.",
    "start": 1234,
    "end": 5678,
    "confidence": 0.95,
    "speaker_id": "Speaker A",
    "is_overlap": false,
    "words": [
      {"word": "Hello", "start": 1234, "end": 1500, "confidence": 0.98},
      {"word": "welcome", "start": 1500, "end": 2000, "confidence": 0.95}
    ]
  }
]
```

## SRT Format

SubRip subtitle format with comma-separated milliseconds:

```
1
00:00:01,234 --> 00:00:05,678
[Speaker A] Hello, welcome to the meeting.

2
00:00:05,678 --> 00:00:10,123
[Speaker B] Thank you for joining today.
```

## ASS Format

Advanced SubStation Alpha with speaker-specific styling:

```
[Script Info]
Title: Transcription
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour
Style: Default,Arial,16,&H00FFFFFF
Style: SpeakerA,Arial,16,&H00FFFF
Style: SpeakerB,Arial,16,&H00FFFF00

[Events]
Format: Layer, Start, End, Style, Text
Dialogue: 0,0:00:01.23,0:00:05.68,SpeakerA,Hello, welcome to the meeting.
```

## Markdown Format

Speaker-grouped sections:

```markdown
## Speaker A

- [00:00:01] Hello, welcome to the meeting.
- [00:00:10] Let's get started.

## Speaker B

- [00:00:05] Thank you for joining today.
```

## Timestamp Format

All timestamps use SRT-style format: `HH:MM:SS.mmm` (hours:minutes:seconds.milliseconds)

- TXT: `[HH:MM:SS.mmm]`
- JSON: milliseconds as integer
- SRT: `HH:MM:SS,mmm` (comma for milliseconds per spec)
- ASS: `H:MM:SS.cc` (centiseconds)
- Markdown: `[HH:MM:SS]`
