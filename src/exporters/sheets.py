import csv
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from src.exporters.goodbudget import GOODBUDGET_FIELDNAMES

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def export_to_google_sheets(
    csv_path: str,
    credentials_path: str = "config/google_credentials.json",
    spreadsheet_title: str = "Fipro Transactions",
) -> str:
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.authorize(creds)

    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))

    headers = list(GOODBUDGET_FIELDNAMES)
    data_rows = [headers]
    for row in rows:
        data_rows.append(
            [
                row.get("Date", ""),
                row.get("Envelope", ""),
                row.get("Account", ""),
                row.get("Name", "")[:100],
                row.get("Notes", ""),
                row.get("Amount", ""),
                row.get("Status", ""),
            ]
        )

    spreadsheet = client.create(spreadsheet_title)
    worksheet = spreadsheet.sheet1

    # Write in batches of 1000 rows to avoid API limits
    batch_size = 1000
    for i in range(0, len(data_rows), batch_size):
        batch = data_rows[i : i + batch_size]
        start_row = i + 1
        end_row = start_row + len(batch) - 1
        if i == 0:
            worksheet.update(f"A1:G{end_row}", batch)  # type: ignore[arg-type]  # pre-existing, tracked as SHEETS-001
        else:
            worksheet.append_rows(batch, insert_data_option="OVERWRITE")  # type: ignore[arg-type]  # pre-existing, tracked as SHEETS-001

    # Format headers
    worksheet.format(
        "A1:G1",
        {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.12, "green": 0.14, "blue": 0.22},
            "textFormatForegroundColor": {"red": 0.9, "green": 0.92, "blue": 0.95},
        },
    )

    # Format amount column
    cell_count = len(data_rows)
    worksheet.format(
        f"F2:F{cell_count}",
        {
            "numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"},
        },
    )

    resize_request = {
        "requests": [{"autoResizeDimensions": {"dimensions": {"dimension": "COLUMNS", "startIndex": 0, "endIndex": 7}}}]
    }
    spreadsheet.batch_update(resize_request)

    spreadsheet_url = spreadsheet.url
    print(f"Google Sheet created: {spreadsheet_url}")
    return spreadsheet_url
