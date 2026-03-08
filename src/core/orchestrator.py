"""
Main processing orchestrator for Fipro.

This module coordinates the entire processing pipeline from file discovery through
export. It manages file lifecycle, routes files to appropriate parsers, and
orchestrates the transformation, deduplication, and export stages.
"""

from typing import List
from src.models.result import ProcessingResult
from src.models.transactions import Transaction


def process_pipeline(config: dict) -> List[ProcessingResult]:
    """
    Execute the complete processing pipeline.
    
    Pipeline stages:
    1. INGESTION: Discover files in input directory
    2. EXTRACTION: Route files to bank parsers
    3. TRANSFORMATION: Clean and standardize data
    4. CONSOLIDATION: Merge, deduplicate, detect transfers
    5. EXPORT: Generate Goodbudget CSV and reports
    
    Args:
        config: Configuration dictionary from config.toml
        
    Returns:
        List of ProcessingResult objects, one per processed file
        
    Suggested implementation:
    - Call ingestion.discover_files() to get CrawledFile objects
    - For each file, route to appropriate parser based on filename
    - Transform raw transactions using transformer.clean_transactions()
    - Deduplicate using deduplicator.deduplicate()
    - Detect transfers using transfer_detector.detect_transfers()
    - Export using exporters.export_to_goodbudget()
    - Move files to processed/ or failed/ directories
    - Return ProcessingResult for each file
    """
    pass


def route_file_to_parser(filename: str, parsers: List) -> object:
    """
    Route a file to the appropriate bank parser.
    
    Args:
        filename: Name of the file to route
        parsers: List of available BankParser instances
        
    Returns:
        BankParser instance that can handle the file
        
    Raises:
        ValueError: If no parser can handle the file
        
    Suggested implementation:
    - Try each parser's can_parse() method
    - Return first parser that returns True
    """
    pass


def move_file_to_processed(source_path: str, dest_dir: str) -> str:
    """
    Move successfully processed file to processed directory.
    
    Args:
        source_path: Path to source file
        dest_dir: Destination directory (processed/)
        
    Returns:
        New file path in processed directory
    """
    pass


def move_file_to_failed(source_path: str, dest_dir: str, error: str) -> str:
    """
    Move failed file to failed directory with error log.
    
    Args:
        source_path: Path to source file
        dest_dir: Destination directory (failed/)
        error: Error message to log
        
    Returns:
        New file path in failed directory
    """
    pass

