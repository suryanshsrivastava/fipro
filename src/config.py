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


@dataclass(frozen=True, slots=True)
class PathSettings:
    input: str
    output: str = "data/output"
    processed: str = "data/processed"
    failed: str = "data/failed"
    dashboard_data: str = "data/output/dashboard_data.csv"
    password_hints: str = "data/password_hints.json"
    seen_hashes: str = "data/.seen_hashes"

    @classmethod
    def from_config(cls, config: dict) -> PathSettings:
        return cls(
            input=_read(config, "paths.input", str, required=True),
            **_present(
                config,
                output=("paths.output", str),
                processed=("paths.processed", str),
                failed=("paths.failed", str),
                dashboard_data=("paths.dashboard_data", str),
                password_hints=("paths.password_hints", str),
                seen_hashes=("processing.seen_hashes_path", str),
            ),
        )


@dataclass(frozen=True, slots=True)
class ProcessingSettings:
    supported_extensions: tuple[str, ...] = ("xls", "xlsx")
    fail_on_file_error: bool = False
    # Whether internal transfers stay in exports and reports.
    export_internal_transfers: bool = True

    @classmethod
    def from_config(cls, config: dict) -> ProcessingSettings:
        values = _present(
            config,
            supported_extensions=("processing.supported_extensions", "strings"),
            fail_on_file_error=("processing.fail_on_file_error", bool),
        )
        if not values.get("supported_extensions"):
            values.pop("supported_extensions", None)  # an empty list means "unset"
        flags = _present(
            config,
            include=("processing.include_internal_transfers", bool),
            skip=("processing.skip_internal_transfers", bool),
        )
        # An explicit include flag wins over the legacy skip flag.
        export = flags["include"] if "include" in flags else not flags.get("skip", False)
        return cls(export_internal_transfers=export, **values)


@dataclass(frozen=True, slots=True)
class GoodbudgetSettings:
    max_description_length: int = 50
    default_envelope: str = "Unallocated"
    default_status: str = "cleared"

    @classmethod
    def from_config(cls, config: dict) -> GoodbudgetSettings:
        return cls(
            **_present(
                config,
                max_description_length=("export.goodbudget.max_description_length", int),
                default_envelope=("export.goodbudget.default_envelope", str),
                default_status=("export.goodbudget.default_status", str),
            )
        )


@dataclass(frozen=True, slots=True)
class ExternalAccountSettings:
    names: tuple[str, ...] = ()
    payment_keywords: tuple[str, ...] = ()

    @classmethod
    def from_config(cls, config: dict) -> ExternalAccountSettings:
        return cls(
            **_present(
                config,
                names=("external_accounts.names", "strings"),
                payment_keywords=("external_accounts.payment_keywords", "strings"),
            )
        )


@dataclass(frozen=True, slots=True)
class GmailSettings:
    credentials: str = "config/gmail_credentials.json"
    token: str = "config/gmail_token.json"
    max_messages: int = 10
    queries: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict) -> GmailSettings:
        return cls(
            **_present(
                config,
                credentials=("gmail.credentials", str),
                token=("gmail.token", str),
                max_messages=("gmail.max_messages", int),
                queries=("gmail.queries", dict),
            )
        )


@dataclass(frozen=True, slots=True)
class Settings:
    """Typed, immutable settings, grouped by who uses them. Built once from config.toml in ``main``.

    Absent optional keys fall back to each field's default; a present value of the wrong type is a
    ValueError, and ``paths.input`` is required.
    """

    paths: PathSettings
    processing: ProcessingSettings = field(default_factory=ProcessingSettings)
    goodbudget: GoodbudgetSettings = field(default_factory=GoodbudgetSettings)
    external_accounts: ExternalAccountSettings = field(default_factory=ExternalAccountSettings)
    gmail: GmailSettings = field(default_factory=GmailSettings)
    log_level: str = "INFO"

    @classmethod
    def from_config(cls, config: dict) -> Settings:
        return cls(
            paths=PathSettings.from_config(config),
            processing=ProcessingSettings.from_config(config),
            goodbudget=GoodbudgetSettings.from_config(config),
            external_accounts=ExternalAccountSettings.from_config(config),
            gmail=GmailSettings.from_config(config),
            **_present(config, log_level=("fipro.log_level", str)),
        )


_MISSING = object()


def _read(config: dict, dotted_key: str, kind: type | str, *, required: bool = False) -> Any:
    """The value at ``dotted_key`` checked against ``kind`` (a type, or "strings" for a list of str)."""
    node: Any = config
    for part in dotted_key.split("."):
        node = node.get(part, _MISSING) if isinstance(node, dict) else _MISSING
    if node is _MISSING or node is None:
        if required:
            raise ValueError(f"Required key '{dotted_key}' not found in config")
        return _MISSING
    if kind == "strings":
        if not isinstance(node, list | tuple) or not all(isinstance(item, str) for item in node):
            raise ValueError(f"Config key '{dotted_key}' must be a list of strings, got {node!r}")
        return tuple(node)
    assert isinstance(kind, type)
    if not isinstance(node, kind) or (kind is int and isinstance(node, bool)):
        raise ValueError(f"Config key '{dotted_key}' must be {kind.__name__}, got {node!r}")
    return node


def _present(config: dict, **specs: tuple[str, type | str]) -> dict[str, Any]:
    """Only the keys that are set in ``config``, so omitted ones keep their dataclass defaults."""
    values = {name: _read(config, key, kind) for name, (key, kind) in specs.items()}
    return {name: value for name, value in values.items() if value is not _MISSING}


def load_settings(config_path: str = "config/config.toml") -> Settings:
    """Load and validate config.toml into Settings."""
    return Settings.from_config(load_config(config_path))


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
