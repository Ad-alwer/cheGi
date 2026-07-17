"""Tests for the CompletionsService class."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chegi.services.completions.completions_service import CompletionsService
from chegi.services.completions.exceptions import (
    InstallationError,
    UnsupportedShellError,
)


class TestCompletionsServiceGenerate:
    """Tests for CompletionsService.generate()."""

    def test_generate_bash_returns_script(self) -> None:
        """Test that generate('bash') returns a bash completion script."""
        script = CompletionsService().generate("bash")
        assert "_chegi_completion" in script
        assert "complete" in script
        assert "chegi" in script

    def test_generate_zsh_returns_script(self) -> None:
        """Test that generate('zsh') returns a zsh completion script."""
        script = CompletionsService().generate("zsh")
        assert "_chegi" in script
        assert "compdef" in script

    def test_generate_fish_returns_script(self) -> None:
        """Test that generate('fish') returns a fish completion script."""
        script = CompletionsService().generate("fish")
        assert "complete" in script
        assert "chegi" in script

    def test_generate_powershell_returns_script(self) -> None:
        """Test that generate('powershell') returns a powershell completion script."""
        script = CompletionsService().generate("powershell")
        assert "Register-ArgumentCompleter" in script
        assert "chegi" in script

    def test_generate_pwsh_returns_script(self) -> None:
        """Test that generate('pwsh') returns a powershell completion script."""
        script = CompletionsService().generate("pwsh")
        assert "Register-ArgumentCompleter" in script
        assert "chegi" in script

    def test_generate_unsupported_shell_raises_error(self) -> None:
        """Test that generate() raises UnsupportedShellError for unknown shells."""
        with pytest.raises(UnsupportedShellError) as exc_info:
            CompletionsService().generate("tcsh")
        assert "Unsupported shell" in str(exc_info.value)
        assert "tcsh" in str(exc_info.value)


class TestCompletionsServiceDetectShell:
    """Tests for CompletionsService.detect_shell()."""

    @patch("shellingham.detect_shell", return_value=("zsh", "/bin/zsh"))
    def test_detect_via_shellingham(self, mock_detect: MagicMock) -> None:
        """Test that detect_shell() uses shellingham when available."""
        result = CompletionsService.detect_shell()
        assert result == "zsh"

    @patch("shellingham.detect_shell", side_effect=Exception("not available"))
    def test_detect_falls_back_to_shell_env(self, mock_detect: MagicMock) -> None:
        """Test that detect_shell() falls back to $SHELL when shellingham fails."""
        with patch.dict(os.environ, {"SHELL": "/bin/fish"}, clear=True):
            result = CompletionsService.detect_shell()
            assert result == "fish"

    @patch("shellingham.detect_shell", side_effect=Exception("not available"))
    def test_detect_returns_none_when_no_shell(self, mock_detect: MagicMock) -> None:
        """Test that detect_shell() returns None when nothing is available."""
        with patch.dict(os.environ, {}, clear=True):
            result = CompletionsService.detect_shell()
            assert result is None


class TestCompletionsServiceInstall:
    """Tests for CompletionsService.install()."""

    def test_install_bash_writes_script(self, tmp_path: Path) -> None:
        """Test that install('bash') writes the completion script to the correct path."""
        install_path = tmp_path / "chegi"
        with patch(
            "chegi.services.completions.completions_service.INSTALL_PATHS",
            {"bash": install_path},
        ):
            service = CompletionsService()
            result_path = service.install("bash")
            assert result_path == install_path
            assert install_path.exists()
            content = install_path.read_text()
            assert "_chegi_completion" in content

    def test_install_unsupported_shell_raises_error(self) -> None:
        """Test that install() raises UnsupportedShellError for powershell/pwsh."""
        service = CompletionsService()
        with pytest.raises(UnsupportedShellError) as exc_info:
            service.install("powershell")
        assert "Auto-install is not supported" in str(exc_info.value)

    def test_install_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that install() creates parent directories if they don't exist."""
        nested = tmp_path / "a" / "b" / "chegi"
        with patch(
            "chegi.services.completions.completions_service.INSTALL_PATHS",
            {"bash": nested},
        ):
            service = CompletionsService()
            path = service.install("bash")
            assert path.parent.exists()
            assert path.exists()

    def test_install_raises_on_write_error(self) -> None:
        """Test that install() raises InstallationError when write fails."""
        path = Path("/nonexistent/readonly/chegi")
        with patch(
            "chegi.services.completions.completions_service.INSTALL_PATHS",
            {"bash": path},
        ):
            service = CompletionsService()
            with pytest.raises(InstallationError):
                service.install("bash")
