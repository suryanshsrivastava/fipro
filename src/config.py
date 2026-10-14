"""
Configuration loader for Fipro.

This module handles loading and validating configuration from config.toml.
Provides a single source of configuration for the entire application.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Dotted config key for each Settings field.
_KEYS = {
    "log_level": "fipro.log_level",
    "output": "paths.output",
    "processed": "paths.processed",
    "failed": "paths.failed",
    "dashboard_data": "paths.dashboard_data",
    "password_hints": "paths.password_hints",
    "supported_extensions": "processing.supported_extensions",
    "fail_on_file_error": "processing.fail_on_file_error",
    "seen_hashes_path": "processing.seen_hashes_path",
    "max_description_length": "export.goodbudget.max_description_length",
    "default_envelope": "export.goodbudget.default_envelope",
    "default_status": "export.goodbudget.default_status",
    "gmail_credentials": "gmail.credentials",
    "gmail_token": "gmail.token",
    "gmail_max_messages": "gmail.max_messages",
    "gmail_queries": "gmail.queries",
}


@dataclass(frozen=True, slots=True)
class Settings:
    """Typed, immutable view of the optional config values; field defaults are the fallbacks.

    Built per read from the config dict because callers may pass partial dicts (tests, library use).
    """

    log_level: str = "INFO"
    output: str = "data/output"
    processed: str = "data/processed"
    failed: str = "data/failed"
    dashboard_data: str = "data/output/dashboard_data.csv"
    password_hints: str = "data/password_hints.json"
    supported_extensions: tuple[str, ...] = ("xls", "xlsx")
    fail_on_file_error: bool = False
    seen_hashes_path: str = "data/.seen_hashes"
    max_description_length: int = 50
    default_envelope: str = "Unallocated"
    default_status: str = "cleared"
    gmail_credentials: str = "config/gmail_credentials.json"
    gmail_token: str = "config/gmail_token.json"
    gmail_max_messages: int = 10
    gmail_queries: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict) -> Settings:
        defaults = cls()
        values: dict[str, Any] = {}
        for name, dotted_key in _KEYS.items():
            node: Any = config
            for part in dotted_key.split("."):
                node = node.get(part) if isinstance(node, dict) else None
            values[name] = getattr(defaults, name) if node is None else node
        # An empty extension list means "unset", matching how discovery has always behaved.
        values["supported_extensions"] = tuple(values["supported_extensions"]) or defaults.supported_extensions
        return cls(**values)


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
