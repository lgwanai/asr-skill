# Requirements: ASR-Skill

**Defined:** 2026-03-13
**Core Value:** 在保障数据隐私（本地化处理）的前提下，实现对超长音频/视频的高精度转写，并通过说话人分离技术输出结构化的智能纪要。

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Core Infrastructure

- [ ] **CORE-01**: System auto-detects available hardware (CUDA GPU, Apple MPS, CPU) and selects optimal device
- [ ] **CORE-02**: System validates Python version (≥3.10) and dependencies before execution
- [ ] **CORE-03**: System auto-downloads and caches FunASR models to local `models/` directory
- [ ] **CORE-04**: System handles GPU-to-CPU fallback gracefully with user notification

### Audio Input

- [ ] **AUDIO-01**: User can input audio files in MP3, WAV, M4A, FLAC formats
- [ ] **AUDIO-02**: User can input video files in MP4, AVI, MKV formats with automatic audio extraction
- [ ] **AUDIO-03**: System automatically resamples audio to 16kHz for optimal recognition
- [ ] **AUDIO-04**: System handles long audio (>1 hour) with VAD-based intelligent segmentation
- [ ] **AUDIO-05**: System provides progress indication during processing

### Transcription

- [ ] **TRAN-01**: User receives text transcription of audio content
- [ ] **TRAN-02**: User receives word-level timestamps for each transcribed segment
- [ ] **TRAN-03**: System adds punctuation using CT-Transformer model
- [ ] **TRAN-04**: System provides per-word confidence scores in output

### Speaker Diarization

- [ ] **SPKR-01**: System identifies and labels different speakers (Speaker A, B, C...)
- [ ] **SPKR-02**: User receives speaker timestamps (start/end times per speaker)
- [ ] **SPKR-03**: System marks overlapping speech segments in output

### Output Formats

- [ ] **OUTP-01**: User can export transcription as plain TXT file
- [ ] **OUTP-02**: User can export as SRT subtitle format with timestamps
- [ ] **OUTP-03**: User can export as ASS subtitle format with speaker styling
- [ ] **OUTP-04**: User can export as structured JSON with full metadata
- [ ] **OUTP-05**: User can export as Markdown with speaker sections
- [ ] **OUTP-06**: Output files are saved in same directory as input by default

### Hotwords

- [ ] **HOTW-01**: User can provide hotwords via JSON/YAML config file
- [ ] **HOTW-02**: User can provide hotwords via CLI arguments
- [ ] **HOTW-03**: Hotwords improve recognition accuracy for domain-specific terms

### Integration

- [ ] **INTG-01**: User can invoke transcription via Claude Code Skill (/asr command)
- [ ] **INTG-02**: User can run transcription via CLI with file path argument
- [ ] **INTG-03**: User can import as Python module for programmatic use
- [ ] **INTG-04**: CLI supports output format selection via flag

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Real-time Processing

- **REAL-01**: Real-time streaming transcription
- **REAL-02**: Live audio capture from microphone

### Advanced Features

- **ADVN-01**: Named speaker identification (pre-registered voices)
- **ADVN-02**: Auto-summarization of transcripts
- **ADVN-03**: Multi-language support (English, Japanese, etc.)

### Deployment

- **DEPL-01**: Docker containerization
- **DEPL-02**: Web UI interface

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Cloud processing | Core value is local/privacy-first processing |
| Real-time streaming | v1 focuses on offline file processing |
| Named speaker identification | Privacy concerns and complexity |
| Auto-summarization | LLM dependency adds complexity |
| Web UI | CLI and skill interfaces sufficient for v1 |
| Multi-language | Focus on Chinese language for v1 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 1 | Pending |
| CORE-02 | Phase 1 | Pending |
| CORE-03 | Phase 1 | Pending |
| CORE-04 | Phase 1 | Pending |
| AUDIO-01 | Phase 1 | Pending |
| AUDIO-02 | Phase 2 | Pending |
| AUDIO-03 | Phase 1 | Pending |
| AUDIO-04 | Phase 1 | Pending |
| AUDIO-05 | Phase 3 | Pending |
| TRAN-01 | Phase 1 | Pending |
| TRAN-02 | Phase 1 | Pending |
| TRAN-03 | Phase 1 | Pending |
| TRAN-04 | Phase 3 | Pending |
| SPKR-01 | Phase 2 | Pending |
| SPKR-02 | Phase 2 | Pending |
| SPKR-03 | Phase 2 | Pending |
| OUTP-01 | Phase 1 | Pending |
| OUTP-02 | Phase 3 | Pending |
| OUTP-03 | Phase 3 | Pending |
| OUTP-04 | Phase 3 | Pending |
| OUTP-05 | Phase 3 | Pending |
| OUTP-06 | Phase 1 | Pending |
| HOTW-01 | Phase 4 | Pending |
| HOTW-02 | Phase 4 | Pending |
| HOTW-03 | Phase 4 | Pending |
| INTG-01 | Phase 5 | Pending |
| INTG-02 | Phase 5 | Pending |
| INTG-03 | Phase 5 | Pending |
| INTG-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-13*
*Last updated: 2026-03-13 after initial definition*
