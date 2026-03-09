import re
import threading

from spellchecker import SpellChecker

WORD_PATTERN = re.compile(r"[a-zA-Z']+")


class SpellCheckCache:
    """Spellcheck cache with lazy background dictionary loading."""

    def __init__(self):
        self._spell: SpellChecker | None = None
        self._line_cache: dict[tuple[int, str], list[tuple[int, int]]] = {}
        self._suggestion_cache: dict[str, list[str]] = {}
        self._load_thread = threading.Thread(target=self._load_dictionary, daemon=True)
        self._load_thread.start()

    def _load_dictionary(self) -> None:
        self._spell = SpellChecker()

    def get_misspelled_spans(self, line_num: int, line_text: str) -> list[tuple[int, int]]:
        """Return (start_col, end_col) spans of misspelled words on a line."""
        if self._spell is None:
            return []

        key = (line_num, line_text)
        if key in self._line_cache:
            return self._line_cache[key]

        # Skip comment lines
        if line_text.lstrip().startswith("#"):
            self._line_cache[key] = []
            return []

        spans = []
        words_with_positions = []

        for match in WORD_PATTERN.finditer(line_text):
            raw_word = match.group()
            # Strip leading/trailing apostrophes
            stripped = raw_word.strip("'")
            if not stripped or len(stripped) == 1:
                continue

            # Calculate offset from stripping leading apostrophes
            leading = len(raw_word) - len(raw_word.lstrip("'"))
            start = match.start() + leading
            end = start + len(stripped)
            words_with_positions.append((stripped, start, end))

        if words_with_positions:
            just_words = [w for w, _, _ in words_with_positions]
            misspelled = self._spell.unknown(just_words)

            for word, start, end in words_with_positions:
                if word.lower() in misspelled:
                    spans.append((start, end))

        self._line_cache[key] = spans
        return spans

    def get_suggestions(self, word: str, max_count: int = 5) -> list[str]:
        """Return top spelling suggestions for a word."""
        if self._spell is None:
            return []

        cache_key = word.lower()
        if cache_key in self._suggestion_cache:
            return self._suggestion_cache[cache_key][:max_count]

        candidates = self._spell.candidates(word)
        if not candidates:
            self._suggestion_cache[cache_key] = []
            return []

        # Sort by word frequency, then alphabetically
        scored = []
        for candidate in candidates:
            frequency = self._spell.word_usage_frequency(candidate)
            scored.append((candidate, frequency))
        scored.sort(key=lambda x: (-x[1], x[0]))

        result = [c for c, _ in scored]
        self._suggestion_cache[cache_key] = result
        return result[:max_count]

    def invalidate_all(self) -> None:
        """Clear the entire line cache."""
        self._line_cache.clear()
