# Fold vs Fipro: feature comparison

Source for Fold: its public FAQ and help center (read Nov 2026). Nothing was reverse engineered, and
claims come from Fold's own marketing copy, so treat them as unverified. Fipro column: from AGENTS.md
and a quick look at `src/ui/dashboard.py` (it has search, sort and filter; I did not audit it further).

Fipro is a local-first ledger built from statements. Fold is a hosted app built from Account Aggregator
(AA) and Gmail alerts. Features are ranked by value for Fipro, not by how impressive they are in Fold.

## Ranked candidates

| # | Fold feature | Fipro today | Value for Fipro | Effort | Notes |
|---|---|---|---|---|---|
| 1 | Cards in one unified list with bank transactions | Not ingested (only tagged as payments in bank statements) | Very high | Medium-high | Already in progress: Gmail PDF fetch, then card layouts. Removes the double-count of card bill payments. |
| 2 | Internal-transfer detection that leaves transfers out of spend | Done (`transfer_detector`) | n/a | n/a | Fipro matches Fold here. Extend it to card bill payment vs card-side credit once cards exist. |
| 3 | Recurring payment detection (subscriptions, rent, EMIs, bills) | Missing. A `frequency` label exists but is hand-set | High | Low-medium | Derivable from counterparty + amount + monthly cadence. Fits the existing counterparty/narration code. Could pre-fill `frequency`. |
| 4 | Merchant recognition and auto-categorisation | Counterparty derived from narration; category rules; local-model suggestions (0.9+ one-click) | High, partly done | Low | Gap is coverage. Extend `narration.py` merchant cleanup (UPI VPAs, card merchant strings). |
| 5 | Plain-language search ("Swiggy this month", "about 500") | Dashboard text search and sort | Medium | Low-medium | A small query parser (merchant, month, amount range) over `dashboard_data.csv`. No LLM needed. |
| 6 | Transaction groups (trip, renovation) with totals and CSV export | Missing | Medium | Low | One extra annotation column (`group`) plus a filter and a total. |
| 7 | Refund and reversal tracking | Missing | Medium | Medium | Statements include refunds, which Fold's email alerts miss. Matching a credit to its original debit is a real advantage of the statement route. |
| 8 | Augmented balance (balance minus card dues and upcoming recurring) | Missing | Medium | Low once 1 and 3 exist | Pure arithmetic over card outstanding and recurring list. |
| 9 | Spend by category / merchant per day, week, month; cash-flow view | Dashboard shows transactions; charts not confirmed | Medium | Low | Check what the dashboard already aggregates before building. |
| 10 | Notes on transactions | `notes` column in annotations | n/a | n/a | Already there. |
| 11 | Recurring-bill calendar and reminders | Missing | Low | Medium | Needs notifications; weak fit for a local CLI tool. |
| 12 | Budgets | Handled by Goodbudget envelopes | Low | n/a | Fold has none yet either. Keep delegating to Goodbudget. |
| 13 | Splits and money friends owe | `splitwise` flag in annotations | Low | n/a | Already covered at label level. |
| 14 | Net worth, mutual funds, stocks, EPF, NPS, loans, credit score | Out of scope | Low | High | Needs AA or other regulated sources. Skip. |
| 15 | Spaces (family shared view) | Out of scope (single user) | Low | n/a | Skip. |
| 16 | Automatic bank sync via AA | Not possible for a personal tool | n/a | n/a | Needs a regulated FIU. Statement download or Gmail attachments remain the route. |
| 17 | Mobile app, widgets, push alerts | Out of scope | Low | High | Skip. |
| 18 | AI assistant over your data (Fold MCP) | Local suggester only | Low-medium | Medium | Could expose the ledger to an agent locally later. Not before the data is complete. |

## Where Fipro is already stronger (by design)

- Statement-level completeness: refunds, EMIs, interest and fees. Fold's own known-issues page says
  alert-based card tracking misses these and starts from the last statement date.
- Data stays on the machine. Fold sends amount, merchant and time to its servers.
- Append-only corpus, dedup across overlapping statements, Goodbudget export, `Group/Envelope`
  categories, need/want labels.
- Uni Gold coverage is possible via manual PDF; Fold lists it as unsupported.

## Suggested order

1. Card statement ingestion (items 1, 2): already under way.
2. Recurring detection (3) and merchant cleanup (4): the best value per line of code.
3. Refund matching (7) and groups (6).
4. Search parser (5) and augmented balance (8).
5. Everything else only if a concrete need appears.

## Unverified

- Fold behaviour beyond its public docs (accuracy of its categoriser, recurring detection quality).
- Which of these the current dashboard already does; check `src/ui/dashboard.py` before starting 5 and 9.
