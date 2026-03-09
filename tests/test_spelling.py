from commit_editor.spelling import SpellCheckCache


def make_ready_cache() -> SpellCheckCache:
    """Create a SpellCheckCache and wait for it to be ready."""
    cache = SpellCheckCache()
    cache._load_thread.join()
    return cache


class TestGetMisspelledSpans:
    """Tests for SpellCheckCache.get_misspelled_spans."""

    def test_known_word_produces_no_spans(self):
        cache = make_ready_cache()
        spans = cache.get_misspelled_spans(0, "hello world")
        assert spans == []

    def test_misspelled_word_returns_span(self):
        cache = make_ready_cache()
        spans = cache.get_misspelled_spans(0, "helo world")
        assert len(spans) == 1
        start, end = spans[0]
        assert "helo world"[start:end] == "helo"

    def test_comment_lines_return_no_spans(self):
        cache = make_ready_cache()
        spans = cache.get_misspelled_spans(0, "# helo wrld")
        assert spans == []

    def test_punctuation_excluded_from_checked_words(self):
        cache = make_ready_cache()
        # "hello" and "world" are correct; punctuation should not affect checking
        spans = cache.get_misspelled_spans(0, "hello, world.")
        assert spans == []

    def test_contractions_not_flagged(self):
        cache = make_ready_cache()
        spans = cache.get_misspelled_spans(0, "don't it's won't")
        assert spans == []

    def test_cache_hit_for_same_text(self):
        cache = make_ready_cache()
        spans1 = cache.get_misspelled_spans(0, "helo world")
        spans2 = cache.get_misspelled_spans(0, "helo world")
        assert spans1 == spans2

    def test_cache_miss_for_changed_text(self):
        cache = make_ready_cache()
        spans1 = cache.get_misspelled_spans(0, "helo world")
        spans2 = cache.get_misspelled_spans(0, "hello world")
        assert spans1 != spans2


class TestGetSuggestions:
    """Tests for SpellCheckCache.get_suggestions."""

    def test_suggestions_for_misspelled_word(self):
        cache = make_ready_cache()
        suggestions = cache.get_suggestions("helo")
        assert len(suggestions) > 0
        assert "hello" in suggestions or "help" in suggestions or "hero" in suggestions

    def test_max_count_limits_results(self):
        cache = make_ready_cache()
        suggestions = cache.get_suggestions("helo", max_count=2)
        assert len(suggestions) <= 2


class TestInvalidateAll:
    """Tests for cache invalidation."""

    def test_invalidate_clears_cache(self):
        cache = make_ready_cache()
        cache.get_misspelled_spans(0, "helo world")
        assert len(cache._line_cache) > 0
        cache.invalidate_all()
        assert len(cache._line_cache) == 0
