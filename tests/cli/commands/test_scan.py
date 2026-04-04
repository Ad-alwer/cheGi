from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app
from chegi.git_utils import GitStatus

runner = CliRunner()


# ==========================================
# Scan Command Tests
# ==========================================

def test_scan_invalid_path():
    """Tests the CLI behavior when an invalid directory path is provided."""
    result = runner.invoke(app, ["scan", "/non/existent/mock/path/12345"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout.lower()


@patch("chegi.services.scanner.scan_service.GitAnalyzer.analyze_concurrently")
@patch("chegi.services.scanner.scan_service.find_git_repos")
def test_scan_with_repos(
    mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path
):
    """Tests successful scan execution and UI output."""
    mock_find_repos.return_value = [tmp_path]
    mock_status = GitStatus(
        path=tmp_path,
        repo_name="mock_project",
        branch="main",
        is_dirty=True,
        has_staged_files=False,
        has_remote=True,
    )
    mock_analyze.return_value = [mock_status]

    result = runner.invoke(app, ["scan", str(tmp_path)])

    assert result.exit_code == 0
    assert "Scanning" in result.stdout
    assert "mock_project" in result.stdout


@patch("chegi.services.scanner.scan_service.GitAnalyzer.analyze_concurrently")
@patch("chegi.services.scanner.scan_service.find_git_repos")
def test_scan_filter_dirty(
    mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path
):
    """Tests the --dirty flag to ensure clean repositories are filtered out."""
    mock_find_repos.return_value = [Path("/repo1"), Path("/repo2")]

    dirty_repo = GitStatus(
        Path("/repo1"),
        "dirty_repo",
        "main",
        is_dirty=True,
        has_staged_files=False,
        has_remote=True,
    )
    clean_repo = GitStatus(
        Path("/repo2"),
        "clean_repo",
        "main",
        is_dirty=False,
        has_staged_files=False,
        has_remote=True,
    )

    mock_analyze.return_value = [dirty_repo, clean_repo]

    result = runner.invoke(app, ["scan", "--dirty", str(tmp_path)])

    assert "dirty_repo" in result.stdout
    assert "clean_repo" not in result.stdout


@patch("chegi.services.scanner.scan_service.GitAnalyzer.analyze_concurrently")
@patch("chegi.services.scanner.scan_service.find_git_repos")
def test_scan_filter_staged(
    mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path
):
    """Tests the --staged flag to ensure only repos with staged files are shown."""
    mock_find_repos.return_value = [Path("/repo1"), Path("/repo2")]

    staged_repo = GitStatus(
        Path("/repo1"),
        "staged_repo",
        "main",
        is_dirty=True,
        has_staged_files=True,
        has_remote=True,
    )
    unstaged_repo = GitStatus(
        Path("/repo2"),
        "unstaged_repo",
        "main",
        is_dirty=True,
        has_staged_files=False,
        has_remote=True,
    )

    mock_analyze.return_value = [staged_repo, unstaged_repo]

    result = runner.invoke(app, ["scan", "--staged", str(tmp_path)])

    assert "staged_repo" in result.stdout
    assert "unstaged_repo" not in result.stdout


@patch("chegi.services.scanner.scan_service.GitAnalyzer.analyze_concurrently")
@patch("chegi.services.scanner.scan_service.find_git_repos")
def test_scan_with_security_flag(
    mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path
):
    """Tests if --security flag correctly triggers the security scanner."""
    mock_find_repos.return_value = [tmp_path]
    
    # The 7th argument represents the security status (e.g. "[green]Safe[/green]")
    mock_status = GitStatus(
        tmp_path, "mock_project", "main", False, False, True, "[green]Safe[/green]"
    )
    mock_analyze.return_value = [mock_status]

    result = runner.invoke(app, ["scan", "--security", str(tmp_path)])

    assert result.exit_code == 0
    mock_analyze.assert_called_once()
    
    # Verify that the security scanner was passed to the analyzer
    assert "security_scanner" in mock_analyze.call_args.kwargs
