"""Configuration loader for ASR skill."""

import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "model_dir": "",
    "output_format": "txt",
    "output_dir": ""
}

def load_config() -> dict:
    """Load configuration from config.json or return defaults.
    
    Search order:
    1. Current working directory
    2. Environment variable ASR_CONFIG_PATH
    3. Default config
    """
    config_paths = [
        Path.cwd() / "config.json",
        Path.cwd() / "skills" / "asr" / "config.json",
    ]
    
    if env_path := os.environ.get("ASR_CONFIG_PATH"):
        config_paths.insert(0, Path(env_path))
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                return {**DEFAULT_CONFIG, **config}
            except (json.JSONDecodeError, IOError):
                pass
    
    return DEFAULT_CONFIG.copy()