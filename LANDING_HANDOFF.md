# Landing Handoff (branch: `tum`)

## What I changed

1. **Filled the previously empty `README.md`** with a production-usable MVP guide:
   - project purpose and MVP scope
   - supported banks and processing behavior
   - setup and run commands using `uv`
   - CLI usage (`process`, `status`)
   - config overview
   - output artifacts and CSV schema
   - testing instructions

## Why this was highest-impact now

- The repository README was empty, which blocks fast onboarding and handoff.
- Current implementation is test-backed and functional, but discoverability/operability from docs was poor.
- This change makes the project immediately usable for a developer/operator landing in the repo cold.

## Verification performed

- Environment setup:
  - `uv sync` completed successfully
- Test suite:
  - `uv run pytest -q`
  - **Result:** `62 passed`

## How to run/verify locally

```bash
uv sync
mkdir -p data/input data/output data/processed data/failed logs
uv run python -m src.main status
uv run python -m src.main process
uv run pytest -q
```

## Follow-ups (recommended)

1. Add one short end-to-end example section in README with sample input/output filenames.
2. Add CI workflow to run `uv sync` + `uv run pytest -q` on push/PR.
3. Add a tiny `--version` CLI command and expose config path in `status` output for smoother ops.
