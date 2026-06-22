import csv
from pathlib import Path

import gspread

from src.exporters.goodbudget import GOODBUDGET_FIELDNAMES

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def _open_or_create_spreadsheet(client: gspread.Client, spreadsheet_title: str) -> gspread.Spreadsheet:
    try:
        return client.open(spreadsheet_title)
    except gspread.SpreadsheetNotFound:
        return client.create(spreadsheet_title)


def export_to_google_sheets(
    csv_path: str,
    credentials_path: str = "config/google_credentials.json",
    spreadsheet_title: str = "Fipro Transactions",
) -> str:
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

    client = gspread.service_account(filename=credentials_path, scopes=SCOPES)

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

    spreadsheet = _open_or_create_spreadsheet(client, spreadsheet_title)
    worksheet = spreadsheet.sheet1
    worksheet.clear()

    batch_size = 1000
    for i in range(0, len(data_rows), batch_size):
        batch = data_rows[i : i + batch_size]
        start_row = i + 1
        end_row = start_row + len(batch) - 1
        if i == 0:
            worksheet.update(f"A1:G{end_row}", batch)  # type: ignore[arg-type]
        else:
            worksheet.append_rows(batch, insert_data_option="OVERWRITE")  # type: ignore[arg-type]

    worksheet.format(
        "A1:G1",
        {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.12, "green": 0.14, "blue": 0.22},
            "textFormatForegroundColor": {"red": 0.9, "green": 0.92, "blue": 0.95},
        },
    )

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
    print(f"Google Sheet updated: {spreadsheet_url}")
    return spreadsheet_url
