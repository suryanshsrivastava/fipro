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
from types import MappingProxyType
from typing import Any

_DEFAULT_LOG_LEVEL = "INFO"


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
        d = cls(input="")
        return cls(
            input=_required_str(config, "paths.input"),
            output=_str(config, "paths.output", d.output),
            processed=_str(config, "paths.processed", d.processed),
            failed=_str(config, "paths.failed", d.failed),
            dashboard_data=_str(config, "paths.dashboard_data", d.dashboard_data),
            password_hints=_str(config, "paths.password_hints", d.password_hints),
            seen_hashes=_str(config, "processing.seen_hashes_path", d.seen_hashes),
        )


@dataclass(frozen=True, slots=True)
class ProcessingSettings:
    supported_extensions: tuple[str, ...] = ("xls", "xlsx")
    fail_on_file_error: bool = False
    # Whether internal transfers stay in exports and reports.
    export_internal_transfers: bool = True

    @classmethod
    def from_config(cls, config: dict) -> ProcessingSettings:
        d = cls()
        include = _lookup(config, "processing.include_internal_transfers")
        if include is not None and not isinstance(include, bool):
            raise ValueError(f"Config key 'processing.include_internal_transfers' must be bool, got {include!r}")
        # An explicit include flag wins over the legacy skip flag.
        export = include if include is not None else not _bool(config, "processing.skip_internal_transfers", False)
        return cls(
            # An empty extension list means "unset".
            supported_extensions=_strings(config, "processing.supported_extensions", d.supported_extensions)
            or d.supported_extensions,
            fail_on_file_error=_bool(config, "processing.fail_on_file_error", d.fail_on_file_error),
            export_internal_transfers=export,
        )


@dataclass(frozen=True, slots=True)
class GoodbudgetSettings:
    max_description_length: int = 50
    default_envelope: str = "Unallocated"
    default_status: str = "cleared"

    @classmethod
    def from_config(cls, config: dict) -> GoodbudgetSettings:
        d = cls()
        return cls(
            max_description_length=_int(config, "export.goodbudget.max_description_length", d.max_description_length),
            default_envelope=_str(config, "export.goodbudget.default_envelope", d.default_envelope),
            default_status=_str(config, "export.goodbudget.default_status", d.default_status),
        )


@dataclass(frozen=True, slots=True)
class ExternalAccountSettings:
    names: tuple[str, ...] = ()
    payment_keywords: tuple[str, ...] = ()

    @classmethod
    def from_config(cls, config: dict) -> ExternalAccountSettings:
        d = cls()
        return cls(
            names=_strings(config, "external_accounts.names", d.names),
            payment_keywords=_strings(config, "external_accounts.payment_keywords", d.payment_keywords),
        )


@dataclass(frozen=True, slots=True)
class GmailSettings:
    credentials: str = "config/gmail_credentials.json"
    token: str = "config/gmail_token.json"
    max_messages: int = 10
    queries: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict) -> GmailSettings:
        d = cls()
        return cls(
            credentials=_str(config, "gmail.credentials", d.credentials),
            token=_str(config, "gmail.token", d.token),
            max_messages=_int(config, "gmail.max_messages", d.max_messages),
            queries=_str_map(config, "gmail.queries"),
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
    log_level: str = _DEFAULT_LOG_LEVEL

    @classmethod
    def from_config(cls, config: dict) -> Settings:
        return cls(
            paths=PathSettings.from_config(config),
            processing=ProcessingSettings.from_config(config),
            goodbudget=GoodbudgetSettings.from_config(config),
            external_accounts=ExternalAccountSettings.from_config(config),
            gmail=GmailSettings.from_config(config),
            log_level=_str(config, "fipro.log_level", _DEFAULT_LOG_LEVEL),
        )


def _lookup(config: dict, dotted_key: str) -> Any:
    """The value at ``dotted_key``, or None when any part of the path is absent."""
    node: Any = config
    for part in dotted_key.split("."):
        node = node.get(part) if isinstance(node, dict) else None
    return node


def _typed(config: dict, key: str, kind: type, default: Any) -> Any:
    value = _lookup(config, key)
    if value is None:
        return default
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise ValueError(f"Config key '{key}' must be {kind.__name__}, got {value!r}")
    return value


def _str(config: dict, key: str, default: str) -> str:
    return str(_typed(config, key, str, default))


def _int(config: dict, key: str, default: int) -> int:
    return int(_typed(config, key, int, default))


def _bool(config: dict, key: str, default: bool) -> bool:
    return bool(_typed(config, key, bool, default))


def _required_str(config: dict, key: str) -> str:
    if _lookup(config, key) is None:
        raise ValueError(f"Required key '{key}' not found in config")
    return _str(config, key, "")


def _strings(config: dict, key: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = _lookup(config, key)
    if value is None:
        return default
    if not isinstance(value, list | tuple) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Config key '{key}' must be a list of strings, got {value!r}")
    return tuple(value)


def _str_map(config: dict, key: str) -> Mapping[str, str]:
    """A read-only copy of a table of strings (never the config's own mutable dict)."""
    value = _lookup(config, key)
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        raise ValueError(f"Config key '{key}' must be a table of strings, got {value!r}")
    return MappingProxyType(dict(value))


def load_settings(config_path: str = "config/config.toml") -> Settings:
    """Load config.toml into Settings; missing required keys and wrong types are ValueErrors."""
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
        tomllib.TOMLDecodeError: If the file is not valid TOML (Settings validates the contents)
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"config.toml not found at {path}")

    with open(path, "rb") as f:
        return tomllib.load(f)
