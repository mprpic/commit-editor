# Commit Editor

[![PyPI](https://img.shields.io/pypi/v/commit-editor.svg)](https://pypi.python.org/pypi/commit-editor)
[![Python](https://img.shields.io/pypi/pyversions/commit-editor.svg)](https://pypi.python.org/pypi/commit-editor)
[![License](https://img.shields.io/pypi/l/commit-editor.svg)](https://github.com/mprpic/commit-editor/blob/main/LICENSE)
[![CI](https://github.com/mprpic/commit-editor/workflows/CI/badge.svg)](https://github.com/mprpic/commit-editor/actions)

An opinionated, terminal-based text editor for git commit messages, built
with [Textual](https://textual.textualize.io/).

- **Title length warning**: Characters beyond position 50 on the first line are highlighted in red
- **Auto-wrap body text**: Lines in the commit body (line 3+) are automatically wrapped at 72 characters (except for
  long strings that can't be wrapped, such as URLs)
- **White space**: Trailing white space is automatically stripped when a file is saved; an empty newline is inserted
  at the end of the file if not present.
- **Signed-off-by toggle**: Quickly add or remove a `Signed-off-by` trailer with a keyboard shortcut
- **Status bar**: Shows current cursor position (line/column) and title length with warnings

## Installation

```bash
# Using uv
uv tool install commit-editor

# Using pip
pip install commit-editor
```

### Requirements

- Python 3.11 or later
- Git (for Signed-off-by functionality)

## Usage

Configure `commit-editor` as your default git commit message editor:

```bash
git config --global core.editor commit-editor
```

When you run `git commit`, the editor will open automatically.

`commit-editor` can also be used as a standalone tool with:

```bash
commit-editor path/to/file.txt
```

## Keyboard Shortcuts

| Shortcut | Action                       |
|----------|------------------------------|
| `Ctrl+S` | Save the file                |
| `Ctrl+Q` | Quit                         |
| `Ctrl+O` | Toggle Signed-off-by trailer |

## Commit Message Format

This editor enforces the widely-accepted git commit message conventions:

1. **Title (line 1)**: Should be 50 characters or less; characters beyond 50 are highlighted in red as a warning.

2. **Blank line (line 2)**: Separates the title from the body.

3. **Body (line 3+)**: Should wrap at 72 characters; long lines are wrapped automatically as you type.

## License

MIT
