# Bank Statement Transaction Processor

This Python script processes bank statements to extract and structure transaction data into a CSV format.

## Features

- Extracts transactions from bank statement text files
- Handles multi-line transaction entries
- Validates branch codes (Init.Br)
- Correctly identifies debit/credit amounts
- Maintains running balance accuracy
- Outputs structured CSV format

## Data Model

### Transaction Fields
- `Tran Date`: Transaction date (DD-MM-YYYY)
- `Chq No`: Cheque number (optional)
- `Particulars`: Transaction description
- `Debit`: Debit amount (optional)
- `Credit`: Credit amount (optional)
- `Balance`: Running balance
- `Init. Br`: Branch code (2177, 248, or 100)

## Components

### 1. Transaction Line Grouping
- Function: `group_transaction_lines()`
- Purpose: Groups lines belonging to same transaction
- Uses Init.Br values as transaction delimiters
- Handles multi-line transaction descriptions

### 2. Transaction Parser
- Function: `parse_transaction()`
- Purpose: Parses grouped lines into structured data
- Components:
  - Date extraction using regex
  - Amount parsing with debit/credit detection
  - Particulars cleaning and concatenation

### 3. Main Processing Pipeline
- Function: `extract_transactions()`
- Steps:
  1. Read input file
  2. Group transaction lines
  3. Parse transactions
  4. Write to CSV
  5. Validate output

## Validation

- Number of transactions validation
- First/Last transaction verification
- Init.Br code validation (2177, 248, 100)
- Balance calculation validation
- Credit/Debit amount validation

## Error Handling

- Graceful degradation for parsing errors
- Data validation at each step
- Balance consistency checks
- Proper exception handling

## File Formats

### Input
Text file with bank statement data in fixed format:
```
Date       Particulars                           Debit        Credit       Balance    Init.Br
DD-MM-YYYY Description                          Amount        Amount       Balance    Code
```

### Output
CSV file with fields:
```
Tran Date,Chq No,Particulars,Debit,Credit,Balance,Init. Br
```

## Technical Details

### Key Regular Expressions
- Date Pattern: `\d{2}-\d{2}-\d{4}`
- Amount Pattern: `(\d+\.\d{2})\s+(\d+\.\d{2})?\s+(\d+\.\d{2})\s+`

### Technical Constraints
- Handles multi-line transactions
- Preserves transaction order
- Maintains 2 decimal place precision
- Supports three branch codes (2177, 248, 100)

## Extension Points

- Custom parser configurations
- Additional validation rules
- Different output formats
- Transaction categorization
- Balance reconciliation

---

the notes I have on the project so far dumped here:

# Program

^df25f3

frequency: [[Month]]ly

- Download the transactions history from all the 3 banks till date
- the flow starts from [[Axis]] which is my salary credit account
	- [[HDFC]]: this is what we use for granular transactions going forward
	- [[SBI]]: this is where the allotted more structured transactions go
- go DFS?
- annotate pdf for credit card statements
	- verify and pay
[[Budgeting]]


