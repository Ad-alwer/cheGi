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
    
    This ensures that standard tests (like 'scan', 'config', or 'guard') are not 
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
    mock_valid_git_env.return_value = (False, "Git version is too old: 2.10.0")
    
    result = runner.invoke(app, ["scan", str(tmp_path)], input="n\n")
    
    assert result.exit_code == 1
    assert "Environment Check Failed" in result.stdout
    assert "Installation aborted" in result.stdout


@patch("chegi.cli.SystemInstaller.install_package")
def test_global_setup_git_install_success(mock_install: MagicMock, mock_valid_git_env, tmp_path: Path):
    """Tests successful automatic installation flow when Git is missing."""
    mock_valid_git_env.return_value = (False, "Git is missing")
    mock_install.return_value = True
    
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
    mock_install.return_value = False
    
    result = runner.invoke(app, ["scan", str(tmp_path)], input="y\n")
    
    assert result.exit_code == 1
    assert "Starting installation process" in result.stdout
    assert "Failed to install Git automatically" in result.stdout
    mock_install.assert_called_once_with("git")


# ==========================================
# Standard Command Tests (scan)
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


# ==========================================
# Guard Command Tests
# ==========================================

@patch("chegi.cli.SecurityGuard.find_sensitive_files")
@patch("chegi.cli.SecurityGuard.get_staged_files")
def test_guard_success_no_secrets(mock_get_staged: MagicMock, mock_find_sensitive: MagicMock):
    """Tests the guard command when no sensitive data is found in staged files."""
    mock_get_staged.return_value = ["clean_code.py"]
    mock_find_sensitive.return_value = []
    
    result = runner.invoke(app, ["guard"])
    
    assert result.exit_code == 0
    mock_get_staged.assert_called_once()
    mock_find_sensitive.assert_called_once_with(["clean_code.py"])


@patch("chegi.cli.SecurityGuard.unstage_files")
@patch("chegi.cli.SecurityGuard.find_sensitive_files")
@patch("chegi.cli.SecurityGuard.get_staged_files")
def test_guard_failure_secrets_found_accept_unstage(mock_get_staged: MagicMock, mock_find_sensitive: MagicMock, mock_unstage: MagicMock):
    """Tests guard command when sensitive files are found and user chooses to unstage them automatically."""
    mock_get_staged.return_value = [".env"]
    mock_find_sensitive.return_value = [".env"]
    mock_unstage.return_value = True
    
    result = runner.invoke(app, ["guard"], input="y\n")
    
    assert result.exit_code == 1
    assert "WARNING: Sensitive files detected" in result.stdout
    assert "Files successfully unstaged" in result.stdout
    mock_get_staged.assert_called_once()
    mock_find_sensitive.assert_called_once_with([".env"])
    mock_unstage.assert_called_once_with([".env"])


@patch("chegi.cli.SecurityGuard.unstage_files")
@patch("chegi.cli.SecurityGuard.find_sensitive_files")
@patch("chegi.cli.SecurityGuard.get_staged_files")
def test_guard_failure_secrets_found_decline_unstage(mock_get_staged: MagicMock, mock_find_sensitive: MagicMock, mock_unstage: MagicMock):
    """Tests guard command when sensitive files are found but user declines automatic unstaging."""
    mock_get_staged.return_value = [".env"]
    mock_find_sensitive.return_value = [".env"]
    
    result = runner.invoke(app, ["guard"], input="n\n")
    
    assert result.exit_code == 1
    mock_unstage.assert_not_called()

# ==========================================
# Configuration Command Tests
# ==========================================

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
    res_remove = runner.invoke(app, ["config", "exclude-remove", "my_junk_folder", "--path", str(tmp_path)])
    assert res_remove.exit_code == 0
    assert "Removed 'my_junk_folder'" in res_remove.stdout
