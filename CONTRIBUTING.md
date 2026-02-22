# Contributing to neotree

## Development setup

- Use the `uv` environment for all Python commands.
- Run tests with `uv run pytest`.
- Keep changes behavior-preserving unless the PR explicitly targets behavior changes.

## Naming conventions

This project prioritizes intention-revealing names over short names.

### Source code

- Use prefix-based function naming by role:
  - `run_*`: orchestration / command execution flow (example: `run_ntree`)
  - `scan_*`: filesystem traversal and data collection (example: `scan`)
  - `format_*`: output rendering (example: `format_short`, `format_compat`)
- Use `build_*` for pure construction helpers that prepare data/options.
- Use `validate_*` for validation helpers that return errors or validation results.
- Avoid ambiguous temporary names such as `data`, `tmp`, `x` unless scope is trivially small.

### Test code

- Name test helper functions with `target + verb` so intent is obvious:
  - `*_tree` for fixture-like tree builders
  - `*_output` for render/run output helpers
  - `*_case` for scenario runners
- Prefer `expected_*` for expected values in parametrized tests.
  - Example: `expected_present_names`, `expected_absent_names`
- Keep test names behavior-oriented (what is guaranteed), not implementation-oriented.

## Refactoring guidelines

- Keep refactors minimal and behavior-preserving.
- Prefer extracting small helpers over adding complex abstractions.
- Update docstrings and tests together when names change.
- Run full tests after refactoring: `uv run pytest`.
