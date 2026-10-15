"""
Configuration loader for Fipro.

This module handles loading and validating configuration from config.toml.
Provides a single source of configuration for the entire application.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import MISSING, dataclass, field, fields
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Settings:
    """Typed, immutable view of the optional config values; field defaults are the fallbacks.

    Each field's ``metadata["key"]`` is its dotted path in config.toml. Built per read from the config
    dict because callers may pass partial dicts (tests, library use).
    """

    input: str | None = field(default=None, metadata={"key": "paths.input", "type": str})
    log_level: str = field(default="INFO", metadata={"key": "fipro.log_level"})
    output: str = field(default="data/output", metadata={"key": "paths.output"})
    processed: str = field(default="data/processed", metadata={"key": "paths.processed"})
    failed: str = field(default="data/failed", metadata={"key": "paths.failed"})
    dashboard_data: str = field(default="data/output/dashboard_data.csv", metadata={"key": "paths.dashboard_data"})
    password_hints: str = field(default="data/password_hints.json", metadata={"key": "paths.password_hints"})
    supported_extensions: tuple[str, ...] = field(
        default=("xls", "xlsx"), metadata={"key": "processing.supported_extensions"}
    )
    include_internal_transfers: bool | None = field(
        default=None, metadata={"key": "processing.include_internal_transfers", "type": bool}
    )
    skip_internal_transfers: bool = field(default=False, metadata={"key": "processing.skip_internal_transfers"})
    fail_on_file_error: bool = field(default=False, metadata={"key": "processing.fail_on_file_error"})
    seen_hashes_path: str = field(default="data/.seen_hashes", metadata={"key": "processing.seen_hashes_path"})
    max_description_length: int = field(default=50, metadata={"key": "export.goodbudget.max_description_length"})
    default_envelope: str = field(default="Unallocated", metadata={"key": "export.goodbudget.default_envelope"})
    default_status: str = field(default="cleared", metadata={"key": "export.goodbudget.default_status"})
    external_account_names: tuple[str, ...] = field(default=(), metadata={"key": "external_accounts.names"})
    external_payment_keywords: tuple[str, ...] = field(
        default=(), metadata={"key": "external_accounts.payment_keywords"}
    )
    gmail_credentials: str = field(default="config/gmail_credentials.json", metadata={"key": "gmail.credentials"})
    gmail_token: str = field(default="config/gmail_token.json", metadata={"key": "gmail.token"})
    gmail_max_messages: int = field(default=10, metadata={"key": "gmail.max_messages"})
    gmail_queries: Mapping[str, str] = field(default_factory=dict, metadata={"key": "gmail.queries"})

    @property
    def export_internal_transfers(self) -> bool:
        """Whether internal transfers stay in exports and reports (explicit flag wins over skip)."""
        if self.include_internal_transfers is not None:
            return self.include_internal_transfers
        return not self.skip_internal_transfers

    @classmethod
    def from_config(cls, config: dict) -> Settings:
        """Read each field from its dotted key; a present value of the wrong type is a ValueError."""
        values: dict[str, Any] = {}
        for f in fields(cls):
            node: Any = config
            for part in f.metadata["key"].split("."):
                node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                continue
            expected: type | tuple[type, ...] = f.metadata.get("type") or (
                dict if f.default is MISSING else type(f.default)
            )
            if expected is tuple:
                expected = (list, tuple)
            if not isinstance(node, expected) or (isinstance(node, bool) and expected is int):
                raise ValueError(f"Config key '{f.metadata['key']}' must be {_describe(expected)}, got {node!r}")
            if f.name == "supported_extensions" and not node:
                continue  # an empty extension list means "unset", as discovery has always treated it
            values[f.name] = tuple(node) if isinstance(node, list) else node
        return cls(**values)


def _describe(expected: type | tuple[type, ...]) -> str:
    return " or ".join(t.__name__ for t in (expected if isinstance(expected, tuple) else (expected,)))


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
