"""Configuration loader for ASR skill.

Supports two operation modes (mutually exclusive):
    - "local": Run ASR models locally via FunASR (default, offline, private)
    - "api":   Call Xiaomi MiMo ASR API (cloud, no local GPU needed, requires network)

Configuration is read from config.txt files in key=value format.
Each configuration item is documented with inline comments in the example file.

Local mode asr_model values:
    - "auto": Auto-detect best model based on platform and hardware (default)
    - "paraformer": Paraformer-large (best accuracy, requires GPU for good speed)
    - "sensevoice": SenseVoiceSmall (lighter, faster on CPU, no speaker diarization)

API mode config (prefixed with "api.") — Xiaomi MiMo ASR:
    - api.url:         Base URL (default: https://api.xiaomimimo.com/v1)
    - api.key:         API key for the ``api-key`` header (or MIMO_API_KEY env var)
    - api.model:       Model name (default: "mimo-v2.5-asr", only supported model)
    - api.language:    Language hint — "auto", "zh", or "en" (default: "auto")
    - api.max_file_mb: Max raw audio file size in MB (default: 7, API limit ~10 MB Base64)
    - api.timeout:     Request timeout in seconds (default: 300)
    - api.headers:     Extra HTTP headers as JSON key-value pairs (optional)

Config file search order:
    1. Environment variable ASR_CONFIG_PATH
    2. Current working directory (config.txt)
    3. skills/asr/config.txt
    4. Built-in defaults

Note: local and api modes are mutually exclusive — only one can be active.
"""

import json
import os
from pathlib import Path

# ── Default Configuration ───────────────────────────────────────────────────

DEFAULT_CONFIG: dict = {
    # ── 运行模式（必选，二选一）──────────────────────────────
    "mode": "local",

    # ── 本地模式配置（仅 mode=local 时生效）─────────────────
    "model_dir": "",
    "asr_model": "auto",

    # ── 输出配置 ──────────────────────────────────────────
    "output_format": "txt",
    "output_dir": "",

    # ── API 模式配置（仅 mode=api 时生效）──────────────────
    "api": {
        "url": "",
        "key": "",
        "model": "mimo-v2.5-asr",
        "language": "auto",
        "max_file_mb": 7,
        "timeout": 300,
        "headers": {},
    },
}

# Valid mode values (local and api are mutually exclusive)
VALID_MODES = frozenset({"local", "api"})


# ── Properties File Parser ──────────────────────────────────────────────────

def _parse_properties(filepath: Path) -> dict[str, str]:
    """Parse a .properties file into a flat key-value dict.

    Handles:
        - Comments: lines starting with # or ! are ignored
        - Key-value: ``key = value`` format (whitespace trimmed)
        - Line continuation: trailing backslash ``\\`` joins next line
        - Empty lines are skipped
        - Keys are kept as-is (dot-notation preserved for _unflatten_dict)

    Args:
        filepath: Path to the .properties file.

    Returns:
        Flat dict of string keys to string values.

    Raises:
        OSError: If file cannot be read.
    """
    result: dict[str, str] = {}

    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    current_key: str | None = None
    current_value: list[str] = []

    for line in lines:
        stripped = line.strip()

        # ── Handle line continuation ──────────────────────────────────
        if current_key is not None:
            if stripped.endswith("\\"):
                current_value.append(stripped[:-1])
                continue
            else:
                current_value.append(stripped)
                result[current_key] = "".join(current_value).strip()
                current_key = None
                current_value = []
                continue

        # ── Skip empty lines and comments ─────────────────────────────
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            continue

        # ── Parse key = value ─────────────────────────────────────────
        if "=" in stripped:
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip()

            if value.endswith("\\"):
                current_key = key
                current_value = [value[:-1]]
            else:
                result[key] = value
        # Lines without "=" are silently ignored (malformed)

    # Flush any pending continuation
    if current_key is not None:
        result[current_key] = "".join(current_value).strip()

    return result


def _parse_value(value: str):
    """Attempt to parse a string value into its proper Python type.

    Tries, in order:
        1. JSON (handles int, float, bool, list, dict, null)
        2. Fallback: plain string

    Args:
        value: Raw string value from properties file.

    Returns:
        Parsed value — may be int, float, bool, list, dict, None, or str.
    """
    if not value:
        return ""  # Empty string stays empty (not None)

    # Try JSON first — handles numbers, booleans, objects, arrays
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: return as plain string
    return value


def _unflatten_dict(flat: dict[str, str]) -> dict:
    """Convert flat dot-notation keys to nested dict structure.

    Example:
        {"api.url": "x", "api.key": "y", "mode": "local"}
        → {"api": {"url": "x", "key": "y"}, "mode": "local"}

    Leaf values are type-parsed via _parse_value.

    Args:
        flat: Flat dict from _parse_properties.

    Returns:
        Nested dict with proper types.
    """
    result: dict = {}
    for key, value in flat.items():
        if "." in key:
            parts = key.split(".")
            d = result
            for part in parts[:-1]:
                if part not in d:
                    d[part] = {}
                elif not isinstance(d[part], dict):
                    # Conflict: existing non-dict value at this path
                    d[part] = {}
                d = d[part]
            # Set leaf value with type parsing
            d[parts[-1]] = _parse_value(value)
        else:
            result[key] = _parse_value(value)
    return result


# ── Deep Merge ──────────────────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge two dicts. Override values take precedence.

    Nested dicts are merged recursively; non-dict values are replaced.

    Args:
        base: Base/default configuration dict.
        override: User-provided override dict.

    Returns:
        Merged configuration dict.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ── Public API ──────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load configuration from config.txt or return defaults.

    Search order (first found wins):
        1. ``ASR_CONFIG_PATH`` environment variable
        2. ``./config.txt`` (current working directory)
        3. Built-in :data:`DEFAULT_CONFIG`

    After merging, environment variables ``MIMO_API_KEY`` and ``MIMO_API_URL``
    override their respective config values (highest priority for secrets).

    Returns:
        Merged configuration dict with structure matching DEFAULT_CONFIG.

    Raises:
        ValueError: If ``mode`` is not ``"local"`` or ``"api"``.

    Example:
        >>> config = load_config()
        >>> print(config["mode"])
        'local'
        >>> print(config["api"]["chunk_size_mb"])
        100
    """
    # Build search path list
    config_paths = [
        Path.cwd() / "config.txt",
    ]

    if env_path := os.environ.get("ASR_CONFIG_PATH"):
        config_paths.insert(0, Path(env_path))

    # Load first found user config
    user_config: dict = {}
    for config_path in config_paths:
        if config_path.exists():
            try:
                flat = _parse_properties(config_path)
                user_config = _unflatten_dict(flat)
                break  # Use first found config
            except (OSError, ValueError):
                pass

    # Deep-merge: user overrides defaults (nested api.* preserved)
    merged = _deep_merge(DEFAULT_CONFIG, user_config)

    # ── Validate: mode must be local or api (mutually exclusive) ─────
    mode = merged.get("mode", "local")
    if mode not in VALID_MODES:
        raise ValueError(
            f"Invalid mode '{mode}' in configuration. "
            "Mode must be 'local' or 'api' (只能二选一)."
        )

    # ── Environment variable overrides (highest priority) ───────────
    # MiMo API key: MIMO_API_KEY (primary) or ASR_API_KEY (fallback)
    if env_key := os.environ.get("MIMO_API_KEY") or os.environ.get("ASR_API_KEY"):
        merged["api"]["key"] = env_key

    # Base URL override (optional)
    if env_url := os.environ.get("MIMO_API_URL") or os.environ.get("ASR_API_URL"):
        merged["api"]["url"] = env_url

    return merged
