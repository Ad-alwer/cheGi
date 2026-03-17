import pytest
from typer.testing import CliRunner
from unittest.mock import patch
from pathlib import Path

from chegi.cli import app
from chegi.git_utils import GitStatus

runner = CliRunner()

def test_scan_invalid_path():
    """
    Tests the CLI behavior when an invalid directory path is provided.

    Expects an exit code of 1 and a specific error message in the output.

    Args:
        None

    Returns:
        None
    """
    # Typer flattens single-command apps by default. 
    # Therefore, we pass the arguments directly without the "scan" keyword.
    result = runner.invoke(app, ["/non/existent/mock/path/12345"])
    
    assert result.exit_code == 1
    assert "Invalid path:" in result.stdout

@patch("chegi.cli.find_git_repos")
def test_scan_no_repos_found(mock_find_repos, tmp_path: Path):
    """
    Tests the CLI behavior when a valid directory contains no Git repositories.

    Expects a normal exit (code 0) and an informative message.

    Args:
        mock_find_repos (MagicMock): Mocked find_git_repos function.
        tmp_path (Path): Pytest fixture providing a temporary directory path.

    Returns:
        None
    """
    mock_find_repos.return_value = []
    
    result = runner.invoke(app, [str(tmp_path)])
    
    assert result.exit_code == 0
    assert "Scanning" in result.stdout

@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_with_repos(mock_find_repos, mock_analyze, tmp_path: Path):
    """
    Tests the successful execution of the CLI command with mocked repositories.

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
    
    result = runner.invoke(app, [str(tmp_path)])
    
    assert result.exit_code == 0
    assert "Scanning" in result.stdout
    assert "Analyzing 1 repositories" in result.stdout
    assert "mock_project" in result.stdout
    assert "feature-branch" in result.stdout
