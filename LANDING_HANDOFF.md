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

## Additional completion work (flight run)

- Added `--version` support in CLI (`fipro 0.1.0`).
- `status` now prints resolved config path for easier operations/debugging.
- Added `resolve_config_path()` helper in config loader.
- Added a "Tomorrow morning runbook" section to `README.md` for immediate real-world use.
- Executed a full fixture-backed E2E dry run with temporary directories/config:
  - `status` detected all 3 banks (HDFC/SBI/AXIS)
  - `process` exported transactions and generated both outputs
  - input files moved to processed
  - failed count stayed zero

## Verification snapshot

- Unit/integration tests: `uv run pytest -q` -> **62 passed**
- E2E dry run command path:
  - `uv run python -m src.main status --config <tmp-config>`
  - `uv run python -m src.main process --config <tmp-config>`

## Remaining recommended enhancement (non-blocking for tomorrow)

1. Add CI workflow to run `uv sync` + `uv run pytest -q` on push/PR.
