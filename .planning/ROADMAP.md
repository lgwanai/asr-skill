# Roadmap: ASR-Skill

## Overview

Build a local speech recognition tool that delivers high-accuracy Chinese transcription with speaker diarization, progressing from core ASR infrastructure through speaker identification, enhanced outputs, hotword support, and finally integration interfaces. Each phase delivers a complete, verifiable capability that builds on the previous.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core ASR Pipeline** - Foundation for audio transcription with hardware auto-detection
- [x] **Phase 2: Speaker Diarization** - Multi-speaker identification and labeling
- [ ] **Phase 3: Enhanced Outputs** - Subtitle formats, progress indication, and confidence scores
- [ ] **Phase 4: Hotwords** - Domain-specific vocabulary enhancement via config and CLI
- [ ] **Phase 5: Integration** - CLI, Claude Code Skill, and Python module interfaces

## Phase Details

### Phase 1: Core ASR Pipeline
**Goal**: Users can transcribe audio/video files to text with automatic hardware detection and basic output formats
**Depends on**: Nothing (first phase)
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, AUDIO-01, AUDIO-03, AUDIO-04, TRAN-01, TRAN-02, TRAN-03, OUTP-01, OUTP-04, OUTP-06
**Success Criteria** (what must be TRUE):
  1. User can input an audio file (MP3, WAV, M4A, FLAC) and receive text transcription
  2. User receives word-level timestamps for each transcribed segment
  3. System automatically detects and uses optimal hardware (CUDA GPU, Apple MPS, or CPU fallback)
  4. User receives transcription output as TXT and JSON files in the same directory as input
  5. System processes audio files longer than 1 hour without crashing
**Plans**: 4 plans in 3 waves

Plans:
- [x] 01-01-PLAN.md — Device detection and audio preprocessing modules
- [x] 01-02-PLAN.md — Output formatters and path utilities
- [x] 01-03-PLAN.md — FunASR model pipeline and Python API
- [x] 01-04-PLAN.md — CLI entry point and package configuration

### Phase 2: Speaker Diarization
**Goal**: Users can identify and distinguish multiple speakers in transcribed audio
**Depends on**: Phase 1
**Requirements**: AUDIO-02, SPKR-01, SPKR-02, SPKR-03
**Success Criteria** (what must be TRUE):
  1. User can input a video file (MP4, AVI, MKV) and audio is automatically extracted for transcription
  2. User sees different speakers labeled (Speaker A, Speaker B, etc.) in the transcription output
  3. User can see when each speaker starts and stops speaking (timestamp ranges per speaker)
  4. Overlapping speech segments are marked in the output
**Plans**: 4 plans in 3 waves

Plans:
- [x] 02-01-PLAN.md — Video extraction module with FFmpeg CLI
- [x] 02-02-PLAN.md — Speaker diarization model and formatters
- [x] 02-03-PLAN.md — API integration with video and speaker support
- [x] 02-04-PLAN.md — End-to-end verification checkpoint

### Phase 3: Enhanced Outputs
**Goal**: Users can export transcriptions in multiple formats suitable for different use cases
**Depends on**: Phase 2
**Requirements**: AUDIO-05, TRAN-04, OUTP-02, OUTP-03, OUTP-05
**Success Criteria** (what must be TRUE):
  1. User sees progress indication (percentage or status) during transcription processing
  2. User can export transcription as SRT subtitle format with timestamps
  3. User can export transcription as ASS subtitle format with speaker-based styling
  4. User can export transcription as Markdown with speaker sections
  5. User can see confidence scores for each word in JSON output
**Plans**: 3 plans in 3 waves

Plans:
- [x] 03-01-PLAN.md — SRT, ASS, and Markdown formatters
- [ ] 03-02-PLAN.md — Progress indication and word-level confidence
- [ ] 03-03-PLAN.md — CLI and API integration for new formats

### Phase 4: Hotwords
**Goal**: Users can improve recognition accuracy for domain-specific terms
**Depends on**: Phase 3
**Requirements**: HOTW-01, HOTW-02, HOTW-03
**Success Criteria** (what must be TRUE):
  1. User can provide hotwords via a JSON or YAML configuration file
  2. User can provide hotwords directly via CLI arguments for quick adjustments
  3. Domain-specific terms in hotwords are recognized more accurately than without hotwords
**Plans**: TBD

### Phase 5: Integration
**Goal**: Users can invoke transcription through multiple interfaces (CLI, Skill, Python)
**Depends on**: Phase 4
**Requirements**: INTG-01, INTG-02, INTG-03, INTG-04
**Success Criteria** (what must be TRUE):
  1. User can run transcription via CLI with a file path argument
  2. User can select output format via CLI flag (e.g., --format srt)
  3. User can invoke transcription from Claude Code using /asr command
  4. User can import the package as a Python module and call transcription programmatically
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core ASR Pipeline | 4/4 | Complete | 01-01, 01-02, 01-03, 01-04 |
| 2. Speaker Diarization | 4/4 | Complete | 02-01, 02-02, 02-03, 02-04 |
| 3. Enhanced Outputs | 1/3 | In Progress | 03-01 |
| 4. Hotwords | 0/TBD | Not started | - |
| 5. Integration | 0/TBD | Not started | - |

---
*Roadmap created: 2026-03-13*
*Depth: standard*
*Last updated: 2026-03-14 after 03-01 completion*
