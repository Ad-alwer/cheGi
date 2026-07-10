import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from chegi.services.guard.security import SecurityGuard

# Dummy path for testing
TEST_REPO_PATH = Path("/fake/repo")


@patch("subprocess.run")
def test_get_staged_files_success(mock_run):
    """Test retrieving staged files successfully via git diff."""
    mock_result = MagicMock()
    mock_result.stdout = "main.py\nconfig.json\n\n"
    mock_run.return_value = mock_result

    files = SecurityGuard.get_staged_files(TEST_REPO_PATH)

    assert files == ["main.py", "config.json"]
    mock_run.assert_called_once_with(
        ["git", "diff", "--name-only", "--cached"],
        cwd=TEST_REPO_PATH,
        capture_output=True,
        text=True,
        check=True,
    )


@patch("subprocess.run")
def test_get_staged_files_failure(mock_run):
    """Test that an empty list is returned when the git command fails."""
    mock_run.side_effect = subprocess.CalledProcessError(1, ["git"])

    files = SecurityGuard.get_staged_files(TEST_REPO_PATH)

    assert files == []


@patch(
    "chegi.services.guard.security.DEFAULT_SENSITIVE_PATTERNS",
    [".env", "*.pem", "secret.*"],
)
def test_find_sensitive_files_found():
    """Test detection of files matching the sensitive patterns."""
    files_to_check = ["main.py", ".env", "utils.py", "key.pem", "secret.txt"]
    detected = SecurityGuard.find_sensitive_files(files_to_check)

    assert len(detected) == 3
    assert ".env" in detected
    assert "key.pem" in detected
    assert "secret.txt" in detected


@patch("chegi.services.guard.security.DEFAULT_SENSITIVE_PATTERNS", [".env", "*.pem"])
def test_find_sensitive_files_clean():
    """Test that an empty list is returned when no sensitive files are present."""
    files_to_check = ["main.py", "README.md"]
    detected = SecurityGuard.find_sensitive_files(files_to_check)

    assert detected == []


@patch("subprocess.run")
def test_unstage_files_success(mock_run):
    """Test successfully unstaging specific files using git rm."""
    result = SecurityGuard.unstage_files([".env", "key.pem"], TEST_REPO_PATH)

    assert result is True
    mock_run.assert_called_once_with(
        ["git", "rm", "--cached", ".env", "key.pem"],
        cwd=TEST_REPO_PATH,
        capture_output=True,
        check=True,
    )


@patch("subprocess.run")
def test_unstage_files_empty_list(mock_run):
    """Test that unstaging an empty list returns True without executing git commands."""
    result = SecurityGuard.unstage_files([], TEST_REPO_PATH)

    assert result is True
    mock_run.assert_not_called()


@patch("subprocess.run")
def test_unstage_files_failure(mock_run):
    """Test that a subprocess failure during unstage returns False."""
    mock_run.side_effect = subprocess.CalledProcessError(1, ["git"])

    result = SecurityGuard.unstage_files([".env"], TEST_REPO_PATH)

    assert result is False


@patch.object(SecurityGuard, "find_sensitive_files")
@patch.object(SecurityGuard, "get_staged_files")
def test_scan_repo_no_staged_files(mock_get_staged, mock_find_sensitive):
    """Test repository scan when no files are staged (returns safe)."""
    mock_get_staged.return_value = []

    result = SecurityGuard.scan_repo(TEST_REPO_PATH)

    assert result.is_safe is True
    assert result.sensitive_files == []
    mock_find_sensitive.assert_not_called()


@patch.object(SecurityGuard, "find_sensitive_files")
@patch.object(SecurityGuard, "get_staged_files")
def test_scan_repo_staged_but_clean(mock_get_staged, mock_find_sensitive):
    """Test repository scan when staged files exist but none are sensitive (returns safe)."""
    mock_get_staged.return_value = ["main.py"]
    mock_find_sensitive.return_value = []

    result = SecurityGuard.scan_repo(TEST_REPO_PATH)

    assert result.is_safe is True
    assert result.sensitive_files == []


@patch.object(SecurityGuard, "find_sensitive_files")
@patch.object(SecurityGuard, "get_staged_files")
def test_scan_repo_staged_and_sensitive(mock_get_staged, mock_find_sensitive):
    """Test repository scan when staged files contain sensitive data (returns unsafe)."""
    mock_get_staged.return_value = ["main.py", ".env"]
    mock_find_sensitive.return_value = [".env"]

    result = SecurityGuard.scan_repo(TEST_REPO_PATH)

    assert result.is_safe is False
    assert result.sensitive_files == [".env"]
