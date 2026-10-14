"""
Configuration loader for Fipro.

This module handles loading and validating configuration from config.toml.
Provides a single source of configuration for the entire application.
"""

import tomllib
from pathlib import Path

# Single source of fallback values. Callers may pass partial config dicts (tests, library use),
# so defaults are applied at read time through ``setting`` rather than only at load time.
DEFAULTS: dict[str, object] = {
    "fipro.log_level": "INFO",
    "paths.output": "data/output",
    "paths.processed": "data/processed",
    "paths.failed": "data/failed",
    "paths.dashboard_data": "data/output/dashboard_data.csv",
    "paths.password_hints": "data/password_hints.json",
    "processing.supported_extensions": ["xls", "xlsx"],
    "processing.fail_on_file_error": False,
    "processing.seen_hashes_path": "data/.seen_hashes",
    "export.goodbudget.max_description_length": 50,
    "export.goodbudget.default_envelope": "Unallocated",
    "export.goodbudget.default_status": "cleared",
    "gmail.credentials": "config/gmail_credentials.json",
    "gmail.token": "config/gmail_token.json",
    "gmail.max_messages": 10,
    "gmail.queries": {},
}


def setting(config: dict, dotted_key: str):
    """Read ``section.key`` (or deeper) from ``config``, falling back to DEFAULTS."""
    value: object = config
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            return DEFAULTS[dotted_key]
        value = value[part]
    return value


def load_config(config_path: str = "config/config.toml") -> dict:
    """
    Load configuration from TOML file.

    Args:
        config_path: Path to config.toml file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"config.toml not found at {path}")

    with open(path, "rb") as f:
        config = tomllib.load(f)

    validate_config(config)
    return config


def validate_config(config: dict) -> bool:
    """
    Validate configuration structure.

    Checks that required sections and keys are present.

    Args:
        config: Configuration dictionary

    Returns:
        True if valid

    Raises:
        ValueError: If validation fails with details
    """
    required_sections = ["paths"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Required section '{section}' not found in config")

    paths = config["paths"]
    for key in ["input", "output"]:
        if key not in paths:
            raise ValueError(f"Required key 'paths.{key}' not found in config")

    return True
