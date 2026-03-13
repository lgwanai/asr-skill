# Feature Research

**Domain:** Automatic Speech Recognition (ASR) / Speech-to-Text Transcription Tools
**Researched:** 2026-03-13
**Confidence:** MEDIUM (WebSearch results limited, WebFetch blocked; combining training knowledge with available sources)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Audio/Video File Input** | Core functionality - users want to transcribe files | LOW | Support common formats (MP3, WAV, MP4, M4A, etc.). FunASR requires 16kHz audio internally. |
| **Text Transcript Output** | Primary deliverable - the transcribed text | LOW | Plain text is minimum; structured formats add value. |
| **Timestamp Markers** | Users need to correlate text with audio positions | MEDIUM | Word-level or segment-level timestamps essential for subtitle generation and verification. |
| **Multi-format Export (SRT/VTT/JSON)** | Different use cases require different formats | LOW | SRT for video subtitles, JSON for programmatic access, TXT for readability. |
| **Progress Indication** | Long files take time; users need feedback | LOW | Essential for files >5 minutes. Percentage or time remaining. |
| **Error Handling** | Files fail; graceful degradation expected | LOW | Unsupported formats, corrupted files, memory issues need clear messages. |
| **Chinese Language Support** | Core market requirement for this project | MEDIUM | FunASR Paraformer optimized for Chinese; this is a strength. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Speaker Diarization** | Distinguish multiple speakers; critical for meetings/interviews | HIGH | CAM++ model in FunASR provides this. Outputs speaker labels per segment. |
| **Punctuation Restoration** | Raw ASR output lacks punctuation; adds readability | MEDIUM | CT-Transformer model in FunASR. Significant UX improvement. |
| **Hotword Injection** | Domain-specific terms (names, jargon) recognized correctly | MEDIUM | FunASR supports hotword biasing. Critical for technical content. |
| **Long Audio Handling** | Process 1+ hour files without memory issues | HIGH | Requires VAD-based segmentation and streaming processing. FunASR VAD FSMN model. |
| **Local/Offline Processing** | Privacy-preserving; no data leaves machine | MEDIUM | Core differentiator for this project. Appeals to enterprise, legal, medical users. |
| **Automatic Hardware Detection** | Seamless GPU/CPU fallback without user config | MEDIUM | CUDA for NVIDIA, MPS for Apple Silicon, CPU fallback. Reduces friction. |
| **Video Audio Extraction** | Users want to transcribe video directly, not extract audio first | LOW | FFmpeg integration. Significant UX improvement for video content. |
| **Intelligent Segmentation** | VAD-based breaks at speech boundaries vs fixed time chunks | MEDIUM | Better semantic coherence in segments. FunASR VAD FSMN provides this. |
| **Claude Code Skill Integration** | Direct `/asr` command in Claude Code workflow | MEDIUM | Unique integration point for AI-assisted workflows. |
| **Structured Markdown Output** | Meeting notes format with speaker labels and timestamps | LOW | Higher-value output than raw text. Enables downstream AI summarization. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time Streaming Transcription** | Live meeting transcription, immediate feedback | Requires different architecture (WebSocket, streaming inference); higher latency sensitivity; FunASR supports but adds significant complexity for v1 | Focus on offline batch processing first; add streaming in v2 |
| **Multi-language Support** | Broader market reach | Dilutes Chinese optimization; requires separate models; increases maintenance burden | Focus on Chinese excellence first; add English/other languages as separate models later |
| **Cloud Processing** | Offload computation, access from anywhere | Contradicts core privacy value proposition; adds infrastructure costs, latency, reliability concerns | Embrace local processing as differentiator; optimize for local hardware |
| **Speaker Identification (Named)** | Know WHO said what, not just "Speaker 1" | Requires enrollment/voice registration; privacy concerns; adds complexity | Provide speaker labeling (Speaker A/B); let users map to names post-transcription |
| **Auto-summarization** | AI-generated meeting summaries | Adds LLM dependency; summarization quality varies; may miss important details | Export structured transcript for external AI tools (including Claude) to summarize |
| **Web UI** | Visual interface for non-technical users | Significant development effort; security considerations; maintenance overhead | CLI + Claude Skill for technical users; Web UI as future consideration |

## Feature Dependencies

```
[Audio/Video Input]
    └──requires──> [Format Detection & Audio Extraction (FFmpeg)]
                       └──requires──> [Sampling Rate Conversion (to 16kHz)]

[Speaker Diarization]
    └──requires──> [VAD Segmentation]
    └──requires──> [Speaker Embedding Model (CAM++)]

[Long Audio Handling]
    └──requires──> [VAD Segmentation]
    └──requires──> [Memory-efficient Processing Pipeline]

[Subtitle Export (SRT/ASS)]
    └──requires──> [Timestamp Markers]

[Hotword Injection]
    └──requires──> [Configuration System]
    └──requires──> [Model Hotword Interface]

[Hardware Auto-Detection]
    └──requires──> [Platform Detection (CUDA/MPS/CPU)]
    └──requires──> [Model Loading for Detected Backend]

[Punctuation Restoration]
    └──enhances──> [Text Transcript Output]

[Claude Code Skill]
    └──requires──> [CLI Entry Point]
    └──requires──> [JSON Output Format]
```

### Dependency Notes

- **Subtitle Export requires Timestamp Markers:** SRT/VTT formats need start/end times per segment. Without timestamps, cannot generate subtitles.
- **Speaker Diarization requires VAD Segmentation:** Cannot cluster speaker embeddings without first identifying speech segments.
- **Long Audio Handling requires VAD Segmentation:** Memory-efficient processing needs intelligent chunking at speech boundaries, not fixed time intervals.
- **Hardware Auto-Detection enhances all inference:** Users get best performance without manual configuration, but core functionality works without it.
- **Punctuation Restoration enhances Text Output:** Adds significant readability but transcript is usable without it.

## MVP Definition

### Launch With (v1)

Minimum viable product - what's needed to validate the concept.

- [x] **Audio/Video File Input** - Core functionality; support common formats via FFmpeg
- [x] **Text Transcript Output** - Primary deliverable
- [x] **Timestamp Markers** - Essential for verification and subtitle generation
- [x] **Multi-format Export (TXT/SRT/JSON)** - Different use cases
- [x] **Chinese Language Support** - Core market; FunASR strength
- [x] **Long Audio Handling** - Process 1+ hour files; key differentiator
- [x] **Hardware Auto-Detection** - Reduces friction; GPU/CPU fallback

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] **Speaker Diarization** - Critical for meetings/interviews; add when core transcription stable
- [ ] **Punctuation Restoration** - Significant UX improvement; relatively easy to add
- [ ] **Hotword Injection** - Domain-specific accuracy; requires configuration system
- [ ] **Video Audio Extraction** - UX improvement; FFmpeg integration
- [ ] **Claude Code Skill Integration** - Unique distribution channel

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Real-time Streaming** - Requires architecture change; different use case
- [ ] **Multi-language Support** - Separate models; broader market
- [ ] **Web UI** - Significant development effort; different user segment
- [ ] **Named Speaker Identification** - Requires enrollment; privacy considerations

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Audio/Video Input | HIGH | LOW | P1 |
| Text Transcript Output | HIGH | LOW | P1 |
| Timestamp Markers | HIGH | MEDIUM | P1 |
| Multi-format Export | HIGH | LOW | P1 |
| Chinese Language Support | HIGH | MEDIUM | P1 |
| Long Audio Handling | HIGH | HIGH | P1 |
| Hardware Auto-Detection | MEDIUM | MEDIUM | P1 |
| Speaker Diarization | HIGH | HIGH | P2 |
| Punctuation Restoration | HIGH | MEDIUM | P2 |
| Hotword Injection | MEDIUM | MEDIUM | P2 |
| Video Audio Extraction | MEDIUM | LOW | P2 |
| Claude Code Skill | MEDIUM | MEDIUM | P2 |
| Real-time Streaming | MEDIUM | HIGH | P3 |
| Multi-language | MEDIUM | HIGH | P3 |
| Web UI | LOW | HIGH | P3 |
| Named Speaker ID | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | OpenAI Whisper | Otter.ai | Descript | FunASR (Our Approach) |
|---------|---------------|----------|----------|----------------------|
| **Processing** | Cloud API | Cloud | Cloud | Local (Privacy advantage) |
| **Speaker Diarization** | Limited | Yes | Yes | Yes (CAM++) |
| **Punctuation** | Yes | Yes | Yes | Yes (CT-Transformer) |
| **Hotword Support** | No | Limited | No | Yes (Config-based) |
| **Chinese Accuracy** | Good | Limited | Limited | Excellent (Paraformer optimized) |
| **Long Audio** | API limits | Yes | Yes | Yes (VAD segmentation) |
| **Pricing** | Per-minute | Subscription | Subscription | Free (local) |
| **Real-time** | No | Yes | Limited | v2 consideration |
| **Export Formats** | JSON/TXT/SRT/VTT | TXT/PDF | TXT/SRT | TXT/SRT/ASS/JSON/MD |

### Competitive Positioning

**vs. OpenAI Whisper:**
- Our advantage: Local processing (privacy), Chinese optimization, hotword support, no API costs
- Their advantage: Multi-language, established ecosystem, easy API integration

**vs. Otter.ai/Descript:**
- Our advantage: Local processing, no subscription, Chinese accuracy, developer-friendly (CLI/Skill)
- Their advantage: Web UI, real-time, editing tools, collaboration features

**Our niche:** Privacy-conscious users, Chinese content, developer/AI workflows, long-form content, technical/domain-specific content (hotwords).

## Sources

- FunASR GitHub documentation (training knowledge - HIGH confidence for model capabilities)
- OpenAI Whisper paper and documentation (training knowledge - HIGH confidence)
- ASR tool comparison research (WebSearch - MEDIUM confidence)
- Speaker diarization technology overview (WebSearch - MEDIUM confidence)
- Transcription software feature analysis (WebSearch - MEDIUM confidence)

---
*Feature research for: ASR/Speech Recognition Tools*
*Researched: 2026-03-13*
