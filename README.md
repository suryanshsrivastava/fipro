# Fipro

Personal finance tool that extracts, consolidates, and deduplicates bank transactions from HDFC, SBI, and Axis Excel statements, then exports to Goodbudget-compatible CSV.

## Quickstart

```bash
./scripts/setup.sh                     # one-shot: installs uv, syncs deps, installs hooks, runs gates
```

Or step-by-step:

```bash
uv sync --all-groups
uv run pre-commit install

# drop statements into data/input/, then:
uv run fipro process

# optional: view in local dashboard
uv run fipro dashboard --port 8080
```

## Common Commands

```bash
uv run pytest                          # tests + coverage
uv run ruff check src/ tests/          # lint
uv run ruff format src/ tests/         # format
uv run mypy src/                       # type check
uv run fipro status                    # show pending files
uv run fipro sheets --creds <path>     # upload to Google Sheets
```

## Layout

- `src/` — application code (parsers, core pipeline, exporters, UI)
- `tests/` — pytest suite with regression fixtures under `tests/fixtures/`
- `config/config.toml` — runtime configuration
- `data/input/` — drop bank statements here (gitignored)
- `data/output/` — generated CSV/JSON (gitignored)

## Further Reading

- [AGENTS.md](AGENTS.md) — working conventions for AI agents and humans
- [docs/PRD.md](docs/PRD.md) — product requirements and scope
- [docs/architecture.md](docs/architecture.md) — canonical architecture reference
- [RUNBOOK.md](RUNBOOK.md) — operations and release procedures
- [CONTRIBUTING.md](CONTRIBUTING.md) — contributor workflow and quality gates
- [docs/plans/](docs/plans/) — implementation plans, chronological

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) for dependency management
