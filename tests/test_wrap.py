"""Tests for the wrap_line function."""

from commit_editor.app import wrap_line


class TestWrapLine:
    """Tests for wrap_line function."""

    def test_short_line_no_wrap(self):
        """Short lines should not be wrapped."""
        line = "This is a short line"
        result = wrap_line(line, 72)
        assert result == ["This is a short line"]

    def test_empty_input(self):
        """Empty input should return empty string in list."""
        assert wrap_line("", 72) == [""]

    def test_exact_length(self):
        """Line at exactly max length should not be wrapped."""
        line = "a" * 72
        result = wrap_line(line, 72)
        assert result == [line]

    def test_wrap_at_word_boundary(self):
        """Long lines should wrap at word boundaries."""
        line = "The quick brown fox jumps over the lazy dog and continues running"
        result = wrap_line(line, 40)
        assert len(result) == 2
        assert all(len(r) <= 40 for r in result)
        assert result[0] == "The quick brown fox jumps over the lazy"
        assert result[1] == "dog and continues running"

    def test_very_long_word(self):
        """Very long words (e.g. URLs) should not be broken."""
        line = "a" * 100
        result = wrap_line(line, 72)
        assert result == ["a" * 100]

    def test_long_word_with_surrounding_text(self):
        """A long word should be placed on its own line without breaking."""
        url = "https://example.com/" + "a" * 80
        line = f"See {url} for details"
        result = wrap_line(line, 72)
        assert result == ["See", url, "for details"]

    def test_multiple_wraps(self):
        """Very long lines should wrap multiple times."""
        words = ["word"] * 30
        line = " ".join(words)
        result = wrap_line(line, 20)
        assert len(result) > 1
        assert all(len(r) <= 20 for r in result)
