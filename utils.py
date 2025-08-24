import tomllib
from pathlib import Path

def load_config() -> dict:
    """Load configuration from config.toml file"""
    config_path = Path('config.toml')
    if not config_path.exists():
        print("config.toml not found. Please  create a configuration file.")
        raise FileNotFoundError("config.toml not found")
    
    with open(config_path, 'rb') as f:
        config = tomllib.load(f)
    
    return config