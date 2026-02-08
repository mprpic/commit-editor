# Development Guide

Read README.md to learn about this project.

This document describes how to work with the commit-editor project.

## Project Structure

```
src/commit_editor/
├── __init__.py    # Package init with version
├── cli.py         # CLI entry point (argparse)
├── app.py         # Textual app, custom TextArea, StatusBar, MessageBar, wrap_line
└── git.py         # Git integration (user.name, user.email, Signed-off-by)

tests/
├── conftest.py    # Pytest fixtures (temp_file, temp_file_with_content)
├── test_app.py    # Integration tests using Textual's Pilot
├── test_git.py    # Unit tests for git module (mocked subprocess)
└── test_wrap.py   # Unit tests for text wrapping functions
```

## Setup

Install dependencies:

```bash
uv sync
```

## Running the Tool

```bash
# Run directly with uv
uv run commit-editor path/to/file.txt

# Or after installing
uv tool install -e .
commit-editor path/to/file.txt
```

## Running All Checks with Tox

The project uses tox to automate testing, linting, formatting, and type checking across multiple Python versions. Run
all checks with:

```bash
tox
```

This runs:

- Tests on Python 3.11, 3.12, and 3.13
- Linting with ruff
- Format checking with ruff
- Type checking with ty

### Running Specific Tox Environments

```bash
# Run only tests on Python 3.13
tox -e py313

# Run only linting
tox -e lint

# Run only format check
tox -e check-format

# Run only type checking
tox -e typecheck

# Auto-fix linting issues
tox -e lint-fix

# Auto-format code
tox -e format
```

## Running Tests Manually

```bash
uv run pytest tests/

# With verbose output
uv run pytest tests/ -v

# Run a specific test file
uv run pytest tests/test_wrap.py -v

# Run a specific test
uv run pytest tests/test_app.py::TestQuitBehavior::test_ctrl_q_clean_exits_immediately -v
```

## Linting Manually

```bash
# Check for linting issues
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix
```

## Formatting Manually

```bash
# Check formatting
uv run ruff format --check .

# Apply formatting
uv run ruff format .
```
