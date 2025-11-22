# AGENTS.md - Development Guidelines for Fipro

## Build/Test Commands
- **Environment**: Use `uv` for package management. Check for existing `.fipro-env` before creating new ones.
- **Dependencies**: Install with `uv add` or `pip install -r requirements.txt`
- **Testing**: No formal test framework detected. Use `python -m pytest` if added, or run scripts directly with `python script.py`
- **Linting**: No linting configured. Consider adding `ruff` or `black` for code formatting

## Code Style Guidelines

### Data Structures
- Use `dataclasses` with `slots=True` for efficiency (preferred over attrs/pydantic)
- Import: `from dataclasses import dataclass, field`
- Example: `@dataclass(slots=True)`

### Imports & Organization
- Standard library imports first, then third-party, then local imports
- Reuse code by adding common functions to `utils.py`
- Use type hints consistently: `from typing import List, Optional, Dict`

### Naming Conventions
- Classes: PascalCase (e.g., `CrawledFile`, `Account`)
- Functions/variables: snake_case (e.g., `consolidate_files_by_bank`)
- Constants: UPPER_SNAKE_CASE
- Private members: prefix with underscore

### Error Handling
- Use descriptive error messages
- Raise appropriate exceptions (FileNotFoundError, ValueError, etc.)
- Handle file operations with proper error checking

### File Organization
- Models in `src/models.py`
- Utility functions in `utils.py`
- Main processing logic in `src/` directory
- Configuration via `config.toml` (loaded with `tomllib`)

### Code Quality
- Add reusable code to `utils.py` to avoid duplication
- Use properties for computed attributes in dataclasses
- Follow PEP 8 formatting standards
- Include docstrings for public functions