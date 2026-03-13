# Pitfalls Research

**Domain:** FunASR Speech Recognition Tool
**Researched:** 2026-03-13
**Confidence:** MEDIUM (Based on GitHub issues analysis, official docs unavailable)

## Critical Pitfalls

### Pitfall 1: Memory Explosion on Long Audio Processing

**What goes wrong:**
Processing long audio files (1+ hours) causes memory to grow unbounded until OOM crash. A 15-hour audio file consumed 100GB memory and was killed. Memory is not released after inference completes.

**Why it happens:**
- FunASR loads entire audio segments into memory without streaming
- VAD segmentation creates many intermediate tensors that accumulate
- The `batch_size_s` parameter controls segment size but memory isn't freed between batches
- GPU memory leaks when processing multiple files sequentially

**How to avoid:**
- Set `batch_size_s` to smaller values (e.g., 300 seconds max per batch)
- Process long audio in chunks with explicit memory cleanup between chunks
- Use `torch.cuda.empty_cache()` after processing large segments
- Monitor memory usage and implement graceful degradation
- Consider restarting the process after processing very long files

**Warning signs:**
- Memory usage grows linearly with audio length
- GPU memory not released after inference
- Process becomes increasingly slow on subsequent files

**Phase to address:** Phase 1 (Core ASR Pipeline) - Memory management must be designed from the start

---

### Pitfall 2: GPU Falls Back to CPU on Subsequent Runs

**What goes wrong:**
First inference runs on GPU as expected, but subsequent inferences silently fall back to CPU, causing 10x+ slowdown. Users report seeing "cuda:0" initially, then CPU usage on later runs.

**Why it happens:**
- FunASR's `AutoModel` keeps mutable state in `kwargs` dictionaries
- Long inferences mutate these dicts (e.g., `torch_threads` grows from default 4)
- This state corruption causes device mismatch on subsequent calls
- Known issue in FunASR 1.3.0 and 1.3.1

**How to avoid:**
- Create fresh `AutoModel` instance for each long inference session
- Use `disable_update=True` in AutoModel initialization
- Explicitly set `device` parameter on every `generate()` call
- Monitor device usage with `nvidia-smi` during inference
- Consider using ONNX runtime for more predictable device behavior

**Warning signs:**
- First inference fast, subsequent inferences slow
- Progress bar shows CPU operations instead of GPU
- `torch.cuda.current_device()` returns different results

**Phase to address:** Phase 1 (Core ASR Pipeline) - Device management must be explicit

---

### Pitfall 3: Speaker Diarization Model Incompatibility

**What goes wrong:**
Using `cam++` speaker model with certain ASR models (like SenseVoice) causes errors: "can not get `timestamp`" or "Only paraformer-large-vad-punc and speech_seaco_paraformer can predict timestamp."

**Why it happens:**
- Speaker diarization requires word-level timestamps from the ASR model
- Not all ASR models output timestamps
- SenseVoice and some newer models don't provide the timestamp format expected by cam++
- The pipeline silently fails or throws cryptic errors

**How to avoid:**
- Use `paraformer-zh` or `speech_paraformer-large-vad-punc` for speaker diarization
- Verify model compatibility before combining ASR + speaker models
- Check for timestamp output in model documentation
- Test speaker diarization with short audio first

**Warning signs:**
- KeyError when accessing timestamp fields
- "can not get `timestamp`" error messages
- Speaker labels are missing or all same speaker

**Phase to address:** Phase 2 (Speaker Diarization) - Model compatibility must be verified

---

### Pitfall 4: VAD Model Configuration Dependencies

**What goes wrong:**
- Disabling VAD causes punc model to also be disabled (unexpected dependency)
- Enabling VAD with certain models causes timestamp format errors
- `decibel_thres` parameter values above default cause IndexError crash

**Why it happens:**
- FunASR's pipeline has implicit dependencies between models
- VAD output format is expected by downstream models
- Default parameters work, but edge cases are not handled
- Version differences in timestamp format handling

**How to avoid:**
- Always test with VAD enabled if using punc or speaker models
- Use default VAD parameters unless absolutely necessary
- Set `vad_kwargs={"max_single_segment_time": 30000}` explicitly
- Test VAD configuration early in development

**Warning signs:**
- Punctuation missing when VAD disabled
- TypeError or KeyError in timestamp processing
- VAD crashes with non-default threshold values

**Phase to address:** Phase 1 (Core ASR Pipeline) - VAD configuration must be explicit

---

### Pitfall 5: Performance Regression Between Versions

**What goes wrong:**
Upgrading from FunASR 1.3.0 to 1.3.1 caused 10x latency increase (70-80ms to ~800ms for same clips on RTX 4080/4090).

**Why it happens:**
- Breaking changes in internal model handling between versions
- PyPI package may not include latest GitHub fixes
- Timestamp format compatibility issues between versions

**How to avoid:**
- Pin exact FunASR version in requirements
- Test performance after any version upgrade
- Check GitHub issues for known regressions
- Consider installing from source for critical fixes

**Warning signs:**
- Sudden performance drop after pip upgrade
- Inference time inconsistent with documentation claims
- Error messages referencing missing fixes

**Phase to address:** Phase 1 (Core ASR Pipeline) - Version pinning is critical

---

### Pitfall 6: Dual-Channel Audio Processing Errors

**What goes wrong:**
Stereo/dual-channel audio causes shape mismatch errors: `data.shape=[2, 11520]` but `data_len=[11520]` - expected `data_len=[11520, 11520]`.

**Why it happens:**
- `extract_fbank` function assumes mono audio
- Shape inference fails for multi-channel input
- No automatic channel mixing/selection

**How to avoid:**
- Convert stereo to mono before processing
- Use ffmpeg to extract single channel: `ffmpeg -i input.wav -ac 1 output.wav`
- Implement audio preprocessing to normalize channel count
- Validate audio format before ASR processing

**Warning signs:**
- Shape mismatch errors in preprocessing
- IndexError in audio loading
- Silent failures producing empty results

**Phase to address:** Phase 1 (Core ASR Pipeline) - Audio preprocessing must handle all formats

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip VAD for short clips | Faster processing | No timestamps, punc fails | Never - VAD required for full pipeline |
| Use CPU fallback silently | Works everywhere | 10x slower, user frustration | Never - must warn user |
| Ignore speaker model compatibility | Simpler code | Runtime errors | Never - validate before use |
| Single batch_size_s for all audio | Simpler config | OOM on long audio | Never - must adapt to file size |
| Hardcode model versions | Predictable behavior | Miss security/bug fixes | Only with thorough testing |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| ffmpeg | Missing installation | Auto-detect and install/bundle |
| CUDA | Assuming GPU available | Check with `torch.cuda.is_available()` before setting device |
| MPS (Apple Silicon) | Same code as CUDA | Use "mps" device, handle MPS-specific tensor issues |
| ModelScope | Network required for download | Pre-download models, use local paths |
| ONNX export | Expecting same results as PyTorch | Test extensively, some models have ONNX bugs |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| kwargs state mutation | Slowdown on repeated inference | Fresh model instance per session | 2nd+ inference on same model |
| Memory leak | Growing memory usage | Explicit cleanup, process restart | After 10+ long files |
| GPU underutilization | CPU bottleneck | Profile with nvidia-smi, optimize batch size | Large batch_size_s values |
| Streaming not supported | Long wait for final result | Accept offline-only for v1 | Real-time use cases |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Downloading models at runtime | Supply chain attack, network dependency | Pre-download and verify model checksums |
| Untrusted audio input | Malformed audio crashes process | Validate audio format, catch exceptions |
| Exposing inference endpoint | DoS via large files | Implement file size limits, timeouts |
| Storing transcripts in temp files | Information disclosure | Use secure temp directory, clean up after use |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent CPU fallback | User wonders why it's slow | Show clear warning: "GPU not available, using CPU (10x slower)" |
| No progress indicator | User thinks it's frozen | Show progress bar with ETA |
| Cryptic model errors | User can't debug | Provide actionable error messages with fix suggestions |
| Empty results | User doesn't know what went wrong | Log warnings for silent failures, provide diagnostics |
| Long wait without feedback | User cancels prematurely | Show chunk-by-chunk progress |

## "Looks Done But Isn't" Checklist

- [ ] **Speaker Diarization:** Often missing timestamps - verify timestamp output with test audio
- [ ] **Long Audio Processing:** Works on 5-minute test but OOMs on 1-hour - test with realistic file sizes
- [ ] **GPU Acceleration:** Works once but falls back on repeat - verify device stays consistent
- [ ] **Memory Cleanup:** Appears to work but leaks over time - run 10+ files and monitor memory
- [ ] **VAD + Punc:** Punc silently disabled without VAD - test both enabled and disabled states
- [ ] **Hotwords:** May not work in online/realtime mode - verify hotword functionality per mode
- [ ] **Stereo Audio:** Crashes on dual-channel - test with stereo input explicitly

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Memory OOM | HIGH | Restart process, implement chunking with cleanup |
| GPU fallback | MEDIUM | Recreate model instance, set device explicitly |
| Model incompatibility | MEDIUM | Switch to compatible model (paraformer-zh) |
| Version regression | LOW | Pin working version, check GitHub for fixes |
| Stereo audio error | LOW | Pre-process to mono, retry |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Memory Explosion | Phase 1 | Test with 1+ hour audio, monitor memory |
| GPU Fallback | Phase 1 | Run 5+ inferences, verify device consistency |
| Speaker Model Incompatibility | Phase 2 | Test cam++ with chosen ASR model |
| VAD Configuration Dependencies | Phase 1 | Test VAD + punc together and separately |
| Performance Regression | Phase 1 | Pin version, benchmark before/after upgrades |
| Dual-Channel Audio | Phase 1 | Test with stereo input file |

## Sources

- GitHub Issues Analysis (modelscope/FunASR repository, March 2026)
  - Issue #2116: Memory OOM on 15-hour audio
  - Issue #2652: GPU to CPU fallback on subsequent runs
  - Issue #2706, #2121, #2662: Speaker diarization model incompatibility
  - Issue #2787: Sampling rate validation overhead
  - Issue #2793: Dual-channel audio shape mismatch
  - Issue #2809: Performance regression 1.3.0 to 1.3.1
  - Issue #2815: VAD affects punc model
  - Issue #2827: High concurrency errors in Triton deployment
  - Issue #2780: VAD decibel_thres crash
  - Issue #2831: PyPI package missing GitHub fixes
- Project Requirements (idea.md, PROJECT.md)

---
*Pitfalls research for: FunASR Speech Recognition Tool*
*Researched: 2026-03-13*
