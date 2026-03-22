import subprocess
import pytest
from unittest.mock import patch

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
