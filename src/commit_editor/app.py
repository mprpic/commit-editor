from collections.abc import Callable
from pathlib import Path

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.strip import Strip
from textual.widgets import Static, TextArea

from commit_editor.git import get_signed_off_by
from commit_editor.spelling import WORD_PATTERN, SpellCheckCache

TITLE_MAX_LENGTH = 50
BODY_MAX_LENGTH = 72
_SUGGESTION_PREFIX = "Suggestions for"


def wrap_line(line: str, width: int = 72) -> list[str]:
    """Wrap a single line at word boundaries to fit within width.

    Args:
        line: The line to wrap.
        width: Maximum line width (default 72).

    Returns:
        List of wrapped lines.
    """
    if not line:
        return [""]

    if len(line) <= width:
        return [line]

    words = line.split(" ")
    lines: list[str] = []
    current_line = ""

    for word in words:
        if not word:
            # Handle multiple spaces
            if current_line:
                current_line += " "
            continue

        # Check if word fits on current line
        test_line = f"{current_line} {word}".strip() if current_line else word
        if len(test_line) <= width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines if lines else [""]


class CommitTextArea(TextArea):
    """TextArea with commit-message-specific highlighting and behavior."""

    DEFAULT_CSS = """
    CommitTextArea {
        border: none;
        padding: 0;
    }
    CommitTextArea:focus {
        border: none;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_body_text = ""
        self._spell_cache = SpellCheckCache()
        self.spellcheck_enabled = True

    def render_line(self, y: int) -> Strip:
        """Render a line with custom highlighting for title overflow and misspelled words."""
        strip = super().render_line(y)
        lines = self.text.split("\n")

        # Highlight overflow on the first line (title)
        if y == 0 and lines:
            title = lines[0]
            if len(title) > TITLE_MAX_LENGTH:
                strip = self._apply_char_styles(
                    strip, title, Style(color="red", bold=True), lambda pos: pos >= TITLE_MAX_LENGTH
                )

        # Underline misspelled words
        if self.spellcheck_enabled and y < len(lines):
            line_text = lines[y]
            spans = self._spell_cache.get_misspelled_spans(y, line_text)
            if spans:
                styled_positions = set()
                for start, end in spans:
                    for i in range(start, end):
                        styled_positions.add(i)
                strip = self._apply_char_styles(
                    strip, line_text, Style(underline=True), lambda pos: pos in styled_positions
                )

        return strip

    @staticmethod
    def _apply_char_styles(
        strip: Strip,
        line_text: str,
        extra_style: Style,
        should_style: Callable[[int], bool],
    ) -> Strip:
        """Apply extra_style to characters where should_style(char_position) is True."""
        segments = list(strip)
        new_segments = []
        char_count = 0
        content_started = False

        for segment in segments:
            text = segment.text
            style = segment.style

            if not content_started:
                if text and line_text and text.strip() and line_text.startswith(text.strip()[:5]):
                    content_started = True

            if content_started and text:
                normal = ""
                styled = ""

                for char in text:
                    if should_style(char_count):
                        if normal:
                            new_segments.append(Segment(normal, style))
                            normal = ""
                        styled += char
                    else:
                        if styled:
                            combined = style + extra_style if style else extra_style
                            new_segments.append(Segment(styled, combined))
                            styled = ""
                        normal += char
                    char_count += 1

                if normal:
                    new_segments.append(Segment(normal, style))
                if styled:
                    combined = style + extra_style if style else extra_style
                    new_segments.append(Segment(styled, combined))
            else:
                new_segments.append(segment)

        return Strip(new_segments, strip.cell_length)

    def get_word_at_cursor(self) -> str | None:
        """Get the word at the current cursor position, or None."""
        if not self.spellcheck_enabled:
            return None

        row, col = self.cursor_location
        lines = self.text.split("\n")
        if row >= len(lines):
            return None

        line = lines[row]
        for match in WORD_PATTERN.finditer(line):
            if match.start() <= col <= match.end():
                word = match.group().strip("'")
                return word if word else None

        return None

    def wrap_current_body_line(self) -> None:
        """Wrap the current line if it's a body line (line 3+) and exceeds 72 chars."""
        cursor_row, cursor_col = self.cursor_location
        lines = self.text.split("\n")

        # Only wrap body lines (index 2+, which is line 3+ in 1-indexed)
        if cursor_row < 2 or cursor_row >= len(lines):
            return

        current_line = lines[cursor_row]

        # Only wrap if line exceeds the limit
        if len(current_line) <= BODY_MAX_LENGTH:
            return

        # Wrap the line
        wrapped = wrap_line(current_line, BODY_MAX_LENGTH)

        if len(wrapped) <= 1:
            return

        # Replace the current line with wrapped content
        lines[cursor_row : cursor_row + 1] = wrapped
        new_text = "\n".join(lines)

        # Calculate new cursor position
        # If cursor was beyond the wrap point, move to next line
        if cursor_col > len(wrapped[0]):
            new_row = cursor_row + 1
            new_col = cursor_col - len(wrapped[0]) - 1  # -1 for the space that became newline
            new_col = max(0, min(new_col, len(wrapped[1]) if len(wrapped) > 1 else 0))
        else:
            new_row = cursor_row
            new_col = cursor_col

        self.load_text(new_text)
        self.invalidate_spell_cache()
        self.cursor_location = (new_row, new_col)

    def invalidate_spell_cache(self) -> None:
        """Clear the spellcheck line cache."""
        self._spell_cache.invalidate_all()

    def get_misspelled_spans(self, row: int, line_text: str) -> list[tuple[int, int]]:
        """Return misspelled word spans for a line."""
        return self._spell_cache.get_misspelled_spans(row, line_text)

    def get_spell_suggestions(self, word: str) -> list[str]:
        """Return spelling suggestions for a word."""
        return self._spell_cache.get_suggestions(word)

    def get_title_length(self) -> int:
        """Get the length of the title (first line)."""
        lines = self.text.split("\n")
        return len(lines[0]) if lines else 0

    def get_cursor_position(self) -> tuple[int, int]:
        """Get the current cursor position (1-indexed line, 1-indexed column)."""
        row, col = self.cursor_location
        return row + 1, col + 1


class StatusBar(Static):
    """Status bar showing cursor position and title length."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }

    StatusBar .warning {
        color: $error;
    }
    """

    def update_status(self, line: int, col: int, title_length: int, dirty: bool) -> None:
        """Update the status bar content."""
        dirty_marker = " \\[modified]" if dirty else ""

        if title_length > TITLE_MAX_LENGTH:
            title_display = f"[bold red]Title: {title_length}[/bold red]"
        else:
            title_display = f"Title: {title_length}"

        left = f"Ln {line}, Col {col} | {title_display}{dirty_marker}"
        hints = "^S Save  ^Q Quit  ^O Sign-off  ^L Spellcheck"
        left_width = len(Text.from_markup(left).plain)
        # Account for padding on both sides
        gap = (self.size.width - 2) - left_width - len(hints)
        if gap >= 2:
            self.update(f"{left}{' ' * gap}[dim]{hints}[/dim]")
        else:
            self.update(left)


class MessageBar(Static):
    """Message bar for showing status messages and prompts."""

    DEFAULT_CSS = """
    MessageBar {
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
    }

    MessageBar.error {
        color: $error;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = ""

    def show_message(self, message: str, error: bool = False) -> None:
        """Show a status message."""
        self.message = message
        if error:
            self.add_class("error")
        else:
            self.remove_class("error")
        self.update(message)

    def show_prompt(self, message: str) -> None:
        """Show a prompt message."""
        self.message = message
        self.remove_class("error")
        self.update(message)

    def clear(self) -> None:
        """Clear the message bar content."""
        self.message = ""
        self.remove_class("error")
        self.update("")


class CommitEditorApp(App):
    """A terminal-based git commit message editor."""

    TITLE = "commit-editor"

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("ctrl+q", "quit_app", "Quit", show=True),
        Binding("ctrl+o", "toggle_signoff", "Sign-off", show=True),
        Binding("ctrl+l", "toggle_spellcheck", "Spellcheck", show=True),
    ]

    DEFAULT_CSS = """
    Screen {
        layout: vertical;
    }

    CommitTextArea {
        height: 1fr;
    }
    """

    def __init__(self, filename: Path):
        super().__init__()
        self.filename = filename
        self.dirty = False
        self._original_content = ""
        self._prompt_mode: str | None = None  # Track active prompt type
        self._spell_timer = None

    def compose(self) -> ComposeResult:
        yield CommitTextArea(id="editor", show_line_numbers=True, highlight_cursor_line=True)
        yield StatusBar(id="status")
        yield MessageBar(id="message")

    def on_mount(self) -> None:
        """Load file content on startup."""
        editor = self.query_one("#editor", CommitTextArea)

        content = self.filename.read_text()
        self._original_content = content
        editor.load_text(content)
        editor.invalidate_spell_cache()
        editor.focus()

        self._update_status_bar()

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        """Disable editor actions when in prompt mode."""
        if self._prompt_mode is not None:
            # Allow only prompt-related actions
            if action in ("confirm_quit", "discard_quit", "cancel_quit"):
                return True
            return False
        return True

    def action_confirm_quit(self) -> None:
        """Save and quit when prompted."""
        if self._prompt_mode == "quit_confirm":
            self._prompt_mode = None
            self.query_one("#message", MessageBar).clear()
            self.action_save()
            self.exit()

    def action_discard_quit(self) -> None:
        """Quit without saving when prompted."""
        if self._prompt_mode == "quit_confirm":
            self._prompt_mode = None
            self.query_one("#message", MessageBar).clear()
            self.exit()

    def action_cancel_quit(self) -> None:
        """Cancel quit when prompted."""
        if self._prompt_mode == "quit_confirm":
            self._prompt_mode = None
            self.query_one("#message", MessageBar).clear()
            editor = self.query_one("#editor", CommitTextArea)
            editor.read_only = False
            editor.focus()

    def on_key(self, event) -> None:
        """Handle key events for prompts."""
        if self._prompt_mode == "quit_confirm":
            if event.key == "y":
                event.prevent_default()
                event.stop()
                self.action_confirm_quit()
            elif event.key == "n":
                event.prevent_default()
                event.stop()
                self.action_discard_quit()
            elif event.key == "escape":
                event.prevent_default()
                event.stop()
                self.action_cancel_quit()

    @on(CommitTextArea.Changed)
    def on_editor_changed(self, event: CommitTextArea.Changed) -> None:
        """Handle text changes - update dirty state and wrap body lines."""
        editor = self.query_one("#editor", CommitTextArea)
        self.dirty = editor.text != self._original_content

        # Auto-wrap body lines
        editor.wrap_current_body_line()

        # Clear any message when user starts typing
        if self._prompt_mode is None:
            self.query_one("#message", MessageBar).clear()

        self._update_status_bar()

    @on(CommitTextArea.SelectionChanged)
    def on_selection_changed(self, event: CommitTextArea.SelectionChanged) -> None:
        """Update status bar on cursor movement."""
        self._update_status_bar()
        self._schedule_spell_suggestions()

    def _update_status_bar(self) -> None:
        """Update the status bar with current state."""
        editor = self.query_one("#editor", CommitTextArea)
        status = self.query_one("#status", StatusBar)

        line, col = editor.get_cursor_position()
        title_length = editor.get_title_length()

        status.update_status(line, col, title_length, self.dirty)

    def _show_message(self, message: str, error: bool = False) -> None:
        """Show a message in the message bar."""
        message_bar = self.query_one("#message", MessageBar)
        message_bar.show_message(message, error=error)

    def action_save(self) -> None:
        """Save the file."""
        editor = self.query_one("#editor", CommitTextArea)
        content = editor.text

        # Strip trailing whitespace from each line and ensure file ends with a newline
        lines = content.split("\n")
        content = "\n".join(line.rstrip() for line in lines)
        if not content.endswith("\n"):
            content += "\n"

        self.filename.write_text(content)
        self._original_content = content
        self.dirty = False

        self._update_status_bar()
        self._show_message(f"Saved {self.filename}")

    def action_quit_app(self) -> None:
        """Quit the application, prompting if there are unsaved changes."""
        if self.dirty:
            self._prompt_mode = "quit_confirm"
            # Disable editor to prevent key events from being consumed
            editor = self.query_one("#editor", CommitTextArea)
            editor.read_only = True
            message_bar = self.query_one("#message", MessageBar)
            message_bar.show_prompt("Save changes? (y/n/esc)")
        else:
            self.exit()

    def action_toggle_signoff(self) -> None:
        """Toggle the Signed-off-by line."""
        editor = self.query_one("#editor", CommitTextArea)
        text = editor.text
        lines = text.split("\n")

        signoff = get_signed_off_by()
        if not signoff:
            self._show_message("Git user not configured", error=True)
            return

        # Find where git comments start (lines starting with #)
        comment_start_index = len(lines)
        for i, line in enumerate(lines):
            if line.startswith("#"):
                comment_start_index = i
                break

        # Split into content and comments
        content_lines = lines[:comment_start_index]
        comment_lines = lines[comment_start_index:]

        # Remove trailing empty lines from content for clean processing
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()

        # Check if Signed-off-by already exists in content
        has_signoff = False
        signoff_index = -1

        for i in range(len(content_lines) - 1, -1, -1):
            line = content_lines[i]
            if line.startswith("Signed-off-by:"):
                has_signoff = True
                signoff_index = i
                break
            elif line.strip() and not line.startswith("#"):
                # Stop at first non-empty, non-comment, non-signoff line
                break

        if has_signoff:
            # Remove the Signed-off-by line
            del content_lines[signoff_index]
            # Remove trailing blank lines from content
            while content_lines and not content_lines[-1].strip():
                content_lines.pop()
        else:
            # Add Signed-off-by with blank line if needed
            if content_lines and content_lines[-1].strip():
                content_lines.append("")
            content_lines.append(signoff)

        # Reassemble: content + blank line (if comments exist) + comments
        if comment_lines:
            # Ensure blank line between content and comments
            new_text = "\n".join(content_lines) + "\n\n" + "\n".join(comment_lines)
        else:
            new_text = "\n".join(content_lines)
        cursor_pos = editor.cursor_location

        editor.load_text(new_text)
        editor.invalidate_spell_cache()

        # Restore cursor position if possible
        new_lines = new_text.split("\n")
        max_row = len(new_lines) - 1
        new_row = min(cursor_pos[0], max_row)
        max_col = len(new_lines[new_row]) if new_row < len(new_lines) else 0
        new_col = min(cursor_pos[1], max_col)
        editor.cursor_location = (new_row, new_col)

        self._update_status_bar()

    def action_toggle_spellcheck(self) -> None:
        """Toggle spellcheck on/off."""
        editor = self.query_one("#editor", CommitTextArea)
        editor.spellcheck_enabled = not editor.spellcheck_enabled
        message_bar = self.query_one("#message", MessageBar)

        if editor.spellcheck_enabled:
            message_bar.show_message("Spellcheck enabled")
        else:
            message_bar.show_message("Spellcheck disabled")

        # Force re-render to update underlines
        editor.refresh()

    def _schedule_spell_suggestions(self) -> None:
        """Debounce spell suggestion updates to avoid blocking during rapid cursor movement."""
        if self._spell_timer is not None:
            self._spell_timer.stop()
        self._spell_timer = self.set_timer(0.15, self._update_spell_suggestions)

    def _update_spell_suggestions(self) -> None:
        """Show spelling suggestions in MessageBar when cursor is on a misspelled word."""
        if self._prompt_mode is not None:
            return

        editor = self.query_one("#editor", CommitTextArea)
        message_bar = self.query_one("#message", MessageBar)

        if not editor.spellcheck_enabled:
            if message_bar.message.startswith(_SUGGESTION_PREFIX):
                message_bar.clear()
            return

        word = editor.get_word_at_cursor()
        if word:
            row, col = editor.cursor_location
            lines = editor.text.split("\n")
            if row < len(lines):
                spans = editor.get_misspelled_spans(row, lines[row])
                on_misspelled = any(start <= col < end for start, end in spans)
                if on_misspelled:
                    suggestions = editor.get_spell_suggestions(word)
                    if suggestions:
                        suggestion_text = ", ".join(suggestions)
                        message_bar.show_message(
                            f"{_SUGGESTION_PREFIX} '{word}': {suggestion_text}"
                        )
                        return

        # Clear only if currently showing a spell suggestion
        if message_bar.message.startswith(_SUGGESTION_PREFIX):
            message_bar.clear()
