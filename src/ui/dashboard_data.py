import csv


def load_csv_data(csv_path: str) -> list[dict]:
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))

    normalized_rows: list[dict] = []
    for row in rows:
        amount = row.get("amount") or row.get("Amount") or ""
        try:
            signed_amount = float(amount)
        except (TypeError, ValueError):  # fmt: skip
            signed_amount = 0.0
        normalized_rows.append(
            {
                "hash": row.get("hash") or "",
                "transaction_date": row.get("transaction_date") or row.get("Date") or "",
                "description": row.get("description") or row.get("Name") or "",
                "amount": amount,
                "transaction_type": row.get("transaction_type") or ("debit" if signed_amount < 0 else "credit"),
                "source_bank": row.get("source_bank") or row.get("Account") or "",
                "source_file": row.get("source_file") or "",
                "status": row.get("status") or row.get("Status") or "",
                "notes": row.get("notes") or row.get("Notes") or "",
                **{
                    key: row.get(key) or ""
                    for key in (
                        "payment_mode",
                        "counterparty",
                        "category",
                        "review_status",
                        "need_want",
                        "frequency",
                        "splitwise",
                    )
                },
            }
        )
    return normalized_rows
