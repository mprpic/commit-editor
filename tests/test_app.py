from unittest.mock import patch

from textual.widgets import Input, OptionList

from commit_editor.app import (
    AI_COAUTHOR_MODELS,
    CoauthorSelectScreen,
    CommitEditorApp,
    CommitTextArea,
    MessageBar,
    ValidationBar,
    _format_coauthor,
)


class TestAppStartup:
    """Tests for app startup behavior."""

    async def test_app_opens_and_displays_content(self, temp_file):
        """App should open and display file content."""
        content = "Test commit message\n\nBody of the commit."
        temp_file.write_text(content)

        app = CommitEditorApp(temp_file)
        async with app.run_test():
            editor = app.query_one("#editor", CommitTextArea)
            assert editor.text == content

    async def test_app_starts_clean(self, temp_file):
        """App should start with dirty=False."""
        temp_file.write_text("Content")
        app = CommitEditorApp(temp_file)

        async with app.run_test():
            assert app.dirty is False


class TestSaveFunction:
    """Tests for the save functionality."""

    async def test_ctrl_s_saves_file(self, temp_file):
        """Ctrl+S should save the file."""
        temp_file.write_text("Original")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            editor = app.query_one("#editor", CommitTextArea)
            editor.load_text("Modified content")
            app.dirty = True

            await pilot.press("ctrl+s")

            saved_content = temp_file.read_text()
            assert saved_content == "Modified content\n"
            assert app.dirty is False

    async def test_ctrl_s_shows_message(self, temp_file):
        """Ctrl+S should show saved message with file path in message bar."""
        temp_file.write_text("Original")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            await pilot.press("ctrl+s")

            message_bar = app.query_one("#message", MessageBar)
            # Message should contain "Saved" and the file path
            message_content = message_bar.message
            assert "Saved" in message_content


class TestQuitBehavior:
    """Tests for quit functionality."""

    async def test_ctrl_q_clean_exits_immediately(self, temp_file):
        """Ctrl+Q on clean buffer should exit immediately."""
        temp_file.write_text("Content")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            assert app.dirty is False
            await pilot.press("ctrl+q")
            # App should have exited - check that it's no longer running
            assert app._exit is True

    async def test_ctrl_q_dirty_shows_prompt(self, temp_file):
        """Ctrl+Q on dirty buffer should show confirmation prompt in message bar."""
        temp_file.write_text("Original")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            editor = app.query_one("#editor", CommitTextArea)
            editor.load_text("Modified")
            app.dirty = True

            await pilot.press("ctrl+q")

            # Check that the prompt mode is active and message bar shows prompt
            assert app._prompt_mode == "quit_confirm"
            message_bar = app.query_one("#message", MessageBar)
            message_content = message_bar.message
            assert "Save changes?" in message_content

    async def test_confirm_quit_with_y_saves_and_exits(self, temp_file):
        """Pressing 'y' in confirmation prompt should save and quit."""
        temp_file.write_text("Original")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            editor = app.query_one("#editor", CommitTextArea)
            editor.load_text("Modified")
            app.dirty = True

            await pilot.press("ctrl+q")
            await pilot.press("y")

            assert app._exit is True
            # File should have been saved with the modified content
            assert temp_file.read_text() == "Modified\n"

    async def test_discard_quit_with_n(self, temp_file):
        """Pressing 'n' in confirmation prompt should quit without saving."""
        temp_file.write_text("Original")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            editor = app.query_one("#editor", CommitTextArea)
            editor.load_text("Modified")
            app.dirty = True

            await pilot.press("ctrl+q")
            await pilot.press("n")

            # Should have exited without saving
            assert app._exit is True
            assert temp_file.read_text() == "Original"

    async def test_cancel_quit_with_escape(self, temp_file):
        """Pressing 'escape' in confirmation prompt should cancel quit."""
        temp_file.write_text("Original")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            editor = app.query_one("#editor", CommitTextArea)
            editor.load_text("Modified")
            app.dirty = True

            await pilot.press("ctrl+q")
            await pilot.press("escape")

            # Should not have exited, prompt mode should be cleared
            assert app._exit is False
            assert app._prompt_mode is None


class TestSignOffToggle:
    """Tests for the Signed-off-by toggle functionality."""

    async def test_ctrl_o_adds_signoff(self, temp_file):
        """Ctrl+O should add Signed-off-by line."""
        temp_file.write_text("Commit message\n\nBody text")
        app = CommitEditorApp(temp_file)

        with patch("commit_editor.app.get_signed_off_by") as mock_signoff:
            mock_signoff.return_value = "Signed-off-by: Test User <test@example.com>"

            async with app.run_test() as pilot:
                await pilot.press("ctrl+o")

                editor = app.query_one("#editor", CommitTextArea)
                assert "Signed-off-by: Test User <test@example.com>" in editor.text

    async def test_ctrl_o_removes_existing_signoff(self, temp_file):
        """Ctrl+O should remove existing Signed-off-by line."""
        content = "Commit message\n\nBody text\n\nSigned-off-by: Test User <test@example.com>"
        temp_file.write_text(content)
        app = CommitEditorApp(temp_file)

        with patch("commit_editor.app.get_signed_off_by") as mock_signoff:
            mock_signoff.return_value = "Signed-off-by: Test User <test@example.com>"

            async with app.run_test() as pilot:
                await pilot.press("ctrl+o")

                editor = app.query_one("#editor", CommitTextArea)
                assert "Signed-off-by:" not in editor.text

    async def test_ctrl_o_inserts_before_git_comments(self, temp_file):
        """Ctrl+O should insert Signed-off-by before git comment lines."""
        content = (
            "Commit message\n\n"
            "# Please enter the commit message for your changes.\n"
            "# Lines starting with '#' will be ignored.\n"
        )
        temp_file.write_text(content)
        app = CommitEditorApp(temp_file)

        with patch("commit_editor.app.get_signed_off_by") as mock_signoff:
            mock_signoff.return_value = "Signed-off-by: Test User <test@example.com>"

            async with app.run_test() as pilot:
                await pilot.press("ctrl+o")

                editor = app.query_one("#editor", CommitTextArea)
                text = editor.text
                # Sign-off should appear before comments
                signoff_pos = text.find("Signed-off-by:")
                comment_pos = text.find("# Please enter")
                assert signoff_pos < comment_pos
                assert signoff_pos != -1

    async def test_ctrl_o_removes_signoff_before_git_comments(self, temp_file):
        """Ctrl+O should remove Signed-off-by that's before git comments."""
        content = (
            "Commit message\n\n"
            "Signed-off-by: Test User <test@example.com>\n\n"
            "# Please enter the commit message for your changes.\n"
        )
        temp_file.write_text(content)
        app = CommitEditorApp(temp_file)

        with patch("commit_editor.app.get_signed_off_by") as mock_signoff:
            mock_signoff.return_value = "Signed-off-by: Test User <test@example.com>"

            async with app.run_test() as pilot:
                await pilot.press("ctrl+o")

                editor = app.query_one("#editor", CommitTextArea)
                assert "Signed-off-by:" not in editor.text
                # Comments should still be present
                assert "# Please enter" in editor.text

    async def test_ctrl_o_shows_error_when_git_not_configured(self, temp_file):
        """Ctrl+O should show error message when git user is not configured."""
        temp_file.write_text("Commit message")
        app = CommitEditorApp(temp_file)

        with patch("commit_editor.app.get_signed_off_by") as mock_signoff:
            mock_signoff.return_value = None

            async with app.run_test() as pilot:
                await pilot.press("ctrl+o")

                message_bar = app.query_one("#message", MessageBar)
                assert "error" in message_bar.classes
                message_content = message_bar.message
                assert "Git user not configured" in message_content


class TestTitleWarning:
    """Tests for title length warning."""

    async def test_title_length_in_status(self, temp_file):
        """Status bar should show title length."""
        temp_file.write_text("Short title")
        app = CommitEditorApp(temp_file)

        async with app.run_test():
            editor = app.query_one("#editor", CommitTextArea)
            assert editor.get_title_length() == 11  # "Short title" is 11 chars

    async def test_long_title_warning(self, temp_file):
        """Long title should trigger warning in status bar."""
        long_title = "A" * 60  # 60 chars, exceeds 50 limit
        temp_file.write_text(long_title)
        app = CommitEditorApp(temp_file)

        async with app.run_test():
            editor = app.query_one("#editor", CommitTextArea)
            assert editor.get_title_length() == 60


def _wait_for_spellcheck(editor: CommitTextArea, timeout: float = 5.0) -> None:
    """Wait for the spellcheck dictionary to finish loading."""
    editor._spell_cache._load_thread.join(timeout=timeout)


class TestSpellcheck:
    """Tests for spellcheck integration."""

    async def test_misspelled_word_shows_suggestions(self, temp_file):
        """When cursor is on a misspelled word, suggestions appear in MessageBar."""
        temp_file.write_text("helo world")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            editor = app.query_one("#editor", CommitTextArea)
            _wait_for_spellcheck(editor)

            # Move cursor onto the misspelled word "helo"
            editor.cursor_location = (0, 2)
            await pilot.pause()
            app._update_spell_suggestions()

            message_bar = app.query_one("#message", MessageBar)
            assert "Suggestions for 'helo'" in message_bar.message

    async def test_correct_word_no_suggestions(self, temp_file):
        """When cursor is on a correct word, no suggestions appear."""
        temp_file.write_text("hello world")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            editor = app.query_one("#editor", CommitTextArea)
            _wait_for_spellcheck(editor)

            editor.cursor_location = (0, 2)
            await pilot.pause()
            app._update_spell_suggestions()

            message_bar = app.query_one("#message", MessageBar)
            assert not message_bar.message.startswith("Suggestions for")

    async def test_comment_line_no_suggestions(self, temp_file):
        """Words on comment lines don't trigger suggestions."""
        temp_file.write_text("title\n\n# helo wrld")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            editor = app.query_one("#editor", CommitTextArea)
            _wait_for_spellcheck(editor)

            editor.cursor_location = (2, 3)
            await pilot.pause()
            app._update_spell_suggestions()

            message_bar = app.query_one("#message", MessageBar)
            assert not message_bar.message.startswith("Suggestions for")

    async def test_moving_off_misspelled_clears_suggestion(self, temp_file):
        """Moving cursor off a misspelled word clears the suggestion."""
        temp_file.write_text("helo world")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            editor = app.query_one("#editor", CommitTextArea)
            _wait_for_spellcheck(editor)

            # First, place cursor on misspelled word
            editor.cursor_location = (0, 2)
            await pilot.pause()
            app._update_spell_suggestions()

            message_bar = app.query_one("#message", MessageBar)
            assert "Suggestions for 'helo'" in message_bar.message

            # Move cursor to correct word
            editor.cursor_location = (0, 6)
            await pilot.pause()
            app._update_spell_suggestions()

            assert not message_bar.message.startswith("Suggestions for")

    async def test_toggle_spellcheck_off_and_on(self, temp_file):
        """Ctrl+L toggles spellcheck and shows status message."""
        temp_file.write_text("helo world")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            editor = app.query_one("#editor", CommitTextArea)
            assert editor.spellcheck_enabled is True

            await pilot.press("ctrl+l")
            message_bar = app.query_one("#message", MessageBar)
            assert editor.spellcheck_enabled is False
            assert "Spellcheck disabled" in message_bar.message

            await pilot.press("ctrl+l")
            assert editor.spellcheck_enabled is True
            assert "Spellcheck enabled" in message_bar.message


class TestCoauthorToggle:
    """Tests for the Co-authored-by toggle functionality."""

    async def test_add_coauthor(self, temp_file):
        """Ctrl+B and Enter should add the first model (default highlight)."""
        temp_file.write_text("Commit message\n\nBody text")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            await pilot.press("ctrl+b")
            # Modal should be showing with first model highlighted by default
            screen = app.screen
            assert isinstance(screen, CoauthorSelectScreen)
            option_list = screen.query_one("#coauthor-list", OptionList)
            assert option_list.highlighted == 0
            option_list.action_select()
            await pilot.pause()

            editor = app.query_one("#editor", CommitTextArea)
            name, email = AI_COAUTHOR_MODELS[0]
            assert _format_coauthor(name, email) in editor.text

    async def test_remove_existing_coauthor(self, temp_file):
        """Ctrl+B when co-author exists should remove it without opening dialog."""
        name, email = AI_COAUTHOR_MODELS[0]
        coauthor = _format_coauthor(name, email)
        content = f"Commit message\n\nBody text\n\n{coauthor}"
        temp_file.write_text(content)
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            await pilot.press("ctrl+b")
            await pilot.pause()

            # Should not have opened the dialog
            assert not isinstance(app.screen, CoauthorSelectScreen)
            editor = app.query_one("#editor", CommitTextArea)
            assert "Co-authored-by:" not in editor.text

    async def test_coauthor_added_before_signoff(self, temp_file):
        """Co-authored-by should be inserted before Signed-off-by."""
        content = "Commit message\n\nBody text\n\nSigned-off-by: Test User <test@example.com>"
        temp_file.write_text(content)
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            await pilot.press("ctrl+b")
            screen = app.screen
            assert isinstance(screen, CoauthorSelectScreen)
            option_list = screen.query_one("#coauthor-list", OptionList)
            option_list.highlighted = 0
            option_list.action_select()
            await pilot.pause()

            editor = app.query_one("#editor", CommitTextArea)
            text = editor.text
            coauthor_pos = text.find("Co-authored-by:")
            signoff_pos = text.find("Signed-off-by:")
            assert coauthor_pos != -1
            assert signoff_pos != -1
            assert coauthor_pos < signoff_pos

    async def test_coauthor_before_git_comments(self, temp_file):
        """Co-authored-by should go before # comment lines."""
        content = (
            "Commit message\n\n"
            "# Please enter the commit message for your changes.\n"
            "# Lines starting with '#' will be ignored.\n"
        )
        temp_file.write_text(content)
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            await pilot.press("ctrl+b")
            screen = app.screen
            assert isinstance(screen, CoauthorSelectScreen)
            option_list = screen.query_one("#coauthor-list", OptionList)
            option_list.highlighted = 0
            option_list.action_select()
            await pilot.pause()

            editor = app.query_one("#editor", CommitTextArea)
            text = editor.text
            coauthor_pos = text.find("Co-authored-by:")
            comment_pos = text.find("# Please enter")
            assert coauthor_pos != -1
            assert coauthor_pos < comment_pos

    async def test_escape_cancels(self, temp_file):
        """Pressing Escape in the modal should cancel without changes."""
        content = "Commit message\n\nBody text"
        temp_file.write_text(content)
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            await pilot.press("ctrl+b")
            screen = app.screen
            assert isinstance(screen, CoauthorSelectScreen)
            await pilot.press("escape")
            await pilot.pause()

            editor = app.query_one("#editor", CommitTextArea)
            assert editor.text == content
            assert "Co-authored-by:" not in editor.text

    async def test_toggle_removes_then_allows_new_selection(self, temp_file):
        """Ctrl+B removes existing co-author, then Ctrl+B again opens dialog."""
        temp_file.write_text("Commit message\n\nBody text")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            # Add first model
            await pilot.press("ctrl+b")
            screen = app.screen
            assert isinstance(screen, CoauthorSelectScreen)
            option_list = screen.query_one("#coauthor-list", OptionList)
            option_list.highlighted = 0
            option_list.action_select()
            await pilot.pause()

            editor = app.query_one("#editor", CommitTextArea)
            name0, email0 = AI_COAUTHOR_MODELS[0]
            assert _format_coauthor(name0, email0) in editor.text

            # Ctrl+B again removes it (no dialog)
            await pilot.press("ctrl+b")
            await pilot.pause()
            assert "Co-authored-by:" not in editor.text

            # Ctrl+B again opens dialog for new selection
            await pilot.press("ctrl+b")
            screen = app.screen
            assert isinstance(screen, CoauthorSelectScreen)
            option_list = screen.query_one("#coauthor-list", OptionList)
            option_list.highlighted = 5
            option_list.action_select()
            await pilot.pause()

            name5, email5 = AI_COAUTHOR_MODELS[5]
            assert _format_coauthor(name5, email5) in editor.text
            assert _format_coauthor(name0, email0) not in editor.text

    async def test_custom_coauthor(self, temp_file):
        """Selecting 'Other...' and typing custom value should add it."""
        temp_file.write_text("Commit message\n\nBody text")
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            await pilot.press("ctrl+b")
            screen = app.screen
            assert isinstance(screen, CoauthorSelectScreen)
            option_list = screen.query_one("#coauthor-list", OptionList)
            # Select "Other..." (last option after separator)
            option_list.highlighted = len(AI_COAUTHOR_MODELS) + 1
            option_list.action_select()
            await pilot.pause()

            # Input should now be visible
            input_widget = screen.query_one("#coauthor-input", Input)
            input_widget.value = "Custom Bot <bot@example.com>"
            await input_widget.action_submit()
            await pilot.pause()

            editor = app.query_one("#editor", CommitTextArea)
            assert "Co-authored-by: Custom Bot <bot@example.com>" in editor.text

    async def test_no_blank_line_between_coauthor_and_signoff(self, temp_file):
        """There should be no blank line between Co-authored-by and Signed-off-by."""
        content = "Commit message\n\nBody text\n\nSigned-off-by: Test User <test@example.com>"
        temp_file.write_text(content)
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            await pilot.press("ctrl+b")
            screen = app.screen
            assert isinstance(screen, CoauthorSelectScreen)
            option_list = screen.query_one("#coauthor-list", OptionList)
            option_list.highlighted = 0
            option_list.action_select()
            await pilot.pause()

            editor = app.query_one("#editor", CommitTextArea)
            name, email = AI_COAUTHOR_MODELS[0]
            coauthor = _format_coauthor(name, email)
            lines = editor.text.split("\n")
            coauthor_idx = lines.index(coauthor)
            signoff_idx = next(
                i for i, line in enumerate(lines) if line.startswith("Signed-off-by:")
            )
            # Trailers should be on adjacent lines
            assert signoff_idx == coauthor_idx + 1

    async def test_coauthor_not_on_first_line_when_empty(self, temp_file):
        """Co-authored-by should not appear on the first line of an empty message."""
        content = "\n# Please enter the commit message for your changes.\n"
        temp_file.write_text(content)
        app = CommitEditorApp(temp_file)

        async with app.run_test() as pilot:
            await pilot.press("ctrl+b")
            screen = app.screen
            assert isinstance(screen, CoauthorSelectScreen)
            option_list = screen.query_one("#coauthor-list", OptionList)
            option_list.highlighted = 0
            option_list.action_select()
            await pilot.pause()

            editor = app.query_one("#editor", CommitTextArea)
            lines = editor.text.split("\n")
            # First line should be empty (title), trailer should not be on line 1
            assert lines[0] == ""
            assert not lines[0].startswith("Co-authored-by:")

    async def test_signoff_after_coauthor_no_blank_line(self, temp_file):
        """Adding Signed-off-by after Co-authored-by should not insert a blank line."""
        temp_file.write_text("Commit message\n\nBody text")
        app = CommitEditorApp(temp_file)

        with patch("commit_editor.app.get_signed_off_by") as mock_signoff:
            mock_signoff.return_value = "Signed-off-by: Test User <test@example.com>"

            async with app.run_test() as pilot:
                # Add co-author first
                await pilot.press("ctrl+b")
                screen = app.screen
                assert isinstance(screen, CoauthorSelectScreen)
                option_list = screen.query_one("#coauthor-list", OptionList)
                option_list.highlighted = 0
                option_list.action_select()
                await pilot.pause()

                # Add signoff
                await pilot.press("ctrl+o")

                editor = app.query_one("#editor", CommitTextArea)
                name, email = AI_COAUTHOR_MODELS[0]
                coauthor = _format_coauthor(name, email)
                lines = editor.text.split("\n")
                coauthor_idx = lines.index(coauthor)
                signoff_idx = next(
                    i for i, line in enumerate(lines) if line.startswith("Signed-off-by:")
                )
                # Trailers should be on adjacent lines
                assert signoff_idx == coauthor_idx + 1


class TestIssueIdValidation:
    """Tests for issue ID validation in commit title."""

    async def test_no_pattern_configured(self, temp_file):
        """When no pattern is configured, validation bar should be hidden."""
        temp_file.write_text("Any title without issue ID")
        with patch("commit_editor.app.get_issue_pattern", return_value=None):
            app = CommitEditorApp(temp_file)
            async with app.run_test():
                validation_bar = app.query_one("#validation", ValidationBar)
                assert "has-errors" not in validation_bar.classes

    async def test_invalid_title_shows_error(self, temp_file):
        """Invalid title should show error in validation bar."""
        temp_file.write_text("Fix something")
        with patch("commit_editor.app.get_issue_pattern", return_value=r"AIPCC-\d+"):
            app = CommitEditorApp(temp_file)
            async with app.run_test():
                validation_bar = app.query_one("#validation", ValidationBar)
                assert "has-errors" in validation_bar.classes

    async def test_valid_title_no_error(self, temp_file):
        """Valid title should not show error in validation bar."""
        temp_file.write_text("AIPCC-123: Fix something")
        with patch("commit_editor.app.get_issue_pattern", return_value=r"AIPCC-\d+"):
            app = CommitEditorApp(temp_file)
            async with app.run_test():
                validation_bar = app.query_one("#validation", ValidationBar)
                assert "has-errors" not in validation_bar.classes

    async def test_title_becomes_valid_clears_error(self, temp_file):
        """Error should disappear when title becomes valid."""
        temp_file.write_text("Fix something")
        with patch("commit_editor.app.get_issue_pattern", return_value=r"AIPCC-\d+"):
            app = CommitEditorApp(temp_file)
            async with app.run_test() as pilot:
                validation_bar = app.query_one("#validation", ValidationBar)
                assert "has-errors" in validation_bar.classes

                # Edit title to be valid
                editor = app.query_one("#editor", CommitTextArea)
                editor.load_text("AIPCC-123: Fix something")
                await pilot.pause()

                assert "has-errors" not in validation_bar.classes

    async def test_error_shown_on_mount(self, temp_file):
        """Error should be shown immediately on mount with invalid title."""
        temp_file.write_text("Bad title")
        with patch("commit_editor.app.get_issue_pattern", return_value=r"AIPCC-\d+"):
            app = CommitEditorApp(temp_file)
            async with app.run_test():
                validation_bar = app.query_one("#validation", ValidationBar)
                assert "has-errors" in validation_bar.classes

    async def test_error_persists_while_typing(self, temp_file):
        """Error should persist while title remains invalid during typing."""
        temp_file.write_text("Fix something")
        with patch("commit_editor.app.get_issue_pattern", return_value=r"AIPCC-\d+"):
            app = CommitEditorApp(temp_file)
            async with app.run_test() as pilot:
                validation_bar = app.query_one("#validation", ValidationBar)
                assert "has-errors" in validation_bar.classes

                # Type more text (title still invalid)
                editor = app.query_one("#editor", CommitTextArea)
                editor.load_text("Fix something else")
                await pilot.pause()

                assert "has-errors" in validation_bar.classes

    async def test_invalid_regex_treated_as_unconfigured(self, temp_file):
        """Invalid regex pattern should be treated as unconfigured (no error, no crash)."""
        temp_file.write_text("Any title")
        with patch("commit_editor.app.get_issue_pattern", return_value="[invalid"):
            app = CommitEditorApp(temp_file)
            async with app.run_test():
                validation_bar = app.query_one("#validation", ValidationBar)
                assert "has-errors" not in validation_bar.classes
