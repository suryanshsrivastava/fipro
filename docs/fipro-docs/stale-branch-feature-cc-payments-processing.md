# Archive: `feature/cc-payments-processing` (remote)

This note records what mattered from the stale branch before deletion. Last activity on that line was **2025-08-17** (PR #2 merge: CodeRabbit-generated tests).

## Name vs contents

The branch name suggests credit-card payment **details**; the tree did **not** implement card-specific parsing or payment-detail fields. Anything labeled “credit” in the old script is the bank statement **Debit/Credit columns**, not credit-card products.

## What lived on the branch (non-cache)

| Artifact | Notes |
|----------|--------|
| `extract_transactions.py` | Legacy pipeline: read `extracted_transations.txt` (typo in filename), group lines by `Init.Br`, parse Tran Date / Chq No / Particulars / Debit / Credit / Balance, write CSV, optional debit/credit classification from balance deltas. Early experiment; **superseded** by the current `src/` parsers and CLI. |
| `docs/NOTES.md` | Short personal project notes (monthly flow, Axis as salary account, HDFC vs SBI usage). **Future considerations** copied below for reference. |
| `tests/test_notes_documentation_validation.py` | Only unique delta vs `main` history: validation tests for `.gitignore`, README, and notes (CodeRabbit). Safe to drop unless you want to resurrect that style of doc-validation tests. |

## `docs/NOTES.md` future considerations (verbatim snapshot)

- Go DFS (Digital Financial Services)?
- Annotate PDF for credit card statements — verify and pay
- Budgeting implementation

Product direction for credit cards on **current `main`** is different: Excel-only MVP; credit cards appear as **configured external accounts** and **payment keywords** for note tagging (see `config/config.toml` and implementation plans under `docs/plans/`), not PDF/card-statement ingestion.

## Deletion checklist

- [ ] Confirm no need to cherry-pick `tests/test_notes_documentation_validation.py`.
- [ ] Remove remote branch: `git push origin --delete feature/cc-payments-processing`
