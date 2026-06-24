import csv
from pathlib import Path

import gspread

from src.exporters.goodbudget import GOODBUDGET_FIELDNAMES

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

DEFAULT_SPREADSHEET_ID_PATH = "config/fipro_spreadsheet_id.txt"


def _read_spreadsheet_id(path: Path) -> str | None:
    if not path.exists():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value or None


def _write_spreadsheet_id(path: Path, spreadsheet_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(spreadsheet_id, encoding="utf-8")


def _open_or_create_spreadsheet(
    client: gspread.Client,
    spreadsheet_title: str,
    spreadsheet_id_path: Path,
) -> gspread.Spreadsheet:
    stored_id = _read_spreadsheet_id(spreadsheet_id_path)
    if stored_id:
        try:
            return client.open_by_key(stored_id)
        except gspread.SpreadsheetNotFound:
            spreadsheet = client.create(spreadsheet_title)
            _write_spreadsheet_id(spreadsheet_id_path, spreadsheet.id)
            return spreadsheet

    try:
        spreadsheet = client.open(spreadsheet_title)
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(spreadsheet_title)

    _write_spreadsheet_id(spreadsheet_id_path, spreadsheet.id)
    return spreadsheet


def _apply_sheet_formatting(
    worksheet: gspread.Worksheet,
    spreadsheet: gspread.Spreadsheet,
    cell_count: int,
) -> None:
    worksheet.format(
        "A1:G1",
        {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.12, "green": 0.14, "blue": 0.22},
            "textFormatForegroundColor": {"red": 0.9, "green": 0.92, "blue": 0.95},
        },
    )
    if cell_count > 1:
        worksheet.format(
            f"F2:F{cell_count}",
            {
                "numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"},
            },
        )
    spreadsheet.batch_update(
        {
            "requests": [
                {"autoResizeDimensions": {"dimensions": {"dimension": "COLUMNS", "startIndex": 0, "endIndex": 7}}}
            ]
        }
    )


def _trim_leftover_rows(worksheet: gspread.Worksheet, data_row_count: int) -> None:
    grid_rows = worksheet.row_count
    if grid_rows > data_row_count:
        worksheet.batch_clear([f"A{data_row_count + 1}:G{grid_rows}"])


def export_to_google_sheets(
    csv_path: str,
    credentials_path: str = "config/google_credentials.json",
    spreadsheet_title: str = "Fipro Transactions",
    spreadsheet_id_path: str = DEFAULT_SPREADSHEET_ID_PATH,
) -> str:
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

    client = gspread.service_account(filename=credentials_path, scopes=SCOPES)
    id_path = Path(spreadsheet_id_path)

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

    spreadsheet = _open_or_create_spreadsheet(client, spreadsheet_title, id_path)
    worksheet = spreadsheet.sheet1

    batch_size = 1000
    for i in range(0, len(data_rows), batch_size):
        batch = data_rows[i : i + batch_size]
        start_row = i + 1
        end_row = start_row + len(batch) - 1
        if i == 0:
            worksheet.update(f"A1:G{end_row}", batch)  # type: ignore[arg-type]  # pre-existing, tracked as SHEETS-001
        else:
            worksheet.append_rows(batch, insert_data_option="OVERWRITE")  # type: ignore[arg-type]  # pre-existing, tracked as SHEETS-001

    cell_count = len(data_rows)
    _trim_leftover_rows(worksheet, cell_count)
    _apply_sheet_formatting(worksheet, spreadsheet, cell_count)

    spreadsheet_url = spreadsheet.url
    print(f"Google Sheet updated: {spreadsheet_url}")
    return spreadsheet_url
