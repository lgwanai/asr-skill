"""Xiaomi MiMo ASR API client (MiMo-V2.5-ASR).

This module provides an API client for cloud-based ASR transcription via
the Xiaomi MiMo platform. The MiMo ASR API uses the chat completions
endpoint with a special ``input_audio`` content type — audio is Base64-encoded
and sent as a data URL in the request body.

Large audio files are intelligently split at silence points before upload,
avoiding mid-word cuts and preserving transcription quality.

API Reference:
    https://platform.xiaomimimo.com/docs/zh-CN/usage-guide/Speech-Recognition

Key constraints:
    - Base64-encoded audio must be ≤ 10 MB per chunk
    - Supported formats: WAV and MP3
    - Only model: ``mimo-v2.5-asr``
    - Language options: ``auto``, ``zh``, ``en``

Configuration (from config.txt "api" section):
    api.url:           Base URL (default: https://api.xiaomimimo.com/v1)
    api.key:           API key for the ``api-key`` header (or MIMO_API_KEY env var)
    api.model:         Model name (default: "mimo-v2.5-asr")
    api.language:      Language hint — "auto", "zh", or "en" (default: "auto")
    api.timeout:       Request timeout in seconds (default: 300)
    api.max_file_mb:   Max raw audio size in MB per chunk (default: 7)
    api.headers:       Extra HTTP headers as JSON key-value pairs (optional)
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable
from urllib import request, error

# ── Constants ────────────────────────────────────────────────────────────────

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds

BASE64_EXPANSION_RATIO = 4.0 / 3.0  # Base64 → raw ratio
API_MAX_BASE64_BYTES = 10 * 1024 * 1024  # 10 MB per chunk

DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"

# Silence detection parameters
SILENCE_DURATION_SEC = 1.0   # minimum silence to consider a split point
SILENCE_THRESHOLD_DB = -40   # silence threshold in dB
CHUNK_OVERLAP_SEC = 0.0      # no overlap (MiMo API returns no timestamps for dedup)

# Max chunk duration guess: at 16kHz 16-bit mono, 1 sec ≈ 32 KB.
# 7 MB raw ≈ ~218 seconds. Use 180 as safe margin.
BYTES_PER_SEC_16K_MONO = 16000 * 2  # 32 KB/s
FALLBACK_CHUNK_SEC = 180


# ── API Client ───────────────────────────────────────────────────────────────

class ASRAPIClient:
    """Client for Xiaomi MiMo ASR transcription via chat completions API."""

    def __init__(self, config: dict[str, Any]) -> None:
        api_cfg = config.get("api", {})

        self.api_key: str = api_cfg.get("key", "")
        if not self.api_key:
            raise ValueError(
                "API mode requires 'api.key' in config.txt or MIMO_API_KEY env var.\n"
                "Get your key at: https://platform.xiaomimimo.com/profile"
            )

        base_url: str = api_cfg.get("url", "").strip()
        if not base_url:
            base_url = DEFAULT_BASE_URL
        self.endpoint: str = f"{base_url.rstrip('/')}/chat/completions"

        self.model: str = api_cfg.get("model", "mimo-v2.5-asr")
        self.language: str = api_cfg.get("language", "auto")
        if self.language not in ("auto", "zh", "en"):
            raise ValueError(
                f"Invalid api.language '{self.language}'. Expected 'auto', 'zh', or 'en'."
            )

        self.timeout: int = api_cfg.get("timeout", 300)
        max_file_mb: int = api_cfg.get("max_file_mb", 7)
        self.max_chunk_bytes: int = max_file_mb * 1024 * 1024
        self.extra_headers: dict[str, str] = dict(api_cfg.get("headers", {}))

    # ── Public API ──────────────────────────────────────────────────────────

    def transcribe(
        self,
        audio_path: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any] | None:
        """Transcribe an audio file via the MiMo ASR API.

        Files exceeding ``max_file_mb`` are automatically split at silence
        points for intelligent chunking.

        Args:
            audio_path: Path to preprocessed 16kHz mono WAV file.
            progress_callback: Optional callback(current_chunk, total_chunks).

        Returns:
            Normalized result dict with ``text`` and ``sentence_info`` keys.
        """
        file_size = os.path.getsize(audio_path)

        if file_size <= self.max_chunk_bytes:
            return self._transcribe_single(audio_path)

        return self._transcribe_chunked(audio_path, progress_callback)

    # ── Single Upload ───────────────────────────────────────────────────────

    def _transcribe_single(self, audio_path: str) -> dict[str, Any] | None:
        """Transcribe a single file in one API call."""
        file_size_mb = os.path.getsize(audio_path) / 1024 / 1024

        # Validate size
        estimated_b64 = int(os.path.getsize(audio_path) * BASE64_EXPANSION_RATIO) + 100
        if estimated_b64 > API_MAX_BASE64_BYTES:
            raise ValueError(
                f"Audio too large: {file_size_mb:.1f} MB raw "
                f"(~{estimated_b64 / 1024 / 1024:.1f} MB Base64). "
                f"API limit: {API_MAX_BASE64_BYTES / 1024 / 1024:.0f} MB Base64."
            )

        print(f"[API] Reading {file_size_mb:.1f} MB, encoding...")
        data_url = self._encode_audio(audio_path)

        print(f"[API] Sending to MiMo (model={self.model}, lang={self.language})...")
        raw = self._post_asr(data_url)
        if raw is None:
            return None

        return self._normalize_response(raw)

    # ── Intelligent Chunked Upload ──────────────────────────────────────────

    def _transcribe_chunked(
        self,
        audio_path: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any] | None:
        """Split large audio at silence points, transcribe chunks, merge."""
        file_size_mb = os.path.getsize(audio_path) / 1024 / 1024
        print(f"\n[API] File {file_size_mb:.1f} MB exceeds chunk limit "
              f"({self.max_chunk_bytes / 1024 / 1024:.0f} MB).")
        print("[API] Detecting silence points for intelligent splitting...")

        chunk_paths = self._split_at_silence(audio_path)
        print(f"[API] Split into {len(chunk_paths)} chunks at natural pauses.\n")

        all_texts: list[str] = []

        for i, chunk_path in enumerate(chunk_paths):
            if progress_callback:
                progress_callback(i + 1, len(chunk_paths))

            chunk_mb = os.path.getsize(chunk_path) / 1024 / 1024
            print(f"[API] Chunk {i+1}/{len(chunk_paths)} ({chunk_mb:.1f} MB)...")

            raw = self._post_asr(self._encode_audio(chunk_path))
            if raw is None:
                print(f"[API]   Warning: chunk {i+1} returned no result.")
                continue

            result = self._normalize_response(raw)
            text = result.get("text", "") if result else ""
            if text:
                all_texts.append(text)

            # Clean up chunk temp file
            try:
                Path(chunk_path).unlink(missing_ok=True)
            except OSError:
                pass

        if progress_callback:
            progress_callback(len(chunk_paths), len(chunk_paths))

        if not all_texts:
            return None

        return {
            "text": "".join(all_texts),
            "sentence_info": [
                {"sentence": "".join(all_texts), "start": 0, "end": 0}
            ],
        }

    # ── Silence Detection ───────────────────────────────────────────────────

    def _detect_silence_points(self, audio_path: str) -> list[float]:
        """Find silence breakpoints in an audio file using ffmpeg.

        Uses the ``silencedetect`` filter to locate regions of low volume,
        then returns the midpoint of each silence region as a candidate
        split point.

        Args:
            audio_path: Path to audio file.

        Returns:
            List of split-point timestamps in seconds.
        """
        if not self._has_ffmpeg():
            print("[API] ffmpeg not available, falling back to time-based split.")
            return self._fallback_split_points(audio_path)

        # Run ffmpeg silencedetect
        cmd = [
            "ffmpeg", "-i", audio_path,
            "-af", f"silencedetect=noise={SILENCE_THRESHOLD_DB}dB:"
                   f"d={SILENCE_DURATION_SEC}",
            "-f", "null", "-",
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._fallback_split_points(audio_path)

        # Parse output: silence_start and silence_end lines
        # Example: [silencedetect @ ...] silence_start: 15.23
        #          [silencedetect @ ...] silence_end: 17.45 | silence_duration: 2.22
        silence_starts: list[float] = []
        silence_ends: list[float] = []

        for line in result.stderr.splitlines():
            if "silence_start" in line:
                try:
                    silence_starts.append(float(line.split("silence_start:")[1].strip()))
                except (ValueError, IndexError):
                    pass
            elif "silence_end" in line:
                try:
                    silence_ends.append(float(line.split("silence_end:")[1].strip()))
                except (ValueError, IndexError):
                    pass

        if not silence_starts:
            return self._fallback_split_points(audio_path)

        # Use midpoints of silence regions as split points
        split_points: list[float] = []
        for start, end in zip(silence_starts, silence_ends):
            midpoint = (start + end) / 2.0
            split_points.append(midpoint)

        return split_points

    def _fallback_split_points(self, audio_path: str) -> list[float]:
        """Generate evenly-spaced split points when silence detection fails.

        Uses FALLBACK_CHUNK_SEC intervals.
        """
        duration = self._get_duration(audio_path)
        if duration <= 0:
            return []
        points = []
        t = FALLBACK_CHUNK_SEC
        while t < duration:
            points.append(t)
            t += FALLBACK_CHUNK_SEC
        return points

    # ── Audio Splitting ─────────────────────────────────────────────────────

    def _split_at_silence(self, audio_path: str) -> list[str]:
        """Split audio into chunks at silence points, each under max_chunk_bytes.

        Algorithm:
        1. Detect silence split-point candidates.
        2. Calculate target chunk byte size.
        3. Walk through split points, selecting those that produce chunks
           within the size limit.
        4. Extract chunks using ffmpeg (or librosa as fallback).

        Returns:
            List of temporary chunk WAV file paths.
        """
        silence_points = self._detect_silence_points(audio_path)
        total_duration = self._get_duration(audio_path)
        total_bytes = os.path.getsize(audio_path)

        if total_duration <= 0 or not silence_points:
            # Can't split intelligently — do single time-based chunk
            return self._fallback_chunk(audio_path)

        # Calculate target duration per chunk (with 10% safety margin)
        bytes_per_sec = total_bytes / total_duration if total_duration > 0 else BYTES_PER_SEC_16K_MONO
        target_chunk_bytes = int(self.max_chunk_bytes * 0.85)
        max_chunk_sec = target_chunk_bytes / bytes_per_sec if bytes_per_sec > 0 else FALLBACK_CHUNK_SEC

        # Select split points that produce chunks ≤ max_chunk_sec
        selected_points: list[float] = []
        last_point = 0.0

        for pt in silence_points:
            if pt <= last_point + 1.0:
                continue  # too close to previous point
            if pt - last_point > max_chunk_sec:
                continue  # gap too large (can't split here — use what we have)
            selected_points.append(pt)
            last_point = pt

        # Ensure the remaining tail isn't too long
        if selected_points and total_duration - selected_points[-1] > max_chunk_sec * 1.5:
            # Add another point from the tail
            t = selected_points[-1] + max_chunk_sec
            if t < total_duration:
                selected_points.append(t)

        if not selected_points:
            return self._fallback_chunk(audio_path)

        # Extract chunks using ffmpeg
        return self._extract_chunks(audio_path, selected_points, total_duration)

    def _extract_chunks(
        self, audio_path: str, split_points: list[float], total_duration: float,
    ) -> list[str]:
        """Extract audio chunks using ffmpeg at given split points.

        Each chunk includes a small overlap at the start (except the first)
        to prevent word cuts at boundaries.
        """
        if self._has_ffmpeg():
            return self._extract_chunks_ffmpeg(audio_path, split_points, total_duration)
        else:
            return self._extract_chunks_librosa(audio_path, split_points)

    def _extract_chunks_ffmpeg(
        self, audio_path: str, split_points: list[float], total_duration: float,
    ) -> list[str]:
        """Extract chunks with ffmpeg (fast, streaming)."""
        ffmpeg = self._get_ffmpeg()
        tmp_dir = tempfile.mkdtemp(prefix="asr_chunks_")
        chunk_paths: list[str] = []

        points = [0.0] + split_points + [total_duration]

        for i in range(len(points) - 1):
            start = max(0, points[i] - (CHUNK_OVERLAP_SEC if i > 0 else 0))
            end = points[i + 1]
            duration = end - start

            out_path = os.path.join(tmp_dir, f"chunk_{i:04d}.wav")
            cmd = [
                ffmpeg,
                "-ss", str(start),
                "-t", str(duration),
                "-i", audio_path,
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                "-y", "-loglevel", "error",
                out_path,
            ]
            try:
                subprocess.run(cmd, capture_output=True, check=True, timeout=60)
                if os.path.getsize(out_path) > 1024:
                    chunk_paths.append(out_path)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                print(f"[API] Warning: ffmpeg chunk {i} failed: {e}")

        return chunk_paths or [audio_path]

    def _extract_chunks_librosa(
        self, audio_path: str, split_points: list[float],
    ) -> list[str]:
        """Extract chunks with librosa (slower, always available)."""
        import librosa
        import soundfile as sf

        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        total_samples = len(y)
        chunk_paths: list[str] = []

        points = [0.0] + split_points + [total_samples / sr]
        overlap_samples = int(CHUNK_OVERLAP_SEC * sr)

        for i in range(len(points) - 1):
            start_sample = max(0, int(points[i] * sr) - (overlap_samples if i > 0 else 0))
            end_sample = min(total_samples, int(points[i + 1] * sr))
            chunk = y[start_sample:end_sample]

            fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="asr_chunk_")
            os.close(fd)
            sf.write(tmp_path, chunk, sr)
            chunk_paths.append(tmp_path)

        return chunk_paths

    def _fallback_chunk(self, audio_path: str) -> list[str]:
        """Last-resort: single time-based chunk via ffmpeg segment."""
        if self._has_ffmpeg():
            return self._fallback_chunk_ffmpeg(audio_path)
        return [audio_path]  # Return original — will likely fail if too big

    def _fallback_chunk_ffmpeg(self, audio_path: str) -> list[str]:
        """Use ffmpeg segment muxer for basic splitting."""
        total_duration = self._get_duration(audio_path)
        num_chunks = max(1, int(total_duration / FALLBACK_CHUNK_SEC) + 1)
        chunk_sec = total_duration / num_chunks

        ffmpeg = self._get_ffmpeg()
        tmp_dir = tempfile.mkdtemp(prefix="asr_chunks_")
        chunk_paths: list[str] = []

        for i in range(num_chunks):
            start = max(0, i * chunk_sec - (CHUNK_OVERLAP_SEC if i > 0 else 0))
            dur = chunk_sec + (CHUNK_OVERLAP_SEC if i > 0 else 0)
            out_path = os.path.join(tmp_dir, f"chunk_{i:04d}.wav")
            cmd = [
                ffmpeg, "-ss", str(start), "-t", str(dur),
                "-i", audio_path,
                "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                "-y", "-loglevel", "error", out_path,
            ]
            try:
                subprocess.run(cmd, capture_output=True, check=True, timeout=60)
                if os.path.getsize(out_path) > 1024:
                    chunk_paths.append(out_path)
            except subprocess.CalledProcessError:
                pass

        return chunk_paths or [audio_path]

    # ── Audio Encoding ──────────────────────────────────────────────────────

    def _encode_audio(self, audio_path: str) -> str:
        """Read raw audio and return a Base64 data URL string."""
        audio_bytes = Path(audio_path).read_bytes()
        b64_string = base64.b64encode(audio_bytes).decode("utf-8")
        print(f"[API]   Encoded: {len(b64_string) / 1024 / 1024:.1f} MB Base64")
        ext = Path(audio_path).suffix.lower()
        mime_type = "audio/wav" if ext in (".wav",) else "audio/mpeg"
        return f"data:{mime_type};base64,{b64_string}"

    # ── HTTP Request ─────────────────────────────────────────────────────────

    def _post_asr(self, data_url: str) -> dict[str, Any] | None:
        """POST Base64-encoded audio to MiMo chat completions endpoint."""
        body_obj: dict[str, Any] = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": [{
                    "type": "input_audio",
                    "input_audio": {"data": data_url},
                }],
            }],
            "asr_options": {"language": self.language},
        }
        body_bytes = json.dumps(body_obj, ensure_ascii=False).encode("utf-8")

        last_error: str | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self._do_post(body_bytes)
            except error.HTTPError as http_err:
                error_body = ""
                try:
                    error_body = http_err.read().decode("utf-8", errors="replace")[:500]
                except Exception:
                    pass

                # Content moderation rejection — skip this chunk
                if "high risk" in error_body.lower() or "rejected" in error_body.lower():
                    print(f"[API]   Chunk rejected (content filter). Skipping.")
                    return None

                last_error = f"HTTP {http_err.code}: {http_err.reason}"
                print(f"[API]   Attempt {attempt}/{MAX_RETRIES} failed: {last_error}")
                if error_body:
                    print(f"[API]   Response: {error_body}")
                if http_err.code in (401, 403):
                    raise RuntimeError(
                        f"API auth failed. Check api.key in config.txt"
                    ) from http_err
                if http_err.code == 413:
                    print("[API]   Chunk too large. Skipping.")
                    return None
            except (error.URLError, OSError) as e:
                last_error = str(e)
                print(f"[API]   Attempt {attempt}/{MAX_RETRIES} failed: {last_error}")

            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                time.sleep(wait)

        raise RuntimeError(f"API request failed after {MAX_RETRIES} attempts")

    def _do_post(self, body_bytes: bytes) -> dict[str, Any]:
        """Execute a single JSON POST request."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
            "User-Agent": "asr-skill/0.2.0",
            "Content-Length": str(len(body_bytes)),
        }
        headers.update(self.extra_headers)

        req = request.Request(self.endpoint, data=body_bytes, headers=headers, method="POST")
        with request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ── Response Normalization ──────────────────────────────────────────────

    def _normalize_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Convert MiMo chat completions response to internal result format.

        Returns None if the response indicates content was rejected by the
        safety filter (e.g. "high risk" content).
        """
        text = ""
        choices = raw.get("choices", [])
        if choices:
            text = choices[0].get("message", {}).get("content", "")

        # Content moderation rejection — chunk was blocked
        if "high risk" in text.lower() or "rejected" in text.lower():
            print(f"[API]   Content rejected by safety filter, skipping chunk.")
            return None

        if not text:
            return None

        return {
            "text": text,
            "sentence_info": [
                {"sentence": text, "start": 0, "end": 0}
            ],
            "_api_id": raw.get("id", ""),
            "_api_model": raw.get("model", self.model),
        }

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _has_ffmpeg() -> bool:
        """Check if ffmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        try:
            import imageio_ffmpeg
            return bool(imageio_ffmpeg.get_ffmpeg_exe())
        except ImportError:
            return False

    @staticmethod
    def _get_ffmpeg() -> str:
        """Get ffmpeg executable path."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                return "ffmpeg"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()

    @staticmethod
    def _get_duration(audio_path: str) -> float:
        """Get audio duration in seconds."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            return float(result.stdout.strip())
        except Exception:
            pass
        try:
            import librosa
            return librosa.get_duration(path=audio_path)
        except Exception:
            return 0.0
