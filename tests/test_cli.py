import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path

from chegi.cli import app
from chegi.git_utils import GitStatus

runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_valid_git_env():
    """Automatically mocks the Git environment check to pass for all tests.
    
    This ensures that standard tests (like 'scan' or 'config') are not 
    blocked by the global_setup environment check. Specific tests can 
    override this behavior by modifying the yielded mock object.
    """
    with patch("chegi.cli.check_git_environment") as mock_check:
        mock_check.return_value = (True, "")
        yield mock_check


# ==========================================
# Global Setup & Installation Prompt Tests
# ==========================================

def test_global_setup_git_failure_abort(mock_valid_git_env, tmp_path: Path):
    """Tests if the CLI gracefully exits when the user aborts Git installation."""
    # Simulate Git check failure
    mock_valid_git_env.return_value = (False, "Git version is too old: 2.10.0")
    
    # input="n\n" simulates the user typing 'n' and hitting Enter
    result = runner.invoke(app, ["scan", str(tmp_path)], input="n\n")
    
    assert result.exit_code == 1
    assert "Environment Check Failed" in result.stdout
    assert "Installation aborted" in result.stdout


@patch("chegi.cli.SystemInstaller.install_package")
def test_global_setup_git_install_success(mock_install: MagicMock, mock_valid_git_env, tmp_path: Path):
    """Tests successful automatic installation flow when Git is missing."""
    mock_valid_git_env.return_value = (False, "Git is missing")
    mock_install.return_value = True  # Simulate successful installation
    
    # input="y\n" simulates the user agreeing to install
    result = runner.invoke(app, ["scan", str(tmp_path)], input="y\n")
    
    assert result.exit_code == 0
    assert "Starting installation process" in result.stdout
    assert "Success! Git has been installed" in result.stdout
    assert "Please restart your terminal" in result.stdout
    mock_install.assert_called_once_with("git")


@patch("chegi.cli.SystemInstaller.install_package")
def test_global_setup_git_install_fail(mock_install: MagicMock, mock_valid_git_env, tmp_path: Path):
    """Tests the failure flow when the automatic Git installation fails."""
    mock_valid_git_env.return_value = (False, "Git is missing")
    mock_install.return_value = False  # Simulate failed installation
    
    # User agrees, but installation fails
    result = runner.invoke(app, ["scan", str(tmp_path)], input="y\n")
    
    assert result.exit_code == 1
    assert "Starting installation process" in result.stdout
    assert "Failed to install Git automatically" in result.stdout
    mock_install.assert_called_once_with("git")


# ==========================================
# Standard Command Tests (scan, config, etc.)
# ==========================================

def test_scan_invalid_path():
    """Tests the CLI behavior when an invalid directory path is provided."""
    result = runner.invoke(app, ["scan", "/non/existent/mock/path/12345"])
    
    assert result.exit_code == 1
    assert "does not exist" in result.stdout.lower()


@patch("chegi.cli.find_git_repos")
def test_scan_no_repos_found(mock_find_repos: MagicMock, tmp_path: Path):
    """Tests the CLI behavior when a valid directory contains no Git repositories."""
    mock_find_repos.return_value = []
    
    result = runner.invoke(app, ["scan", str(tmp_path)])
    
    assert result.exit_code == 0
    assert "Scanning" in result.stdout


@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_with_repos(mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path):
    """Tests the successful execution of the CLI scan command with mocked repositories."""
    mock_find_repos.return_value = [tmp_path]
    
    mock_status = GitStatus(
        path=tmp_path,
        repo_name="mock_project",
        branch="feature-branch",
        is_dirty=True,
        has_remote=True
    )
    mock_analyze.return_value = [mock_status]
    
    result = runner.invoke(app, ["scan", str(tmp_path)])
    
    assert result.exit_code == 0
    assert "Scanning" in result.stdout
    assert "Analyzing 1 repositories" in result.stdout
    assert "mock_project" in result.stdout
    assert "feature-branch" in result.stdout


def test_config_list(tmp_path: Path):
    """Tests listing current configuration settings via CLI."""
    result = runner.invoke(app, ["config", "list", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Current Configuration" in result.stdout
    assert "Max Depth" in result.stdout


def test_config_set(tmp_path: Path):
    """Tests setting a new configuration value via CLI."""
    result = runner.invoke(app, ["config", "set", "max_depth", "5", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Successfully updated 'max_depth' to 5" in result.stdout


def test_config_exclude_add_remove(tmp_path: Path):
    """Tests adding and removing items from the exclude list via CLI."""
    # Test Adding
    res_add = runner.invoke(app, ["config", "exclude-add", "my_junk_folder", "--path", str(tmp_path)])
    assert res_add.exit_code == 0
    assert "Added 'my_junk_folder'" in res_add.stdout

    # Test Removing
    res_rem = runner.invoke(app, ["config", "exclude-remove", "my_junk_folder", "--path", str(tmp_path)])
    assert res_rem.exit_code == 0
    assert "Removed 'my_junk_folder'" in res_rem.stdout
