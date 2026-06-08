"""Discover and validate bank statement files in the input directory."""

import os
from datetime import datetime

from src.models.account import CrawledFile


def discover_files(config: dict) -> list[CrawledFile]:
    """Scan the input path for supported statement files and return CrawledFile metadata."""
    input_path = config.get("paths", {}).get("input")
    if not input_path:
        raise ValueError("Input path not configured under paths.input")

    supported_exts = config.get("processing", {}).get("supported_extensions", [])
    if not supported_exts:
        supported_exts = ["xls", "xlsx"]

    discovered: list[CrawledFile] = []

    for root, _, files in os.walk(input_path):
        for fname in files:
            ext = fname.split(".")[-1].lower()
            if ext not in supported_exts:
                continue

            full_path = os.path.join(root, fname)
            if not validate_file(full_path):
                continue

            size = os.path.getsize(full_path)
            metadata = {"bank": get_bank_from_filename(fname)}
            discovered.append(
                CrawledFile(
                    filepath=full_path,
                    extension=ext,
                    size=size,
                    crawl_date=datetime.utcnow().isoformat(),
                    metadata=metadata,
                )
            )

    return discovered


def validate_file(filepath: str) -> bool:
    """Return True when the path is a non-empty, readable file."""
    if not os.path.isfile(filepath):
        return False
    if not os.access(filepath, os.R_OK):
        return False
    return not os.path.getsize(filepath) <= 0


def get_bank_from_filename(filename: str) -> str:
    """Infer bank label (HDFC, SBI, AXIS, UNKNOWN) from the filename."""
    name = filename.lower()
    if "hdfc" in name:
        return "HDFC"
    if "sbi" in name:
        return "SBI"
    if "axis" in name:
        return "AXIS"
    return "UNKNOWN"
