"""Tests for the chegi hooks CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app
from chegi.services.hooks.exceptions import HookInstallError, HookRemoveError

runner = CliRunner()


class TestHooksCli:
    """Tests for the chegi hooks CLI command."""

    @patch("chegi.cli.commands.hooks.HooksService")
    def test_hooks_install_success(
        self, mock_service: MagicMock, tmp_path: Path
    ) -> None:
        """Test that chegi hooks install succeeds."""
        mock_service.return_value.install.return_value = (
            tmp_path / ".git" / "hooks" / "pre-commit"
        )

        result = runner.invoke(app, ["hooks", "install", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "installed" in result.stdout.lower()

    @patch("chegi.cli.commands.hooks.HooksService")
    def test_hooks_install_with_force(
        self, mock_service: MagicMock, tmp_path: Path
    ) -> None:
        """Test that chegi hooks install --force passes force flag."""
        mock_service.return_value.install.return_value = (
            tmp_path / ".git" / "hooks" / "pre-commit"
        )

        result = runner.invoke(
            app, ["hooks", "install", "--path", str(tmp_path), "--force"]
        )
        assert result.exit_code == 0
        mock_service.return_value.install.assert_called_once_with(force=True)

    @patch("chegi.cli.commands.hooks.HooksService")
    def test_hooks_install_failure(
        self, mock_service: MagicMock, tmp_path: Path
    ) -> None:
        """Test that chegi hooks install shows error on failure."""
        mock_service.return_value.install.side_effect = HookInstallError("Failed")

        result = runner.invoke(app, ["hooks", "install", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "Failed" in result.stdout

    @patch("chegi.cli.commands.hooks.HooksService")
    def test_hooks_remove_success(
        self, mock_service: MagicMock, tmp_path: Path
    ) -> None:
        """Test that chegi hooks remove succeeds."""
        mock_service.return_value.remove.return_value = True

        result = runner.invoke(app, ["hooks", "remove", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "removed" in result.stdout.lower()

    @patch("chegi.cli.commands.hooks.HooksService")
    def test_hooks_remove_no_hook(
        self, mock_service: MagicMock, tmp_path: Path
    ) -> None:
        """Test that chegi hooks remove shows message when no hook found."""
        mock_service.return_value.remove.return_value = False

        result = runner.invoke(app, ["hooks", "remove", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "no" in result.stdout.lower() or "not" in result.stdout.lower()

    @patch("chegi.cli.commands.hooks.HooksService")
    def test_hooks_remove_failure(
        self, mock_service: MagicMock, tmp_path: Path
    ) -> None:
        """Test that chegi hooks remove shows error on failure."""
        mock_service.return_value.remove.side_effect = HookRemoveError("Failed")

        result = runner.invoke(app, ["hooks", "remove", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "Failed" in result.stdout

    @patch("chegi.cli.commands.hooks.HooksService")
    def test_hooks_status_installed(
        self, mock_service: MagicMock, tmp_path: Path
    ) -> None:
        """Test that chegi hooks status shows installed."""
        mock_service.return_value.is_installed.return_value = MagicMock(
            installed=True, path=str(tmp_path / ".git" / "hooks" / "pre-commit")
        )
        result = runner.invoke(app, ["hooks", "status", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "installed" in result.stdout.lower()

    @patch("chegi.cli.commands.hooks.HooksService")
    def test_hooks_status_not_installed(
        self, mock_service: MagicMock, tmp_path: Path
    ) -> None:
        """Test that chegi hooks status shows not installed."""
        mock_service.return_value.is_installed.return_value = MagicMock(
            installed=False, path=None
        )
        result = runner.invoke(app, ["hooks", "status", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "not installed" in result.stdout.lower()

    def test_hooks_no_subcommand_shows_help(self) -> None:
        """Test that chegi hooks with no subcommand shows usage hint."""
        result = runner.invoke(app, ["hooks"])
        assert "install" in result.stdout
        assert "status" in result.stdout
        assert "remove" in result.stdout
