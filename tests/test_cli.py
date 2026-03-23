import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path
from chegi.cli import app
from chegi.git_utils import GitStatus

# Initialize the CLI Runner for testing
runner = CliRunner()

@pytest.fixture(autouse=True)
def mock_valid_git_env():
    """Automatically mocks the Git environment check to pass for all tests."""
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
    mock_install.assert_called_once_with("git")

# ==========================================
# Scan Command Tests
# ==========================================

def test_scan_invalid_path():
    """Tests the CLI behavior when an invalid directory path is provided."""
    result = runner.invoke(app, ["scan", "/non/existent/mock/path/12345"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout.lower()

@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_with_repos(mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path):
    """Tests successful scan execution and UI output."""
    mock_find_repos.return_value = [tmp_path]
    mock_status = GitStatus(
        path=tmp_path,
        repo_name="mock_project",
        branch="main",
        is_dirty=True,
        has_staged_files=False,
        has_remote=True
    )
    mock_analyze.return_value = [mock_status]
    
    result = runner.invoke(app, ["scan", str(tmp_path)])
    
    assert result.exit_code == 0
    assert "Scanning" in result.stdout
    assert "mock_project" in result.stdout

@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_filter_dirty(mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path):
    """Tests the --dirty flag to ensure clean repositories are filtered out."""
    mock_find_repos.return_value = [Path("/repo1"), Path("/repo2")]
    
    dirty_repo = GitStatus(Path("/repo1"), "dirty_repo", "main", is_dirty=True, has_staged_files=False, has_remote=True)
    clean_repo = GitStatus(Path("/repo2"), "clean_repo", "main", is_dirty=False, has_staged_files=False, has_remote=True)
    
    mock_analyze.return_value = [dirty_repo, clean_repo]
    
    result = runner.invoke(app, ["scan", "--dirty", str(tmp_path)])
    
    assert "dirty_repo" in result.stdout
    assert "clean_repo" not in result.stdout

@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_filter_staged(mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path):
    """Tests the --staged flag to ensure only repos with staged files are shown."""
    mock_find_repos.return_value = [Path("/repo1"), Path("/repo2")]
    
    staged_repo = GitStatus(Path("/repo1"), "staged_repo", "main", is_dirty=True, has_staged_files=True, has_remote=True)
    unstaged_repo = GitStatus(Path("/repo2"), "unstaged_repo", "main", is_dirty=True, has_staged_files=False, has_remote=True)
    
    mock_analyze.return_value = [staged_repo, unstaged_repo]
    
    result = runner.invoke(app, ["scan", "--staged", str(tmp_path)])
    
    assert "staged_repo" in result.stdout
    assert "unstaged_repo" not in result.stdout

@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_with_security_flag(mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path):
    """Tests if --security flag correctly triggers the security scanner."""
    mock_find_repos.return_value = [tmp_path]
    mock_status = GitStatus(tmp_path, "mock_project", "main", False, False, True, "[green]Safe[/green]")
    mock_analyze.return_value = [mock_status]
    
    result = runner.invoke(app, ["scan", "--security", str(tmp_path)])
    
    assert result.exit_code == 0
    mock_analyze.assert_called_once()
    assert "security_scanner" in mock_analyze.call_args.kwargs

# ==========================================
# Guard Command Tests
# ==========================================

@patch("chegi.cli.SecurityGuard.find_sensitive_files")
@patch("chegi.cli.SecurityGuard.get_staged_files")
def test_guard_success_no_secrets(mock_get_staged: MagicMock, mock_find_sensitive: MagicMock):
    """Tests guard command when no sensitive files are detected."""
    mock_get_staged.return_value = ["clean.py"]
    mock_find_sensitive.return_value = []
    
    result = runner.invoke(app, ["guard"])
    assert result.exit_code == 0

@patch("chegi.cli.SecurityGuard.unstage_files")
@patch("chegi.cli.SecurityGuard.find_sensitive_files")
@patch("chegi.cli.SecurityGuard.get_staged_files")
def test_guard_failure_secrets_found_accept_unstage(mock_get, mock_find, mock_unstage):
    """Tests guard behavior when secrets are found and user accepts unstaging."""
    mock_get.return_value = [".env"]
    mock_find.return_value = [".env"]
    mock_unstage.return_value = True
    
    result = runner.invoke(app, ["guard"], input="y\n")
    
    assert result.exit_code == 1
    assert "WARNING: Sensitive files detected" in result.stdout
    assert "Files successfully unstaged" in result.stdout

# ==========================================
# Configuration Command Tests
# ==========================================

def test_config_list(tmp_path: Path):
    """Tests listing configuration settings."""
    result = runner.invoke(app, ["config", "list", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Max Depth" in result.stdout

def test_config_set(tmp_path: Path):
    """Tests updating a configuration value."""
    result = runner.invoke(app, ["config", "set", "max_depth", "5", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Successfully updated 'max_depth' to 5" in result.stdout

def test_config_exclude_add_remove(tmp_path: Path):
    """Tests adding and then removing an item from the exclude list."""
    runner.invoke(app, ["config", "exclude-add", "junk", "--path", str(tmp_path)])
    res_remove = runner.invoke(app, ["config", "exclude-remove", "junk", "--path", str(tmp_path)])
    assert res_remove.exit_code == 0
    assert "Removed 'junk'" in res_remove.stdout

# ==========================================
# Gitignore Command Tests
# ==========================================

@patch("chegi.cli.questionary.select")
@patch("chegi.cli.subprocess.run")
def test_gitignore_success_without_commit(mock_subprocess, mock_select, tmp_path: Path):
    """Tests successful .gitignore creation but user declines commit.

    Args:
        mock_subprocess (MagicMock): Mock for subprocess.run.
        mock_select (MagicMock): Mock for questionary.select.
        tmp_path (Path): Pytest fixture for temporary directory path.
    """
    mock_subprocess.return_value = MagicMock(returncode=0)
    mock_select.return_value.ask.return_value = "Python"
    
    result = runner.invoke(app, ["gitignore", "--path", str(tmp_path)], input="n\n")
    
    assert result.exit_code == 0
    assert "Created:" in result.stdout
    assert "Skipping commit." in result.stdout
    assert (tmp_path / ".gitignore").exists()


@patch("chegi.cli.questionary.select")
@patch("chegi.cli.subprocess.run")
def test_gitignore_success_with_commit(mock_subprocess, mock_select, tmp_path: Path):
    """Tests .gitignore creation with user accepting the automatic commit.

    Args:
        mock_subprocess (MagicMock): Mock for subprocess.run.
        mock_select (MagicMock): Mock for questionary.select.
        tmp_path (Path): Pytest fixture for temporary directory path.
    """
    mock_subprocess.return_value = MagicMock(returncode=0)
    mock_select.return_value.ask.return_value = "Python"
    
    result = runner.invoke(app, ["gitignore", "--path", str(tmp_path)], input="y\n")
    
    assert result.exit_code == 0
    assert "Committed with message:" in result.stdout
    assert mock_subprocess.call_count >= 3 


@patch("chegi.cli.questionary.select")
@patch("chegi.cli.subprocess.run")
def test_gitignore_overwrite_abort(mock_subprocess, mock_select, tmp_path: Path):
    """Tests that the command asks before overwriting and aborts if declined.

    Args:
        mock_subprocess (MagicMock): Mock for subprocess.run.
        mock_select (MagicMock): Mock for questionary.select.
        tmp_path (Path): Pytest fixture for temporary directory path.
    """
    dummy_file = tmp_path / ".gitignore"
    dummy_file.write_text("# Old config")
    
    mock_select.return_value.ask.return_value = "Python"
    
    result = runner.invoke(app, ["gitignore", "--path", str(tmp_path)], input="n\n")
    
    assert result.exit_code == 0
    assert "already exists" in result.stdout
    assert "Aborted" in result.stdout
    assert dummy_file.read_text() == "# Old config"
