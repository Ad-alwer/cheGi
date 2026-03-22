import subprocess
import pytest
from unittest.mock import patch
from pathlib import Path


from chegi.security import SecurityGuard


def test_find_sensitive_files_clean() -> None:
    """Tests that safe files are not flagged as sensitive."""
    files = ["src/main.py", "README.md", "tests/test_app.py", "image.png"]
    detected = SecurityGuard.find_sensitive_files(files)
    
    assert detected == []
    assert len(detected) == 0


def test_find_sensitive_files_detected() -> None:
    """Tests that files matching sensitive patterns are correctly identified."""
    files = [
        "src/main.py", 
        ".env.local", 
        "config/prod.pem", 
        "my_secret_token.txt",
        "id_rsa.pub"
    ]
    detected = SecurityGuard.find_sensitive_files(files)
    
    assert len(detected) == 4
    assert ".env.local" in detected
    assert "config/prod.pem" in detected
    assert "my_secret_token.txt" in detected
    assert "id_rsa.pub" in detected
    assert "src/main.py" not in detected


@patch("chegi.security.subprocess.run")
def test_get_staged_files_success(mock_run) -> None:
    """Tests successful retrieval of staged files from git diff."""
    # Mocking the stdout of the git command
    mock_run.return_value.stdout = "file1.txt\nsrc/main.py\n\n"
    
    files = SecurityGuard.get_staged_files()
    
    assert files == ["file1.txt", "src/main.py"]
    mock_run.assert_called_once()


@patch("chegi.security.subprocess.run")
def test_get_staged_files_git_error(mock_run) -> None:
    """Tests that a Git error (e.g., not a git repo) returns an empty list gracefully."""
    mock_run.side_effect = subprocess.CalledProcessError(128, "git")
    
    files = SecurityGuard.get_staged_files()
    
    assert files == []


@patch("chegi.security.subprocess.run")
def test_get_staged_files_no_git_installed(mock_run) -> None:
    """Tests that a missing Git executable returns an empty list gracefully."""
    mock_run.side_effect = FileNotFoundError()
    
    files = SecurityGuard.get_staged_files()
    
    assert files == []


@patch("chegi.security.subprocess.run")
def test_unstage_files_success(mock_run) -> None:
    """Tests successful unstaging of files."""
    files_to_unstage = [".env", "config.json"]
    
    result = SecurityGuard.unstage_files(files_to_unstage)
    
    assert result is True
    mock_run.assert_called_once_with(
        ["git", "rm", "--cached", ".env", "config.json"],
        cwd=Path.cwd(),
        capture_output=True,
        check=True
    )


def test_unstage_files_empty_list() -> None:
    """Tests that passing an empty list returns True without running subprocess."""
    result = SecurityGuard.unstage_files([])
    
    assert result is True


@patch("chegi.security.subprocess.run")
def test_unstage_files_failure(mock_run) -> None:
    """Tests unstaging failure handling when git command fails."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "git")
    
    result = SecurityGuard.unstage_files([".env"])
    
    assert result is False
    mock_run.assert_called_once()

@patch("chegi.security.subprocess.run")
def test_get_staged_files_with_repo_path(mock_run) -> None:
    mock_run.return_value.stdout = "file1.txt\n"
    custom_path = Path("/custom/repo/path")
    
    SecurityGuard.get_staged_files(repo_path=custom_path)
    
    mock_run.assert_called_once_with(
        ["git", "diff", "--name-only", "--cached"],
        cwd=custom_path,
        capture_output=True,
        text=True,
        check=True
    )


@patch("chegi.security.subprocess.run")
def test_unstage_files_with_repo_path(mock_run) -> None:
    custom_path = Path("/custom/repo/path")
    files = [".env"]
    
    SecurityGuard.unstage_files(files, repo_path=custom_path)
    
    mock_run.assert_called_once_with(
        ["git", "rm", "--cached", ".env"],
        cwd=custom_path,
        capture_output=True,
        check=True
    )


@patch("chegi.security.SecurityGuard.get_staged_files")
def test_scan_repo_safe_no_staged(mock_get_staged) -> None:
    mock_get_staged.return_value = []
    repo_path = Path("/mock/repo")
    
    result = SecurityGuard.scan_repo(repo_path)
    
    assert result == "[green]✅ Safe[/green]"
    mock_get_staged.assert_called_once_with(repo_path)


@patch("chegi.security.SecurityGuard.find_sensitive_files")
@patch("chegi.security.SecurityGuard.get_staged_files")
def test_scan_repo_safe_clean_staged(mock_get_staged, mock_find_sensitive) -> None:
    mock_get_staged.return_value = ["main.py"]
    mock_find_sensitive.return_value = []
    
    result = SecurityGuard.scan_repo(Path("/mock/repo"))
    
    assert result == "[green]✅ Safe[/green]"


@patch("chegi.security.SecurityGuard.find_sensitive_files")
@patch("chegi.security.SecurityGuard.get_staged_files")
def test_scan_repo_unsafe_single_secret(mock_get_staged, mock_find_sensitive) -> None:
    mock_get_staged.return_value = [".env"]
    mock_find_sensitive.return_value = [".env"]
    
    result = SecurityGuard.scan_repo(Path("/mock/repo"))
    
    assert result == "[red]❌ 1 Staged Secret[/red]"


@patch("chegi.security.SecurityGuard.find_sensitive_files")
@patch("chegi.security.SecurityGuard.get_staged_files")
def test_scan_repo_unsafe_multiple_secrets(mock_get_staged, mock_find_sensitive) -> None:
    mock_get_staged.return_value = [".env", "id_rsa"]
    mock_find_sensitive.return_value = [".env", "id_rsa"]
    
    result = SecurityGuard.scan_repo(Path("/mock/repo"))
    
    assert result == "[red]❌ 2 Staged Secrets[/red]"