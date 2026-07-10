from unittest.mock import MagicMock, patch

import pytest
import typer

from chegi.cli.core.checks.git_check import GitRequirementCheck


@pytest.fixture
def git_check() -> GitRequirementCheck:
    """Returns a fresh instance of GitRequirementCheck for testing."""
    return GitRequirementCheck()


@patch("chegi.cli.core.checks.git_check.shutil.which")
@patch("chegi.cli.core.checks.git_check.SystemInstaller")
def test_git_already_installed(
    mock_installer_class: MagicMock,
    mock_which: MagicMock,
    git_check: GitRequirementCheck,
):
    """Tests behavior when Git is already installed."""
    mock_which.return_value = "/usr/bin/git"

    git_check.execute()

    mock_which.assert_called_once_with("git")
    mock_installer_class.install_package.assert_not_called()


@patch("chegi.cli.core.checks.git_check.typer.confirm")
@patch("chegi.cli.core.checks.git_check.shutil.which")
@patch("chegi.cli.core.checks.git_check.SystemInstaller")
def test_git_not_installed_but_install_succeeds(
    mock_installer_class: MagicMock,
    mock_which: MagicMock,
    mock_confirm: MagicMock,
    git_check: GitRequirementCheck,
):
    """Tests behavior when Git is missing but the auto-installer succeeds."""
    mock_which.return_value = None
    mock_confirm.return_value = True
    mock_installer_class.install_package.return_value = True

    with pytest.raises(typer.Exit) as exc_info:
        git_check.execute()

    assert exc_info.value.exit_code == 0
    mock_which.assert_called_once_with("git")
    mock_confirm.assert_called_once()
    mock_installer_class.install_package.assert_called_once_with("git")


@patch("chegi.cli.core.checks.git_check.typer.confirm")
@patch("chegi.cli.core.checks.git_check.shutil.which")
@patch("chegi.cli.core.checks.git_check.SystemInstaller")
def test_git_not_installed_and_install_fails(
    mock_installer_class: MagicMock,
    mock_which: MagicMock,
    mock_confirm: MagicMock,
    git_check: GitRequirementCheck,
):
    """Tests that typer.Exit(1) is raised if Git is missing and installation fails."""
    mock_which.return_value = None
    mock_confirm.return_value = True
    mock_installer_class.install_package.return_value = False

    with pytest.raises(typer.Exit) as exc_info:
        git_check.execute()

    assert exc_info.value.exit_code == 1
    mock_which.assert_called_once_with("git")
    mock_confirm.assert_called_once()
    mock_installer_class.install_package.assert_called_once_with("git")
