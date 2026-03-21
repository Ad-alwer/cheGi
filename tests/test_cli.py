import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path

from chegi.cli import app
from chegi.git_utils import GitStatus


runner = CliRunner()

def test_scan_invalid_path():
    """Tests the CLI behavior when an invalid directory path is provided.

    Expects an exit code of 1 and a specific error message gracefully 
    caught from NotADirectoryError.

    Args:
        None

    Returns:
        None
    """
    # Now we must explicitly call the "scan" subcommand
    result = runner.invoke(app, ["scan", "/non/existent/mock/path/12345"])
    
    assert result.exit_code == 1
    # Check if the error caught from scanner.py is displayed
    assert "does not exist" in result.stdout.lower()

@patch("chegi.cli.find_git_repos")
def test_scan_no_repos_found(mock_find_repos: MagicMock, tmp_path: Path):
    """Tests the CLI behavior when a valid directory contains no Git repositories.

    Expects a normal exit (code 0) and an informative scanning message.

    Args:
        mock_find_repos (MagicMock): Mocked find_git_repos function.
        tmp_path (Path): Pytest fixture providing a temporary directory path.

    Returns:
        None
    """
    mock_find_repos.return_value = []
    
    result = runner.invoke(app, ["scan", str(tmp_path)])
    
    assert result.exit_code == 0
    assert "Scanning" in result.stdout

@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_with_repos(mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path):
    """Tests the successful execution of the CLI scan command with mocked repositories.

    Ensures that the output contains the correct parsing stages and repository data.

    Args:
        mock_find_repos (MagicMock): Mocked find_git_repos function.
        mock_analyze (MagicMock): Mocked GitAnalyzer.analyze_concurrently method.
        tmp_path (Path): Pytest fixture providing a temporary directory path.

    Returns:
        None
    """
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
    """Tests listing current configuration settings via CLI.

    Args:
        tmp_path (Path): Pytest fixture providing a temporary directory.

    Returns:
        None
    """
    result = runner.invoke(app, ["config", "list", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Current Configuration" in result.stdout
    assert "Max Depth" in result.stdout

def test_config_set(tmp_path: Path):
    """Tests setting a new configuration value via CLI.

    Args:
        tmp_path (Path): Pytest fixture providing a temporary directory.

    Returns:
        None
    """
    result = runner.invoke(app, ["config", "set", "max_depth", "5", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Successfully updated max_depth to 5" in result.stdout

def test_config_exclude_add_remove(tmp_path: Path):
    """Tests adding and removing items from the exclude list via CLI.

    Ensures the add and remove commands output the correct success messages.

    Args:
        tmp_path (Path): Pytest fixture providing a temporary directory.

    Returns:
        None
    """
    # Test Adding
    res_add = runner.invoke(app, ["config", "exclude-add", "my_junk_folder", "--path", str(tmp_path)])
    assert res_add.exit_code == 0
    assert "Added 'my_junk_folder'" in res_add.stdout

    # Test Removing
    res_rem = runner.invoke(app, ["config", "exclude-remove", "my_junk_folder", "--path", str(tmp_path)])
    assert res_rem.exit_code == 0
    assert "Removed 'my_junk_folder'" in res_rem.stdout


@patch("chegi.cli.check_git_environment")
def test_cli_global_setup_git_failure(mock_check_git):
    """Tests that the CLI exits before running commands if Git validation fails.

    Args:
        mock_check_git (MagicMock): Mocked check_git_environment function.
    """
    mock_check_git.return_value = (False, "Git version is too old: 2.10.0")
    
    result = runner.invoke(app, ["scan"])
    
    assert result.exit_code == 1
    assert "Git version is too old" in result.stdout