from unittest.mock import patch

from commit_editor.git import get_signed_off_by, get_user_email, get_user_name


class TestGetUserName:
    """Tests for get_user_name function."""

    def test_successful_config_read(self):
        """Should return user name when git config succeeds."""
        with patch("commit_editor.git.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "John Doe\n"
            mock_run.return_value.returncode = 0

            result = get_user_name()
            assert result == "John Doe"

            mock_run.assert_called_once_with(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                check=True,
            )

    def test_missing_config(self):
        """Should return None when git config is not set."""
        with patch("commit_editor.git.subprocess.run") as mock_run:
            from subprocess import CalledProcessError

            mock_run.side_effect = CalledProcessError(1, "git config")

            result = get_user_name()
            assert result is None

    def test_git_not_found(self):
        """Should return None when git is not installed."""
        with patch("commit_editor.git.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = get_user_name()
            assert result is None

    def test_empty_config(self):
        """Should return None when git config returns empty string."""
        with patch("commit_editor.git.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "\n"
            mock_run.return_value.returncode = 0

            result = get_user_name()
            assert result is None


class TestGetUserEmail:
    """Tests for get_user_email function."""

    def test_successful_config_read(self):
        """Should return user email when git config succeeds."""
        with patch("commit_editor.git.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "john@example.com\n"
            mock_run.return_value.returncode = 0

            result = get_user_email()
            assert result == "john@example.com"

    def test_missing_config(self):
        """Should return None when git config is not set."""
        with patch("commit_editor.git.subprocess.run") as mock_run:
            from subprocess import CalledProcessError

            mock_run.side_effect = CalledProcessError(1, "git config")

            result = get_user_email()
            assert result is None


class TestGetSignedOffBy:
    """Tests for get_signed_off_by function."""

    def test_returns_formatted_line(self):
        """Should return properly formatted Signed-off-by line."""
        with (
            patch("commit_editor.git.get_user_name") as mock_name,
            patch("commit_editor.git.get_user_email") as mock_email,
        ):
            mock_name.return_value = "John Doe"
            mock_email.return_value = "john@example.com"

            result = get_signed_off_by()
            assert result == "Signed-off-by: John Doe <john@example.com>"

    def test_returns_none_when_name_missing(self):
        """Should return None when user name is not configured."""
        with (
            patch("commit_editor.git.get_user_name") as mock_name,
            patch("commit_editor.git.get_user_email") as mock_email,
        ):
            mock_name.return_value = None
            mock_email.return_value = "john@example.com"

            result = get_signed_off_by()
            assert result is None

    def test_returns_none_when_email_missing(self):
        """Should return None when user email is not configured."""
        with (
            patch("commit_editor.git.get_user_name") as mock_name,
            patch("commit_editor.git.get_user_email") as mock_email,
        ):
            mock_name.return_value = "John Doe"
            mock_email.return_value = None

            result = get_signed_off_by()
            assert result is None
