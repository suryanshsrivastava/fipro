import os
import pandas as pd
import tomllib
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime

def load_config() -> dict:
    """Load configuration from config.toml file"""
    config_path = Path('config.toml')
    if not config_path.exists():
        print("config.toml not found. Please create a configuration file.")
        raise FileNotFoundError("config.toml not found")
    
    with open(config_path, 'rb') as f:
        config = tomllib.load(f)
    
    return config

@dataclass
class CrawledFile:
    filename: str
    extension: str      # 'pdf', 'xlsx', 'csv'
    size: int           # in bytes
    crawl_date: str     # ISO format
    page_count: Optional[int] = None         # for PDF
    sheet_names: Optional[List[str]] = None  # for XLSX
    row_count: Optional[int] = None          # for CSV
    metadata: dict = field(default_factory=dict) # for custom info

def crawl_files(data_path: str) -> List[CrawledFile]:
    """Crawls a directory for transaction files and returns a list of CrawledFile objects."""
    crawled_files: List[CrawledFile] = []
    supported_extensions = {'pdf', 'xls', 'xlsx', 'csv'}

    for root, _, files in os.walk(data_path):
        for file in files:
            file_path = os.path.join(root, file)
            extension = file.split('.')[-1].lower()

            if extension not in supported_extensions:
                continue

            try:
                file_info = {
                    'filename': file_path,
                    'extension': extension,
                    'size': os.path.getsize(file_path),
                    'crawl_date': datetime.now().isoformat(),
                }

                if extension == 'pdf':
                    # PDF processing can be added here if needed in the future
                    pass
                elif extension in ['xls', 'xlsx']:
                    try:
                        with pd.ExcelFile(file_path) as xls:
                            file_info['sheet_names'] = xls.sheet_names
                    except Exception as e:
                        print(f"Error reading Excel file {file_path}: {e}")
                        file_info['sheet_names'] = []
                elif extension == 'csv':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_info['row_count'] = sum(1 for _ in f)
                
                crawled_files.append(CrawledFile(**file_info))
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
    
    return crawled_files

def find_header_row(df: pd.DataFrame, expected_headers: set) -> Optional[int]:
    """
    Scans the first 20 rows of a DataFrame to find the header row.
    Returns the index of the header row if found, otherwise None.
    """
    for i in range(min(20, len(df))):
        row_values = set(str(v).strip() for v in df.iloc[i])
        # Consider it a header if at least 3 common columns are present
        if len(expected_headers.intersection(row_values)) >= 3:
            return i
    return None

def process_bank_transactions(bank_name: str, files: List[CrawledFile]) -> Optional[pd.DataFrame]:
    """Processes and consolidates transaction files for a given bank.""" 
    all_transactions = []
    
    # Define a mapping for common transaction column names to a standardized format
    column_mapping = {
        # Standard names
        'Transaction Date': 'Transaction Date',
        'Description': 'Description',
        'Amount': 'Amount',
        'Debit': 'Debit',
        'Credit': 'Credit',
        'Balance': 'Balance',
        
        # Common variations
        'Date': 'Transaction Date',
        'Tran Date': 'Transaction Date',
        'Txn Date': 'Transaction Date',
        'Narration': 'Description',
        'Particulars': 'Description',
        'Withdrawal': 'Debit',
        'Deposit': 'Credit',
        'Value Date': 'Transaction Date'
    }
    expected_headers = set(column_mapping.keys())

    for file_info in files:
        df = None
        try:
            if file_info.extension == 'csv':
                # Read without header to find the start of transactions
                temp_df = pd.read_csv(file_info.filename, header=None)
                header_row_index = find_header_row(temp_df, expected_headers)
                if header_row_index is not None:
                    df = pd.read_csv(file_info.filename, header=header_row_index)
                else:
                    print(f"Warning: Could not find a valid header in {file_info.filename}. Skipping.")
                    print("First 20 rows of the file for debugging:")
                    print(temp_df.head(20))
                    continue
            elif file_info.extension.lower() in ['xls', 'xlsx']:
                # Read the first sheet without a header to find the start of transactions
                sheet_name = file_info.sheet_names[0] if file_info.sheet_names else 0
                temp_df = pd.read_excel(file_info.filename, sheet_name=sheet_name, header=None)
                header_row_index = find_header_row(temp_df, expected_headers)
                if header_row_index is not None:
                    df = pd.read_excel(file_info.filename, sheet_name=sheet_name, header=header_row_index)
                else:
                    print(f"Warning: Could not find a valid header in {file_info.filename}. Skipping.")
                    # GEMINI: Added debugging step to print the first 20 rows of the file.
                    print("First 20 rows of the file for debugging:")
                    print(temp_df.head(20))
                    continue
            
            if df is not None:
                # Standardize column names
                print(f"Columns before rename for {file_info.filename}: {df.columns}")
                df.rename(columns=column_mapping, inplace=True)
                print(f"Columns after rename for {file_info.filename}: {df.columns}")
                
                # Data validation and cleaning
                required_columns = ['Transaction Date', 'Description']
                if not all(col in df.columns for col in required_columns):
                    print(f"Skipping {file_info.filename}: Missing one or more required columns after standardization.")
                    continue

                # Handle Debit/Credit to create a single 'Amount' column
                if 'Amount' not in df.columns:
                    if 'Debit' in df.columns and 'Credit' in df.columns:
                        df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
                        df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
                        df['Amount'] = df['Credit'] - df['Debit']
                    else:
                        print(f"Skipping {file_info.filename}: Could not determine transaction amount from Debit/Credit columns.")
                        continue
                else:
                    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')

                # Convert 'Transaction Date' to datetime, coercing errors
                df['Transaction Date'] = pd.to_datetime(df['Transaction Date'], errors='coerce')
                
                # Drop rows where essential data is missing after conversion
                df.dropna(subset=['Transaction Date', 'Description', 'Amount'], inplace=True)
                
                # Add a 'Bank' column for context
                df['Bank'] = bank_name
                
                all_transactions.append(df)

        except Exception as e:
            print(f"Error processing file {file_info.filename}: {e}")

    if all_transactions:
        return pd.concat(all_transactions, ignore_index=True)
    return None

def consolidate_files_by_bank(files: List[CrawledFile]) -> dict:
    """Consolidates a list of crawled files into a dictionary grouped by bank."""
    bank_files = {'HDFC': [], 'SBI': [], 'AXIS': [], 'UNKNOWN': []}
    
    for file in files:
        filename_lower = file.filename.lower()
        if 'hdfc' in filename_lower:
            bank_files['HDFC'].append(file)
        elif 'sbi' in filename_lower:
            bank_files['SBI'].append(file)
        elif 'axis' in filename_lower:
            bank_files['AXIS'].append(file)
        else:
            bank_files['UNKNOWN'].append(file)
            
    return bank_files

def post_process_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Applies deduplication, internal transfer identification, and tagging to the consolidated DataFrame."""
    # Sort by date to ensure chronological order
    df.sort_values(by='Transaction Date', inplace=True)
    
    # Deduplicate transactions
    df = deduplicate_transactions(df)
    
    # Identify internal transfers
    df = identify_internal_transfers(df)
    
    # Tag transactions
    df = tag_transactions(df)
    
    return df

def deduplicate_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Removes duplicate transactions based on a subset of columns."""
    subset_cols = ['Transaction Date', 'Description', 'Amount', 'Bank']
    
    initial_rows = len(df)
    df.drop_duplicates(subset=subset_cols, keep='first', inplace=True)
    duplicates_removed = initial_rows - len(df)
    if duplicates_removed > 0:
        print(f"  Removed {duplicates_removed} duplicate transactions.")
    return df

def identify_internal_transfers(df: pd.DataFrame) -> pd.DataFrame:
    """Identifies and tags internal transfers within the consolidated transactions."""
    df['Tag'] = 'Uncategorized' # Initialize Tag column
    
    # Find potential transfers: a debit and a credit of the same amount on the same day
    potential_transfers = df[df.duplicated(subset=['Transaction Date', 'Amount'], keep=False)]
    
    credits = potential_transfers[potential_transfers['Amount'] > 0]
    debits = potential_transfers[potential_transfers['Amount'] < 0]

    for _, credit_row in credits.iterrows():
        # Find a matching debit
        matching_debit = debits[
            (debits['Transaction Date'] == credit_row['Transaction Date']) &
            (debits['Amount'] == -credit_row['Amount'])
        ]
        
        if not matching_debit.empty:
            # Tag both sides of the transfer
            df.loc[credit_row.name, 'Tag'] = 'Internal Transfer'
            df.loc[matching_debit.index, 'Tag'] = 'Internal Transfer'

    return df

def tag_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Tags transactions based on keywords in their descriptions, skipping internal transfers.""" 
    tag_categories = {
        'Food': ['RESTAURANT', 'CAFE', 'SWIGGY', 'ZOMATO'],
        'Transport': ['UBER', 'OLA', 'PETROL', 'FUEL'],
        'Shopping': ['AMAZON', 'FLIPKART', 'MYNTRA'],
        'Salary': ['SALARY', 'PAY', 'INCOME', 'CAPITAL ONE'],
        'Bills': ['ELECTRICITY', 'RENT', 'BROADBAND', 'BESCOM'],
        'ATM Withdrawal': ['ATM WDL', 'CASH WDL']
    }

    # Only tag transactions that are not already tagged as 'Internal Transfer'
    untagged_mask = df['Tag'] == 'Uncategorized'
    
    for category, keywords in tag_categories.items():
        for keyword in keywords:
            # Create a boolean mask for rows that match the keyword and are untagged
            keyword_mask = df['Description'].str.contains(keyword, case=False, na=False)
            df.loc[untagged_mask & keyword_mask, 'Tag'] = category
            
    return df

if __name__ == "__main__":
    # Configuration
    config = load_config()
    data_path = config['paths']['input_data']
    output_dir = config['paths']['output_data']
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Crawl files and identify bank statements
    crawled_files = crawl_files(data_path)
    bank_files = consolidate_files_by_bank(crawled_files)

    # Step 2: Process transactions for each bank
    all_bank_dfs = []
    for bank, files in bank_files.items():
        if files:
            print(f"\nProcessing transactions for {bank}...")
            bank_df = process_bank_transactions(bank, files)
            if bank_df is not None:
                print(f"  Consolidated {len(bank_df)} transactions for {bank}")
                all_bank_dfs.append(bank_df)
            else:
                print(f"  No transactions consolidated for {bank}")

    # Step 3: Consolidate all bank transactions into a single DataFrame
    if all_bank_dfs:
        final_df = pd.concat(all_bank_dfs, ignore_index=True)
        
        # Step 4: Post-processing on the consolidated data
        final_df = post_process_transactions(final_df)
        
        # Save the final consolidated file
        final_output_filename = os.path.join(output_dir, 'all_transactions.csv')
        final_df.to_csv(final_output_filename, index=False)
        print(f"Saved all consolidated transactions to {final_output_filename}")
        
        print("\nFinal Consolidated Data Head:")
        print(final_df.head())
    else:
        print("\nNo transactions were processed from any bank.")