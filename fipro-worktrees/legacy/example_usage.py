#!/usr/bin/env python3
"""
Example usage of the new file discovery and dataframe loading functions.
This script demonstrates how to use the refactored ingest_transactions.py
"""

from ingest_transactions import (
    load_config, 
    discover_files, 
    load_files_to_dataframes,
    analyze_discovered_files,
    print_file_summary,
    analyze_dataframes,
    get_dataframe_by_bank
)

def main():
    """Demonstrate the new file discovery and loading functionality"""
    
    # Load configuration
    try:
        config = load_config()
        print("Configuration loaded successfully")
        print(f"Input directory: {config['paths']['input']}")
    except FileNotFoundError:
        print("Error: config.toml not found")
        return
    
    # Step 1: Discover files (no I/O operations)
    print("\n=== Step 1: Discovering Files ===")
    discovered_files = discover_files(config)
    
    if not discovered_files:
        print("No files discovered. Check the input directory path.")
        return
    
    # Step 2: Print file summary
    print_file_summary(discovered_files)
    
    # Step 3: Load files into dataframes (only when needed)
    print("\n=== Step 2: Loading Files into Dataframes ===")
    dataframes = load_files_to_dataframes(discovered_files)
    
    if not dataframes:
        print("No dataframes loaded. Check file formats and permissions.")
        return
    
    # Step 4: Analyze loaded dataframes
    print("\n=== Step 3: Analyzing Dataframes ===")
    analyze_dataframes(dataframes)
    
    # Step 5: Example: Work with specific bank data
    print("\n=== Step 4: Working with Specific Bank Data ===")
    
    # Get HDFC dataframes
    hdfc_dataframes = get_dataframe_by_bank(dataframes, 'HDFC')
    if hdfc_dataframes:
        print(f"\nHDFC dataframes found: {len(hdfc_dataframes)}")
        for key, df in hdfc_dataframes.items():
            print(f"\nFile: {key}")
            print(f"  Rows: {len(df)}")
            print(f"  Columns: {list(df.columns)}")
            if len(df) > 0:
                print(f"  Sample data:")
                print(df.head(2).to_string())
    
    # Get SBI dataframes
    sbi_dataframes = get_dataframe_by_bank(dataframes, 'SBI')
    if sbi_dataframes:
        print(f"\nSBI dataframes found: {len(sbi_dataframes)}")
        for key, df in sbi_dataframes.items():
            print(f"\nFile: {key}")
            print(f"  Rows: {len(df)}")
            print(f"  Columns: {list(df.columns)}")
    
    print("\n=== Example Complete ===")
    print("You can now work with the loaded dataframes for further processing.")

if __name__ == "__main__":
    main()
