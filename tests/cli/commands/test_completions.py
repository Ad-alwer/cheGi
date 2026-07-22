"""Tests for the chegi completions CLI command."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app

runner = CliRunner()


class TestCompletionsCliDirect:
    """Tests for 'chegi completions <shell>' direct mode."""

    def test_completions_bash(self) -> None:
        """Test that 'chegi completions bash' outputs a bash completion script."""
        result = runner.invoke(app, ["completions", "bash"])
        assert result.exit_code == 0
        assert "_chegi_completion" in result.stdout
        assert "complete" in result.stdout

    def test_completions_zsh(self) -> None:
        """Test that 'chegi completions zsh' outputs a zsh completion script."""
        result = runner.invoke(app, ["completions", "zsh"])
        assert result.exit_code == 0
        assert "_chegi" in result.stdout
        assert "compdef" in result.stdout

    def test_completions_fish(self) -> None:
        """Test that 'chegi completions fish' outputs a fish completion script."""
        result = runner.invoke(app, ["completions", "fish"])
        assert result.exit_code == 0
        assert "complete" in result.stdout
        assert "chegi" in result.stdout

    def test_completions_powershell(self) -> None:
        """Test that 'chegi completions powershell' outputs a powershell script."""
        result = runner.invoke(app, ["completions", "powershell"])
        assert result.exit_code == 0
        assert "Register-ArgumentCompleter" in result.stdout
        assert "chegi" in result.stdout

    def test_completions_pwsh(self) -> None:
        """Test that 'chegi completions pwsh' outputs a powershell script."""
        result = runner.invoke(app, ["completions", "pwsh"])
        assert result.exit_code == 0
        assert "Register-ArgumentCompleter" in result.stdout
        assert "chegi" in result.stdout

    def test_completions_invalid_shell(self) -> None:
        """Test that an unsupported shell produces a non-zero exit code."""
        result = runner.invoke(app, ["completions", "tcsh"])
        assert result.exit_code == 1
        assert "Unsupported shell" in result.stdout


class TestCompletionsCliInteractive:
    """Tests for 'chegi completions' interactive mode."""

    @patch("questionary.select")
    @patch("shellingham.detect_shell", return_value=("bash", "/bin/bash"))
    def test_interactive_cancel(self, mock_detect, mock_select: MagicMock) -> None:
        """Test that cancelling in interactive mode exits cleanly."""
        mock_select.return_value.ask.return_value = "cancel"
        result = runner.invoke(app, ["completions"])
        assert result.exit_code == 0

    @patch("questionary.select")
    @patch("shellingham.detect_shell", return_value=("bash", "/bin/bash"))
    def test_interactive_show_script(self, mock_detect, mock_select: MagicMock) -> None:
        """Test that 'Show completion script' prints to stdout."""
        mock_select.return_value.ask.side_effect = ["show", "bash"]
        result = runner.invoke(app, ["completions"])
        assert result.exit_code == 0
        assert "_chegi_completion" in result.stdout

    @patch("questionary.select")
    @patch("shellingham.detect_shell", return_value=("bash", "/bin/bash"))
    def test_interactive_install(
        self, mock_detect, mock_select: MagicMock, tmp_path: Path
    ) -> None:
        """Test that 'Install for bash' writes the script and reports success."""
        install_path = tmp_path / "chegi-completion"
        mock_select.return_value.ask.return_value = "install"
        with patch(
            "chegi.services.completions.completions_service.INSTALL_PATHS",
            {"bash": install_path},
        ):
            result = runner.invoke(app, ["completions"])
        assert result.exit_code == 0
        assert "installed" in result.stdout
        assert install_path.exists()

    @patch("questionary.select")
    @patch("shellingham.detect_shell", side_effect=OSError("no shell"))
    def test_interactive_undetected_shell(
        self, mock_detect, mock_select: MagicMock
    ) -> None:
        """Test that interactive mode works when shell cannot be detected."""
        mock_select.return_value.ask.side_effect = ["show", "bash"]
        result = runner.invoke(app, ["completions"])
        assert result.exit_code == 0
        assert "_chegi_completion" in result.stdout


class TestCompletionsCliInstallFlag:
    """Tests for 'chegi completions --install / -i' flag."""

    @patch("shellingham.detect_shell", return_value=("bash", "/bin/bash"))
    def test_install_flag_detects_and_installs(
        self, mock_detect, tmp_path: Path
    ) -> None:
        """Test that '--install' detects shell and installs without prompts."""
        install_path = tmp_path / "chegi-completion"
        with patch(
            "chegi.services.completions.completions_service.INSTALL_PATHS",
            {"bash": install_path},
        ):
            result = runner.invoke(app, ["completions", "--install"])
        assert result.exit_code == 0
        assert "installed" in result.stdout
        assert install_path.exists()

    def test_install_flag_with_shell(self, tmp_path: Path) -> None:
        """Test that '--install bash' installs bash directly."""
        install_path = tmp_path / "chegi-completion"
        with patch(
            "chegi.services.completions.completions_service.INSTALL_PATHS",
            {"bash": install_path},
        ):
            result = runner.invoke(app, ["completions", "--install", "bash"])
        assert result.exit_code == 0
        assert "installed" in result.stdout
        assert install_path.exists()

    @patch.dict(os.environ, {}, clear=True)
    @patch("shellingham.detect_shell", side_effect=OSError("no shell"))
    def test_install_flag_undetectable(self, mock_detect) -> None:
        """Test that '--install' fails gracefully when shell is undetectable."""
        result = runner.invoke(app, ["completions", "--install"])
        assert result.exit_code == 1
        assert "Could not detect your shell" in result.stdout
