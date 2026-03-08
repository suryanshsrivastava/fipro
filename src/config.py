"""Configuration loader for Fipro."""

from pathlib import Path
from typing import Dict
import tomllib


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.toml"


def load_config(config_path: str | None = None) -> Dict:
    """Load and validate the project TOML config."""
    path = DEFAULT_CONFIG_PATH if config_path is None else Path(config_path)
    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.exists():
        raise FileNotFoundError(f"config.toml not found at {path}")

    with path.open("rb") as handle:
        config = tomllib.load(handle)

    validate_config(config)
    return config


def validate_config(config: Dict) -> bool:
    """Validate the runtime config structure."""
    required_sections = ["fipro", "paths", "processing", "banks"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Required section '{section}' not found in config")

    required_paths = ["input", "output", "processed", "failed"]
    for key in required_paths:
        if key not in config["paths"]:
            raise ValueError(f"Required path 'paths.{key}' not found in config")

    if "supported_extensions" not in config["processing"]:
        raise ValueError("Required key 'processing.supported_extensions' not found")

    for bank_key in ["hdfc", "sbi", "axis"]:
        if bank_key not in config["banks"]:
            raise ValueError(f"Required bank config 'banks.{bank_key}' not found")

    return True
