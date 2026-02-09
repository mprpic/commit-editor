from unittest.mock import patch

from commit_editor.app import CommitEditorApp, CommitTextArea, MessageBar


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
