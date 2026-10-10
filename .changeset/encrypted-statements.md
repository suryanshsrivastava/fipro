---
"fipro": minor
---

Process password-protected `.xls`/`.xlsx` statements (password from `FIPRO_<BANK>_STATEMENT_PASSWORD` or `FIPRO_STATEMENT_PASSWORD`, decrypted in memory) and detect the bank from a parent folder name when the filename has none (e.g. `SBI/AccountStatement_….xlsx`).
