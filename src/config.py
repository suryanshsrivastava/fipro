"""
Configuration loader for Fipro.

This module handles loading and validating configuration from config.toml.
Provides a single source of configuration for the entire application.
"""

from pathlib import Path
from typing import Dict
import tomllib


def load_config(config_path: str = "../config/config.toml") -> Dict:
    """
    Load configuration from TOML file.
    
    Args:
        config_path: Path to config.toml file
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
        
    Suggested implementation:
    - Check if config_path exists
    - Open file in binary mode
    - Use tomllib.load() to parse TOML
    - Validate required sections exist
    - Return config dictionary
    
    Functions that could be kept from existing code:
    - load_config() - already implemented in utils/utils.py
    """
    config_path = Path(config_path)
    if not config_path.exists():
        print("config.toml not found. Please  create a configuration file.")
        raise FileNotFoundError("config.toml not found")
    
    with open(config_path, 'rb') as f:
        config = tomllib.load(f)
    
    # Validate config
    validate_config(config)
    
    return config


def validate_config(config: Dict) -> bool:
    """
    Validate configuration structure.
    
    Checks that required sections and keys are present.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if valid, False otherwise
        
    Raises:
        ValueError: If validation fails with details
    """
    required_sections = ['paths', 'model', 'data', 'logging']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Required section '{section}' not found in config")
    pass
