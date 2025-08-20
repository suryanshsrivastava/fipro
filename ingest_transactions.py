import re, os
import csv
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd

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

def extract_transactions(data_path: str):
    """Main function to extract and write transactions to CSV"""
    
    crawled_files: List[CrawledFile] = []
    supported_extensions = {'pdf', 'xls', 'csv'}

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

                if extension == 'PDF':
                    # PDF processing is currently skipped as in original code
                    pass
                elif extension.lower() in ['xls', 'xlsx']:
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

    for f in crawled_files:
        print(f"File: {f.filename}, Extension: {f.extension}")
        if f.sheet_names: print(f"  Sheets: {f.sheet_names}")
        if f.row_count: print(f"  Rows: {f.row_count}")

    print(crawled_files)
    
    # Consolidate these into a single list of transactions for each bank based on keywords: SBI, AXIS, HDFC etc
    bank_files = consolidate_files_by_bank(crawled_files)
    
    for bank, files in bank_files.items():
        if files:
            print(f"\nBank: {bank}")
            for f in files:
                print(f"  - {f.filename}")    

def consolidate_files_by_bank(files: List[CrawledFile]) -> dict:
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

# ------------------------------------------------------------------------------
# Validation 1: Check number of transactions
# print(f"Number of transactions found: {len(transactions)}")

# Write to CSV with proper number formatting
    with open('output.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(['Tran Date', 'Chq No', 'Particulars', 'Debit', 'Credit', 'Balance', 'Init. Br'])
        
        # Write transactions
        for transaction_lines in transactions:
            date, chq_no, particulars, debit, credit, balance, init_br = parse_transaction(transaction_lines)
            # Format numbers with exactly 2 decimal places
            row = [
                date,
                chq_no,
                particulars, 
                f"{debit:.2f}" if debit else "",
                f"{credit:.2f}" if credit else "",
                f"{balance:.2f}",
                init_br
            ]
            writer.writerow(row)
    
    # Validation 2: Print first and last transactions
    with open('output.csv', 'r') as csvfile:
        reader = list(csv.reader(csvfile))
        # print("\nFirst transaction:")
        # print(reader[1])
        # print("\nLast transaction:")
        # print(reader[-1])

    # classify_transactions()

    # count_transactions()

def group_transaction_lines() -> List[List[str]]:
    """Group lines belonging to the same transaction based on Init.Br values"""
    transactions = []
    current_group = []
    
    with open('extracted_transations.txt', 'r') as file:
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

def classify_transactions():
    """Classify transactions as debit or credit based on balance changes"""
    # Open the CSV file
    with open('output.csv', 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Read the header row

        rows = list(reader)

        # Initialize the previous balance to 0
        prev_balance = 0.0

        for row in rows:
            try:
                # Get the current balance
                current_balance = float(row[5])  # Assuming balance is in the 6th column

                # Log the balances for debugging
                # logging.debug(f"Previous Balance: {prev_balance}, Current Balance: {current_balance}")

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
    with open('output.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)  # Write the header row
        writer.writerows(rows)  # Write the updated rows

def count_transactions():
    """Count transactions, debits, and credits, and print first and last rows"""
    # Open the CSV file
    with open('output.csv', 'r') as file:
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

        # Print the results
        # print(f"Number of transactions processed: {num_transactions}")
        # print(f"First transaction: {first_row}")
        # print(f"Last transaction: {last_row}")
        # print(f"Number of debits: {num_debits}")
        # print(f"Number of credits: {num_credits}")

def validate_transactions():
    """Validate transactions by checking for missing values and inconsistencies"""
    with open('output.csv', 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Read the header row

        # for row in reader:
            # Check for missing values in critical columns
            # if not row[0]:  # Tran Date
            #     logging.warning(f"Missing transaction date in row: {row}")
            # if not row[2]:  # Particulars
            #     logging.warning(f"Missing particulars in row: {row}")
            # if not row[5]:  # Balance
            #     logging.warning(f"Missing balance in row: {row}")

            # Check for inconsistencies in debit/credit columns
            # if row[3] and row[4]:
            #     logging.warning(f"Both debit and credit columns have values in row: {row}")

def clean_particulars():
    """Clean the 'Particulars' column in the output CSV file"""
    with open('output.csv', 'r') as file:
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

    with open('output.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

def remove_br_prefix():
    """Remove 'Br' prefix from the 'Particulars' column in the output CSV file"""
    with open('output.csv', 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Read the header row
        rows = list(reader)

    for row in rows:
        particulars = row[2]
        # Remove 'Br' prefix, case-insensitive
        particulars = re.sub(r'^Br\s+', '', particulars, flags=re.IGNORECASE)
        row[2] = particulars

    with open('output.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

def log_summary():
    """Log the summary of the transactions"""
    with open('output.csv', 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Read the header row
        rows = list(reader)

        num_transactions = len(rows)
        num_debits = sum(1 for row in rows if row[3])
        num_credits = sum(1 for row in rows if row[4])

        # logging.info(f"Total transactions processed: {num_transactions}")
        # logging.info(f"Number of debit transactions: {num_debits}")
        # logging.info(f"Number of credit transactions: {num_credits}")

if __name__ == "__main__":
    extract_transactions('.data')
    # validate_transactions()
    # clean_particulars()
    # remove_br_prefix()
    # log_summary()