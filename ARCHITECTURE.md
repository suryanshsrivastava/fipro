# Fipro Architecture

The canonical architecture document lives at [fipro-docs/fipro-architecture.md](fipro-docs/fipro-architecture.md).

## Quick summary

Fipro is a local-first Python CLI that:

1. Ingests monthly bank statement exports from `data/input/`
2. Routes each file to a bank-specific parser (HDFC, SBI, Axis) in `src/parsers/`
3. Extracts transactions into a unified `Transaction` dataclass
4. Deduplicates by hash and detects internal transfers
5. Exports to Goodbudget CSV and a local HTML dashboard

```
data/input/*.xls -> src/core/orchestrator.py
                     -> src/parsers/{hdfc,sbi,axis}.py
                       -> src/models/transactions.py (Transaction)
                         -> src/core/deduplicator.py
                           -> src/core/transfer_detector.py
                             -> src/exporters/goodbudget.py -> data/output/*.csv
                             -> src/exporters/report.py -> data/output/*.json
                             -> src/ui/dashboard.py (HTTP server)
```

See the canonical doc for the full mermaid diagram, roadmap, and data model reference.
