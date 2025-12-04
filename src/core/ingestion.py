# import re, os
# import csv
# from models import CrawledFile
# from utils import load_config
# from typing import List, Tuple, Dict

# from datetime import datetime
# import pandas as pd

# def discover_files(config: dict) -> List[CrawledFile]:
#     """Discover files in the input directory and check permissions without loading content"""
#     data_path = config['paths']['input']
    
#     crawled_files: List[CrawledFile] = []
#     supported_extensions = set(config['supported_extensions'])

#     for root, _, files in os.walk(data_path):
#         for file in files:
#             file_path = os.path.join(root, file)
#             extension = file.split('.')[-1].lower()

#             if extension not in supported_extensions:
#                 print(f"Warning: Unsupported file extension: {extension}. Do you want to manually add {file} to the config?")
#                 continue
#             try:
#                 # Check if file is readable
#                 if not os.access(file_path, os.R_OK):
#                     print(f"Warning: No read permission for {file_path}.")
#                     # TODO add to excluded files list
#                     # Stop processing if we encounter a non-readable file
#                     break
                
#                 # Get basic file info without loading content
#                 file_info = {
#                     'filepath': file_path,
#                     'extension': extension,
#                     'size': os.path.getsize(file_path),
#                     'crawl_date': datetime.now().isoformat(),
#                 }
#                 crawled_files.append(CrawledFile(**file_info))
#             except Exception as e:
#                 print(f"Error processing file {file_path}: {e}")

#     print(f"Discovered {len(crawled_files)} files.")
#     return crawled_files

# def load_files_to_dataframes(files: List[CrawledFile]) -> Dict[str, pd.DataFrame]:
#     """Load discovered files into pandas dataframes"""
    # dataframes = {}
    
    # for file in files:
    #     try:
    #         if file.extension == 'csv':
    #             df = pd.read_csv(file.filename)
    #             dataframes[file.filename] = df
    #             print(f"Loaded CSV: {file.filename} with {len(df)} rows")
                
    #         elif file.extension.lower() in ['xls', 'xlsx']:
    #             # Load all sheets from Excel file
    #             excel_file = pd.ExcelFile(file.filename)
    #             for sheet_name in excel_file.sheet_names:
    #                 df = pd.read_excel(file.filename, sheet_name=sheet_name)
    #                 key = f"{file.filename}:{sheet_name}"
    #                 dataframes[key] = df
    #                 print(f"Loaded Excel sheet: {key} with {len(df)} rows")
                    
    #         elif file.extension == 'pdf':
    #             # PDF processing is currently skipped
    #             print(f"PDF file skipped: {file.filename}")
    #             continue
                
    #     except Exception as e:
    #         print(f"Error loading file {file.filename}: {e}")
    
    # return dataframes

def analyze_discovered_files(files: List[CrawledFile]) -> dict:
    """Analyze discovered files and provide summary statistics"""
    analysis = {
        'total_files': len(files),
        'by_extension': {},
        'by_bank': {},
        'total_size': 0,
        'readable_files': 0
    }
    
    for file in files:
        # Count by extension
        ext = file.extension.lower()
        analysis['by_extension'][ext] = analysis['by_extension'].get(ext, 0) + 1
        
        # Count by bank
        bank = get_bank_from_filename(file.filename)
        analysis['by_bank'][bank] = analysis['by_bank'].get(bank, 0) + 1
        
        # Total size
        analysis['total_size'] += file.size
        
        # Count readable files
        if os.access(file.filename, os.R_OK):
            analysis['readable_files'] += 1
    
    return analysis

def get_bank_from_filename(filename: str) -> str:
    """Extract bank name from filename"""
    filename_upper = filename.upper()
    if 'HDFC' in filename_upper:
        return 'HDFC'
    elif 'SBI' in filename_upper:
        return 'SBI'
    elif 'AXIS' in filename_upper:
        return 'AXIS'
    else:
        return 'UNKNOWN'

def print_file_summary(files: List[CrawledFile]):
    """Print a summary of discovered files"""
    if not files:
        print("No files discovered.")
        return
    
    analysis = analyze_discovered_files(files)
    
    print(f"\n=== File Discovery Summary ===")
    print(f"Total files: {analysis['total_files']}")
    print(f"Readable files: {analysis['readable_files']}")
    print(f"Total size: {analysis['total_size'] / (1024*1024):.2f} MB")
    
    print(f"\nBy extension:")
    for ext, count in analysis['by_extension'].items():
        print(f"  {ext.upper()}: {count}")
    
    print(f"\nBy bank:")
    for bank, count in analysis['by_bank'].items():
        print(f"  {bank}: {count}")

def group_transaction_lines(config: dict) -> List[List[str]]:
    """Group lines belonging to the same transaction based on Init.Br values"""
    transactions = []
    current_group = []
    
    with open(config['paths']['input_file'], 'r') as file:
        in_transactions = False
        for line in file:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Start capturing after header row
            if "Tran Date" in line and "Chq No" in line and "Particulars" in line:
                in_transactions = True
                continue
            
            if not in_transactions:
                continue
                
            # Stop at transaction total
            if "TRANSACTION TOTAL" in line:
                break
                
            # If line ends with Init.Br values, it's the end of a transaction
            words = line.split()
            if words and is_init_br(words[-1]):
                current_group.append(line)
                if current_group:
                    transactions.append(current_group)
                current_group = []
            else:
                current_group.append(line)
    
    return transactions

def parse_transaction(lines: List[str]) -> Tuple[str, str, str, float, float, float, str]:
    """
    Parse transaction lines into CSV fields, properly handling multi-line descriptions.
    """
    full_text = ' '.join(line.strip() for line in lines)

    # Extract date (DD-MM-YYYY format)
    date_match = re.search(r'(\d{2}-\d{2}-\d{4})', full_text)
    date = date_match.group(1) if date_match else ''

    # Extract Init.Br (any of the specified codes)
    init_br_match = re.search(r'(2177|248|100)$', full_text)
    init_br = init_br_match.group(1) if init_br_match else ''

    # Extract amounts and balance using a more robust regex
    # This regex looks for numbers with two decimal places, which could be debit, credit, or balance
    amounts_match = re.search(r'(\d+\.\d{2})\s+(\d+\.\d{2})?\s*(\d+\.\d{2})\s+' + re.escape(init_br) if init_br else r'(\d+\.\d{2})\s+(\d+\.\d{2})?\s*(\d+\.\d{2})', full_text)
    
    debit, credit, balance = 0.00, 0.00, 0.00
    if amounts_match:
        # The last number is always the balance
        balance = float(amounts_match.group(3) if amounts_match.group(3) else amounts_match.group(2))
        
        # If there are two amounts before the balance, they are debit and credit
        if amounts_match.group(2):
            debit = float(amounts_match.group(1))
            credit = float(amounts_match.group(2))
        # If there is one amount, we'll classify it later in `classify_transactions`
        else:
            # Temporarily assign to debit, will be corrected later
            debit = float(amounts_match.group(1))

    # Extract particulars by removing known parts (date, amounts, Init.Br)
    particulars = full_text
    if date:
        particulars = particulars.replace(date, '').strip()
    if init_br:
        particulars = particulars.replace(init_br, '').strip()
    if amounts_match:
        particulars = particulars.replace(amounts_match.group(0), '').strip()
    
    # Clean up particulars by removing extra spaces and "Br" prefixes
    particulars = re.sub(r'\s+', ' ', particulars).strip()
    particulars = re.sub(r'^Br\s+', '', particulars, flags=re.IGNORECASE)

    return (date, '', particulars, debit, credit, balance, init_br)

def classify_transactions(config: dict):
    """Classify transactions as debit or credit based on balance changes"""
    # Open the CSV file
    with open(config['paths']['output_file'], 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Read the header row

        rows = list(reader)

        # Initialize the previous balance to 0
        prev_balance = 0.0

        for row in rows:
            try:
                # Get the current balance
                current_balance = float(row[5])  # Assuming balance is in the 6th column

                # Classify as debit or credit based on balance change
                if current_balance > prev_balance:
                    row[4] = f"{current_balance - prev_balance:.2f}"  # Update Credit column
                    row[3] = ""  # Clear Debit column
                    # logging.debug(f"Classified as Credit: {row[4]}")
                elif current_balance < prev_balance:
                    row[3] = f"{prev_balance - current_balance:.2f}"  # Update Debit column
                    row[4] = ""  # Clear Credit column
                    # logging.debug(f"Classified as Debit: {row[3]}")
                else:
                    row[3] = row[4] = ""  # Clear both columns if no change
                    # logging.debug("No change in balance, cleared Debit and Credit columns.")

                # Update the previous balance
                prev_balance = current_balance
            except ValueError:
                # Handle rows with invalid balance values
                row[3] = row[4] = ""
                # logging.error(f"Invalid balance value in row: {row}")

    # Write the updated rows back to the CSV file
    with open(config['paths']['output_file'], 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)  # Write the header row
        writer.writerows(rows)  # Write the updated rows

def count_transactions(config: dict):
    """Count transactions, debits, and credits, and print first and last rows"""
    # Open the CSV file
    with open(config['paths']['output_file'], 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Read the header row

        rows = list(reader)

        # Count the number of transactions
        num_transactions = len(rows)

        # Get the first and last rows
        first_row = rows[0] if rows else None
        last_row = rows[-1] if rows else None

        # Count the number of debits and credits
        num_debits = sum(1 for row in rows if row[3])  # Debit column
        num_credits = sum(1 for row in rows if row[4])  # Credit column

def validate_transactions(config: dict):
    """Validate transactions by checking for missing values and inconsistencies"""
    with open(config['paths']['output_file'], 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Read the header row
def clean_particulars(config: dict):
    """Clean the 'Particulars' column in the output CSV file"""
    with open(config['paths']['output_file'], 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Read the header row
        rows = list(reader)

    for row in rows:
        particulars = row[2]
        # Remove redundant spaces
        particulars = ' '.join(particulars.split())
        # Remove trailing characters like 'Br'
        particulars = re.sub(r'\s+Br$', '', particulars, flags=re.IGNORECASE)
        row[2] = particulars

    with open(config['paths']['output_file'], 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

def remove_br_prefix(config: dict):
    """Remove 'Br' prefix from the 'Particulars' column in the output CSV file"""
    with open(config['paths']['output_file'], 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Read the header row
        rows = list(reader)

    for row in rows:
        particulars = row[2]
        # Remove 'Br' prefix, case-insensitive
        particulars = re.sub(r'^Br\s+', '', particulars, flags=re.IGNORECASE)
        row[2] = particulars

    with open(config['paths']['output_file'], 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

def log_summary(config: dict):
    """Log the summary of the transactions"""
    with open(config['paths']['output_file'], 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Read the header row
        rows = list(reader)

        num_transactions = len(rows)
        num_debits = sum(1 for row in rows if row[3])
        num_credits = sum(1 for row in rows if row[4])

if __name__ == "__main__":
    config = load_config()
    
    # Discover files without loading content
    print("Discovering files...")
    discovered_files = discover_files(config)
    
    # Print summary of discovered files
    print_file_summary(discovered_files)

    #  ------------------------------------------------------------------------------------
    #  Step 2: Load files into dataframes (only when needed)
    #  ------------------------------------------------------------------------------------
    # try:
    #     # Group files by bank
    #     bank_files = consolidate_files_by_bank(discovered_files)
    #     for bank, files in bank_files.items():
    #         if files:
    #             print(f"\nBank: {bank}")
    #             for f in files:
    #                 print(f"  - {f.filename}")
        
        # Load files into dataframes (optional - only if needed)
        # print("\nLoading files into dataframes...")
        # dataframes = load_files_to_dataframes(discovered_files)
        # print(f"Loaded {len(dataframes)} dataframes")
        
        # Analyze loaded dataframes
        # if dataframes:
        #     analyze_dataframes(dataframes)
            
        #     # Example: Get dataframes for a specific bank
        #     hdfc_dataframes = get_dataframe_by_bank(dataframes, 'HDFC')
        #     if hdfc_dataframes:
        #         print(f"\nHDFC dataframes: {len(hdfc_dataframes)}")
        #         for key in hdfc_dataframes.keys():
        #             print(f"  - {key}")
    # except FileNotFoundError:
    #     print("Configuration file not found. Please ensure config.toml exists.")
    #     exit(1)
    # except Exception as e:
    #     print(f"An error occurred: {e}")
    #     exit(1)