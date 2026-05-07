"""
Configuration loader for Fipro.

This module handles loading and validating configuration from config.toml.
Provides a single source of configuration for the entire application.
"""

import tomllib
from pathlib import Path


def load_config(config_path: str = "config/config.toml") -> Dict:
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
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"config.toml not found at {config_path}")
    
    with open(config_path, 'rb') as f:
        config = tomllib.load(f)
    
    validate_config(config)
    return config


def validate_config(config: Dict) -> bool:
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
    required_sections = ['paths']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Required section '{section}' not found in config")
    
    paths = config['paths']
    for key in ['input', 'output']:
        if key not in paths:
            raise ValueError(f"Required key 'paths.{key}' not found in config")
    
    return True
