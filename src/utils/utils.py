from src.models.account import CrawledFile


def consolidate_files_by_bank(files: list[CrawledFile]) -> dict[str, list[CrawledFile]]:
    bank_files: dict[str, list[CrawledFile]] = {"HDFC": [], "SBI": [], "AXIS": [], "UNKNOWN": []}
    for file in files:
        name = file.filename.upper()
        if "HDFC" in name:
            bank_files["HDFC"].append(file)
        elif "SBI" in name:
            bank_files["SBI"].append(file)
        elif "AXIS" in name:
            bank_files["AXIS"].append(file)
        else:
            bank_files["UNKNOWN"].append(file)
    return bank_files
