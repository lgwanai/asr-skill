# Project Research Summary

**Project:** ASR Skill - FunASR-based Speech Recognition Tool
**Domain:** Automatic Speech Recognition (ASR) / Speech-to-Text
**Researched:** 2026-03-13
**Confidence:** MEDIUM

## Executive Summary

This is a local speech recognition tool built on Alibaba's FunASR framework, optimized for Chinese language transcription with speaker diarization. The recommended approach uses FunASR's AutoModel pipeline composition pattern, chaining VAD (FSMN-VAD), ASR (Paraformer-Large), punctuation (CT-Transformer), and speaker diarization (CAM++) models. The key competitive advantages are local processing (privacy), Chinese optimization, hotword support, and integration with Claude Code as a skill.

The primary risks center on memory management for long audio files and FunASR's mutable state issues causing GPU-to-CPU fallback on subsequent runs. These must be addressed from Phase 1 through explicit memory cleanup, device management, and version pinning (FunASR 1.3.1 with `disable_update=True`). The architecture follows a sequential pipeline with hardware-adaptive device selection supporting CUDA, MPS (Apple Silicon), and CPU fallback.

## Key Findings

### Recommended Stack

The core stack centers on FunASR 1.3.1 with PyTorch 2.9.1+ as the deep learning backend. FunASR provides the complete ASR pipeline including models. FFmpeg 6.0+ is essential for multi-format audio/video input. Supporting libraries handle audio processing (librosa, soundfile), output formats (srt, ass), and CLI interface (click, rich).

**Core technologies:**
- **FunASR 1.3.1**: ASR framework with integrated models - optimized for Chinese, includes all pipeline components
- **PyTorch 2.9.1+**: Deep learning backend - required by FunASR, supports CUDA 12.x and MPS
- **FFmpeg 6.0+**: Audio/video processing - format conversion, audio extraction, resampling to 16kHz
- **ModelScope**: Model distribution hub - handles model download and caching (~2.6GB total for all models)

### Expected Features

**Must have (table stakes):**
- Audio/Video file input with format detection - users expect to transcribe any common media file
- Text transcript output with timestamps - primary deliverable, essential for subtitles
- Multi-format export (TXT/SRT/JSON) - different use cases require different formats
- Long audio handling - process 1+ hour files without memory issues
- Hardware auto-detection - seamless GPU/CPU fallback without user configuration

**Should have (competitive):**
- Speaker diarization (CAM++) - distinguish multiple speakers, critical for meetings
- Punctuation restoration (CT-Transformer) - adds readability to raw ASR output
- Hotword injection - domain-specific terms recognized correctly
- Claude Code Skill integration - unique distribution channel for AI-assisted workflows

**Defer (v2+):**
- Real-time streaming transcription - requires different architecture
- Multi-language support - dilutes Chinese optimization
- Web UI - significant development effort, different user segment

### Architecture Approach

The system follows a modular pipeline architecture where FunASR's AutoModel orchestrates model composition. Audio preprocessing extracts and resamples to 16kHz, then VAD segments speech, ASR transcribes with timestamps, punctuation restores sentence boundaries, and speaker diarization clusters voices. Output formatters generate format-specific files (TXT, SRT, ASS, JSON, Markdown).

**Major components:**
1. **Audio Preprocessing** - Format detection, video audio extraction (FFmpeg), resampling to 16kHz
2. **VAD Model (FSMN-VAD)** - Voice activity detection, long audio segmentation, speech boundary detection
3. **ASR Model (Paraformer-Large)** - Non-autoregressive speech recognition with timestamp prediction
4. **Punctuation Model (CT-Transformer)** - Punctuation restoration and sentence boundary detection
5. **Speaker Model (CAM++)** - Speaker embedding extraction and clustering for diarization
6. **Output Formatters** - Generate TXT, SRT, ASS, JSON, Markdown with speaker labels

### Critical Pitfalls

1. **Memory Explosion on Long Audio** - Process 1+ hour files with `batch_size_s=300`, explicit `torch.cuda.empty_cache()`, and chunked processing with cleanup between segments
2. **GPU-to-CPU Fallback on Subsequent Runs** - Use `disable_update=True` in AutoModel, explicitly set device on every `generate()` call, or create fresh model instance per session
3. **Speaker Model Incompatibility** - CAM++ requires timestamp output; must use Paraformer-Large, not SenseVoice
4. **VAD Configuration Dependencies** - Always enable VAD when using punctuation or speaker models; set `vad_kwargs={"max_single_segment_time": 30000}`
5. **Dual-Channel Audio Errors** - Convert stereo to mono before processing; validate audio format in preprocessing

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Core ASR Pipeline
**Rationale:** Foundation for everything else; must get device management, memory handling, and audio preprocessing correct from the start
**Delivers:** Working transcription with timestamps, basic output formats (TXT, JSON), hardware auto-detection
**Addresses:** Audio/video input, text output, timestamps, multi-format export, long audio handling, hardware auto-detection
**Avoids:** Memory explosion (chunked processing), GPU fallback (explicit device management), stereo audio errors (preprocessing normalization)
**Stack:** FunASR, PyTorch, FFmpeg, librosa, soundfile, click, rich

### Phase 2: Speaker Diarization
**Rationale:** Builds on stable Phase 1 pipeline; adds high-value feature for meetings/interviews
**Delivers:** Speaker-labeled transcripts, speaker-aware output formats
**Uses:** CAM++ model from ModelScope, Paraformer-Large (already integrated)
**Implements:** Speaker embedding extraction, clustering, speaker label assignment
**Avoids:** Model incompatibility (verified Paraformer-Large + CAM++ pairing)
**Stack:** FunASR spk_model, scipy for clustering

### Phase 3: Enhanced Output & UX
**Rationale:** Polishes the output quality and user experience once core functionality is stable
**Delivers:** Punctuation restoration, SRT/ASS subtitle formats, Markdown output, progress indication
**Uses:** CT-Transformer punctuation model, srt/ass libraries, tqdm
**Implements:** Output formatters for subtitle formats, structured meeting notes format

### Phase 4: Hotwords & Configuration
**Rationale:** Advanced feature for domain-specific accuracy; requires configuration system
**Delivers:** Hotword injection, YAML configuration, hotword templates
**Uses:** PyYAML, FunASR hotword interface
**Implements:** Configuration loading, hotword file parsing, hotword injection into pipeline

### Phase 5: Claude Code Skill Integration
**Rationale:** Unique distribution channel; depends on stable CLI interface
**Delivers:** `/asr` command in Claude Code, JSON output for programmatic access
**Uses:** Claude Code skill framework, CLI from Phase 1
**Implements:** Skill definition, command parsing, result formatting

### Phase Ordering Rationale

- Phase 1 must come first as all other phases depend on a working transcription pipeline
- Speaker diarization (Phase 2) requires stable ASR with timestamps; adding it early ensures model compatibility is validated
- Output formats (Phase 3) are separated from Phase 1 to allow iteration on core stability first
- Hotwords (Phase 4) require configuration infrastructure and are an enhancement, not core functionality
- Skill integration (Phase 5) depends on mature CLI interface and output formats

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Speaker diarization clustering parameters may need tuning based on audio characteristics; CAM++ model has known edge cases
- **Phase 4:** Hotword format and injection mechanism needs FunASR-specific research; documentation is sparse

Phases with standard patterns (skip research-phase):
- **Phase 1:** Well-documented FunASR AutoModel pattern; extensive examples in official repo
- **Phase 3:** Standard output formatting; srt/ass libraries have straightforward APIs
- **Phase 5:** Claude Code skill pattern is documented in skill development guides

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | PyPI versions verified HIGH; FunASR model IDs and compatibility MEDIUM (WebFetch blocked) |
| Features | MEDIUM | Based on training knowledge and WebSearch; limited external validation |
| Architecture | HIGH | Official FunASR documentation and Model Zoo; clear patterns established |
| Pitfalls | MEDIUM | GitHub issues analysis; official docs unavailable for some issues |

**Overall confidence:** MEDIUM

### Gaps to Address

- **FunASR version stability:** PyPI package may lag GitHub; need to test 1.3.1 thoroughly before committing, check GitHub issues for post-release fixes
- **MPS (Apple Silicon) compatibility:** FunASR may have tensor operation limitations on MPS; need explicit testing on Apple Silicon hardware
- **Hotword injection format:** Documentation sparse; need to research exact hotword format and injection mechanism during Phase 4 planning
- **Long audio memory profile:** Memory behavior needs empirical testing; theoretical mitigation strategies need validation with real workloads

## Sources

### Primary (HIGH confidence)
- FunASR GitHub Repository: https://github.com/modelscope/FunASR
- FunASR PyPI Package: https://pypi.org/project/funasr/
- Model Zoo Documentation: https://github.com/alibaba-damo-academy/FunASR/blob/main/docs/model_zoo/modelscope_models.md

### Secondary (MEDIUM confidence)
- GitHub Issues Analysis (modelscope/FunASR, March 2026) - Pitfalls, performance issues, model compatibility
- FunASR documentation (training knowledge) - Model capabilities, AutoModel patterns
- OpenAI Whisper paper and documentation - Competitor analysis, feature landscape

### Tertiary (LOW confidence)
- WebSearch results (limited availability) - ASR tool comparisons, speaker diarization technology

---
*Research completed: 2026-03-13*
*Ready for roadmap: yes*
