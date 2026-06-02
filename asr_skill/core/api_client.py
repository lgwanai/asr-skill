"""Xiaomi MiMo ASR API client (MiMo-V2.5-ASR).

This module provides an API client for cloud-based ASR transcription via
the Xiaomi MiMo platform. The MiMo ASR API uses the chat completions
endpoint with a special ``input_audio`` content type — audio is Base64-encoded
and sent as a data URL in the request body.

API Reference:
    https://platform.xiaomimimo.com/docs/zh-CN/usage-guide/Speech-Recognition

Key constraints:
    - Base64-encoded audio must be ≤ 10 MB
    - Supported formats: WAV and MP3
    - Only model: ``mimo-v2.5-asr``
    - Language options: ``auto``, ``zh``, ``en``

Configuration (from config.txt "api" section):
    api.url:           Base URL (default: https://api.xiaomimimo.com/v1)
    api.key:           API key for the ``api-key`` header (or MIMO_API_KEY env var)
    api.model:         Model name (default: "mimo-v2.5-asr")
    api.language:      Language hint — "auto", "zh", or "en" (default: "auto")
    api.timeout:       Request timeout in seconds (default: 300)
    api.max_file_mb:   Max raw audio file size in MB before Base64 (default: 7)
    api.headers:        Extra HTTP headers as JSON key-value pairs (optional)
"""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Callable
from urllib import request, error

# ── Constants ────────────────────────────────────────────────────────────────

# HTTP retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds; exponential: base ** attempt

# Base64 encoding expands data by ~4/3 (33%). 10 MB Base64 → ~7.5 MB raw.
BASE64_EXPANSION_RATIO = 4.0 / 3.0
API_MAX_BASE64_BYTES = 10 * 1024 * 1024  # 10 MB

# MiMo ASR API endpoint (OpenAI-compatible chat completions)
DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"


# ── API Client ───────────────────────────────────────────────────────────────

class ASRAPIClient:
    """Client for Xiaomi MiMo ASR transcription via chat completions API.

    Uses the ``/v1/chat/completions`` endpoint with ``input_audio`` content
    type. Audio is Base64-encoded and wrapped as a data URL.

    Args:
        config: The full application config dict (merged with defaults).
                Must contain a non-empty ``api.key`` or ``MIMO_API_KEY`` env var.

    Raises:
        ValueError: If api.key is empty/missing, or if the audio file is too large.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        api_cfg = config.get("api", {})

        # ── API key ──────────────────────────────────────────────────────
        self.api_key: str = api_cfg.get("key", "")
        if not self.api_key:
            raise ValueError(
                "API mode requires 'api.key' in config.txt or MIMO_API_KEY env var.\n"
                "Example: api.key = your-xiaomi-mimo-api-key\n"
                "Get your key at: https://platform.xiaomimimo.com/profile"
            )

        # ── Endpoint ─────────────────────────────────────────────────────
        base_url: str = api_cfg.get("url", "").strip()
        if not base_url:
            base_url = DEFAULT_BASE_URL
        self.endpoint: str = f"{base_url.rstrip('/')}/chat/completions"

        # ── Model ────────────────────────────────────────────────────────
        self.model: str = api_cfg.get("model", "mimo-v2.5-asr")

        # ── Language ─────────────────────────────────────────────────────
        self.language: str = api_cfg.get("language", "auto")
        if self.language not in ("auto", "zh", "en"):
            raise ValueError(
                f"Invalid api.language '{self.language}'. "
                "Expected 'auto', 'zh', or 'en'."
            )

        # ── Timeout ──────────────────────────────────────────────────────
        self.timeout: int = api_cfg.get("timeout", 300)

        # ── Max file size (raw, before Base64 encoding) ─────────────────
        max_file_mb: int = api_cfg.get("max_file_mb", 7)
        self.max_file_bytes: int = max_file_mb * 1024 * 1024

        # ── Extra headers ────────────────────────────────────────────────
        self.extra_headers: dict[str, str] = dict(api_cfg.get("headers", {}))

    # ── Public API ──────────────────────────────────────────────────────────

    def transcribe(
        self,
        audio_path: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any] | None:
        """Transcribe an audio file via the MiMo ASR API.

        Args:
            audio_path: Path to preprocessed 16kHz mono WAV file.
            progress_callback: Optional callback(current_step, total_steps)
                for progress reporting (used for UX, not chunking).

        Returns:
            Normalized result dict with ``text`` and ``sentence_info`` keys,
            or None if transcription produced no results.

        Raises:
            ValueError: If the file exceeds the size limit.
            RuntimeError: If the API returns an error or the request fails.
        """
        file_size = os.path.getsize(audio_path)
        file_size_mb = file_size / 1024 / 1024

        # ── Size validation ──────────────────────────────────────────────
        # Estimate Base64 size: raw * 4/3 + data URL overhead (~50 bytes)
        estimated_b64_size = int(file_size * BASE64_EXPANSION_RATIO) + 100
        if estimated_b64_size > API_MAX_BASE64_BYTES:
            raise ValueError(
                f"Audio file too large for MiMo API: {file_size_mb:.1f} MB raw "
                f"(~{estimated_b64_size / 1024 / 1024:.1f} MB Base64).\n"
                f"MiMo API limit: {API_MAX_BASE64_BYTES / 1024 / 1024:.0f} MB Base64 "
                f"(~{self.max_file_bytes / 1024 / 1024:.0f} MB raw).\n"
                "For longer audio, use local mode: set 'mode = local' in config.txt"
            )

        if progress_callback:
            progress_callback(0, 1)

        # ── Read, encode, and send ───────────────────────────────────────
        print(f"[API] Reading audio file ({file_size_mb:.1f} MB)...")
        audio_bytes = Path(audio_path).read_bytes()

        print(f"[API] Base64 encoding...")
        b64_string = base64.b64encode(audio_bytes).decode("utf-8")
        b64_size_mb = len(b64_string) / 1024 / 1024
        print(f"[API] Encoded size: {b64_size_mb:.1f} MB")

        # Determine MIME type from file extension
        ext = Path(audio_path).suffix.lower()
        mime_type = "audio/wav" if ext in (".wav",) else "audio/mpeg"
        data_url = f"data:{mime_type};base64,{b64_string}"

        print(f"[API] Sending to MiMo ASR (model: {self.model}, "
              f"language: {self.language})...")

        if progress_callback:
            progress_callback(1, 1)

        raw = self._post_asr(data_url)
        if raw is None:
            return None

        result = self._normalize_response(raw)
        return result

    # ── HTTP Request ─────────────────────────────────────────────────────────

    def _post_asr(self, data_url: str) -> dict[str, Any] | None:
        """POST the Base64-encoded audio to the MiMo chat completions endpoint.

        Builds the OpenAI-compatible request body with ``input_audio`` type.

        Returns:
            Parsed JSON response dict, or None if the request failed.
        """
        body_obj: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": data_url,
                            },
                        }
                    ],
                }
            ],
            "asr_options": {
                "language": self.language,
            },
        }
        body_bytes = json.dumps(body_obj, ensure_ascii=False).encode("utf-8")

        last_error: str | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self._do_post(body_bytes)
            except error.HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="replace")[:500]
                except Exception:
                    pass
                print(f"[API]   Attempt {attempt}/{MAX_RETRIES} failed: {last_error}")
                if body:
                    print(f"[API]   Response: {body}")
                if e.code in (401, 403):
                    raise RuntimeError(
                        f"API authentication failed: {last_error}\n"
                        "Check your api.key in config.txt or MIMO_API_KEY env var.\n"
                        f"{body}"
                    ) from e
                if e.code == 413:
                    raise RuntimeError(
                        f"Audio file too large for MiMo API (HTTP 413).\n"
                        "For longer audio, use local mode: mode = local"
                    ) from e
            except (error.URLError, OSError) as e:
                last_error = str(e)
                print(f"[API]   Attempt {attempt}/{MAX_RETRIES} failed: {last_error}")

            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                print(f"[API]   Retrying in {wait}s...")
                time.sleep(wait)

        raise RuntimeError(
            f"API request failed after {MAX_RETRIES} attempts: {last_error}"
        )

    def _do_post(self, body_bytes: bytes) -> dict[str, Any]:
        """Execute a single JSON POST request to the chat completions endpoint."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
            "User-Agent": "asr-skill/0.2.0",
            "Content-Length": str(len(body_bytes)),
        }

        # Extra headers from config (merged after defaults so they can override)
        headers.update(self.extra_headers)

        req = request.Request(
            self.endpoint,
            data=body_bytes,
            headers=headers,
            method="POST",
        )

        with request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8"))

    # ── Response Normalization ──────────────────────────────────────────────

    def _normalize_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Convert MiMo chat completions response to internal result format.

        The MiMo API returns an OpenAI-compatible chat completions response:

        .. code-block:: json

            {
                "id": "chatcmpl-xxx",
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "transcribed text here"
                    }
                }]
            }

        This is normalized to the internal format used by the formatters:

        .. code-block:: json

            {
                "text": "transcribed text here",
                "sentence_info": [
                    {"sentence": "transcribed text here", "start": 0, "end": 0}
                ]
            }
        """
        # Extract text from chat completions response
        text = ""
        choices = raw.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            text = message.get("content", "")

        if not text:
            print("[API] Warning: No text content in API response")

        # Build normalized result
        result: dict[str, Any] = {
            "text": text,
            "sentence_info": [
                {"sentence": text, "start": 0, "end": 0}
            ],
        }

        # Preserve raw response metadata for debugging
        result["_api_id"] = raw.get("id", "")
        result["_api_model"] = raw.get("model", self.model)

        return result
