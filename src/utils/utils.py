from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from src.models.account import CrawledFile

# def load_config() -> dict:
#     """Load configuration from config.toml file"""
#     config_path = Path('config.toml')
#     if not config_path.exists():
#         print("config.toml not found. Please  create a configuration file.")
#         raise FileNotFoundError("config.toml not found")
    
#     with open(config_path, 'rb') as f:
#         config = tomllib.load(f)
    
#     return config


def consolidate_files_by_bank(files: List["CrawledFile"]) -> dict:
    """Consolidates a list of crawled files into a dictionary grouped by bank."""
    bank_files = {'HDFC': [], 'SBI': [], 'AXIS': [], 'UNKNOWN': []}
    
    for file in files:
        filename_upper = file.filename.upper()
        if 'HDFC' in filename_upper:
            bank_files['HDFC'].append(file)
        elif 'SBI' in filename_upper:
            bank_files['SBI'].append(file)
        elif 'AXIS' in filename_upper:
            bank_files['AXIS'].append(file)
        else:
            bank_files['UNKNOWN'].append(file)
            
    return bank_files
