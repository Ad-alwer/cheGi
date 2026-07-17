"""Tests for the chegi info CLI command."""

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app

runner = CliRunner()


class TestInfoCli:
    """Tests for the info CLI command."""

    def test_info_not_a_git_repo(self) -> None:
        """Test that 'chegi info' outside a git repo exits with error."""
        with patch("chegi.services.info.info_service.GitClient") as mock_cls:
            mock_git = MagicMock()
            mock_git.is_valid_repo.return_value = False
            mock_cls.return_value = mock_git
            result = runner.invoke(app, ["info", "--path", "/tmp"])
        assert result.exit_code == 1
        assert "Not a git repository" in result.stdout

    def test_info_directory_not_exists(self) -> None:
        """Test that 'chegi info --path /nonexistent' shows error."""
        result = runner.invoke(app, ["info", "--path", "/nonexistent_dir_42"])
        assert result.exit_code == 1
        assert "Directory does not exist" in result.stdout

    def test_info_dashboard_renders(self) -> None:
        """Test that 'chegi info' renders a dashboard with branch name."""
        with patch("chegi.services.info.info_service.GitClient") as mock_cls:
            mock_git = MagicMock()
            mock_git.is_valid_repo.return_value = True
            _setup_mock_git(mock_git)
            mock_cls.return_value = mock_git
            result = runner.invoke(app, ["info", "--path", "/tmp"])
        assert result.exit_code == 0
        assert "cheGi Info" in result.stdout
        assert "main" in result.stdout

    def test_info_json_output(self) -> None:
        """Test that 'chegi info --json' outputs valid JSON."""
        with patch("chegi.services.info.info_service.GitClient") as mock_cls:
            mock_git = MagicMock()
            mock_git.is_valid_repo.return_value = True
            _setup_mock_git(mock_git)
            mock_cls.return_value = mock_git
            result = runner.invoke(app, ["info", "--json", "--path", "/tmp"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["is_git_repo"] is True
        assert data["branch"] == "main"

    def test_info_short_output(self) -> None:
        """Test that 'chegi info --short' outputs a one-liner."""
        with patch("chegi.services.info.info_service.GitClient") as mock_cls:
            mock_git = MagicMock()
            mock_git.is_valid_repo.return_value = True
            _setup_mock_git(mock_git)
            mock_cls.return_value = mock_git
            result = runner.invoke(app, ["info", "--short", "--path", "/tmp"])
        assert result.exit_code == 0
        assert "main" in result.stdout

    def test_info_json_not_git(self) -> None:
        """Test that 'chegi info --json' outside git shows non-repo."""
        with patch("chegi.services.info.info_service.GitClient") as mock_cls:
            mock_git = MagicMock()
            mock_git.is_valid_repo.return_value = False
            mock_cls.return_value = mock_git
            result = runner.invoke(app, ["info", "--json", "--path", "/tmp"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["is_git_repo"] is False


def _setup_mock_git(mock_git: MagicMock) -> None:
    """Configures a mock GitClient with clean repo outputs.

    Args:
        mock_git: The mock GitClient instance.
    """

    def run_command_side_effect(cmd, check=True, **kwargs):
        cmd_str = " ".join(cmd)
        if "status --porcelain" in cmd_str:
            return ""
        if "rev-list --left-right" in cmd_str:
            return "0\t0"
        if "remote" in cmd_str and "get-url" in cmd_str:
            return "git@github.com:user/repo.git"
        if cmd == ["git", "remote"]:
            return "origin"
        if "branch --show-current" in cmd_str:
            return "main"
        if "config user.name" in cmd_str:
            return "Ali"
        if "config user.email" in cmd_str:
            return "ali@example.com"
        if "stash list" in cmd_str:
            return ""
        if "log" in cmd_str and "-1" in cmd_str:
            return "abc1234\nAli\n2 hours ago\nfix: typo"
        if "shortlog" in cmd_str:
            return "     5\tAli\n     3\tSara\n     1\tReza"
        if "describe" in cmd_str:
            from chegi.services.git.exceptions import GitCommandError

            raise GitCommandError(cmd, 128, "fatal: no tags")
        return ""

    mock_git.run_command.side_effect = run_command_side_effect
