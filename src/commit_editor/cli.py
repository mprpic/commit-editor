import argparse
import sys
from pathlib import Path


def main() -> int:
    """Main entry point for the commit-editor CLI."""
    parser = argparse.ArgumentParser(
        prog="commit-editor",
        description="A terminal-based git commit message editor with opinionated formatting",
    )
    parser.add_argument(
        "filename",
        type=Path,
        help="Path to the file to edit",
    )

    args = parser.parse_args()

    if not args.filename.exists():
        print(f"Error: File not found: {args.filename}", file=sys.stderr)
        return 1

    from commit_editor.app import CommitEditorApp

    app = CommitEditorApp(args.filename)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
