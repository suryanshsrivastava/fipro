"""
File discovery and ingestion module for Fipro.

This module handles scanning the input directory for bank statement files,
validating them, and creating CrawledFile metadata objects. It does not load
file contents, only discovers and validates files.
"""

from typing import List
from datetime import datetime
import os
from src.models.account import CrawledFile


def discover_files(config: dict) -> List[CrawledFile]:
    """
    Discover files in the input directory.
    
    Scans the input directory for supported file extensions (xls, xlsx) and
    creates CrawledFile objects with metadata. Does not load file contents.
    
    Args:
        config: Configuration dictionary with paths and supported_extensions
        
    Returns:
        List of CrawledFile objects
        
    Suggested implementation:
    - Get input path from config['paths']['input']
    - Get supported extensions from config['processing']['supported_extensions']
    - Walk directory tree, check file extensions
    - Validate file is readable
    - Create CrawledFile with filepath, extension, size, crawl_date
    - Return list of CrawledFile objects
    
    Functions that could be kept from existing code:
    - analyze_discovered_files() - provides summary statistics
    - get_bank_from_filename() - extracts bank name from filename
    - print_file_summary() - prints discovery summary
    """
    input_path = config.get("paths", {}).get("input")
    if not input_path:
        raise ValueError("Input path not configured under paths.input")

    supported_exts = config.get("processing", {}).get("supported_extensions", [])
    if not supported_exts:
        supported_exts = ["xls", "xlsx"]

    discovered: List[CrawledFile] = []

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
    """
    Validate that a file is readable and not empty.
    
    Args:
        filepath: Path to file to validate
        
    Returns:
        True if file is valid, False otherwise
    """
    if not os.path.isfile(filepath):
        return False
    if not os.access(filepath, os.R_OK):
        return False
    if os.path.getsize(filepath) <= 0:
        return False
    return True


def get_bank_from_filename(filename: str) -> str:
    """
    Extract bank name from filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        Bank name (HDFC, SBI, AXIS, UNKNOWN)
        
    Suggested implementation:
    - Check filename (case-insensitive) for 'hdfc', 'sbi', 'axis'
    - Return matching bank name or 'UNKNOWN'
    """
    name = filename.lower()
    if "hdfc" in name:
        return "HDFC"
    if "sbi" in name:
        return "SBI"
    if "axis" in name:
        return "AXIS"
    return "UNKNOWN"
