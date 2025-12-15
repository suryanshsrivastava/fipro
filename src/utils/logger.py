"""
Logging configuration for Fipro.

This module sets up Python logging with console and rotating file handlers.
Follows the logging configuration specified in the PRD.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Configure logging for Fipro.
    
    Sets up:
    - Console handler with INFO level
    - Rotating file handler (5MB max, 3 backups) with DEBUG level
    - Standard format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file (default: logs/fipro.log)
        
    Suggested implementation:
    - Create logs directory if it doesn't exist
    - Configure root logger
    - Add console handler
    - Add RotatingFileHandler if log_file provided
    - Set format and levels
    """
    # Resolve log file path and ensure directory exists
    if log_file is None:
        log_file_path = Path("logs") / "fipro.log"
    else:
        log_file_path = Path(log_file)

    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()

    # Avoid reconfiguring logging if handlers are already set up
    if root_logger.handlers:
        return

    # Base log level for the application
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Console handler for high-level progress
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Rotating file handler for more detailed logs
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

