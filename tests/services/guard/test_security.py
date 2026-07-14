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


@patch("chegi.services.guard.security.DEFAULT_SENSITIVE_PATTERNS", [".env", "*.pem"])
def test_find_sensitive_files_with_extra_patterns():
    """Test detection with extra custom patterns added."""
    files_to_check = ["main.py", ".env", "my.key", "secrets.yaml", "config.local"]
    extra = {"my.key", "secrets.yaml", "*.local"}
    detected = SecurityGuard.find_sensitive_files(files_to_check, extra)

    assert len(detected) == 4
    assert ".env" in detected
    assert "my.key" in detected
    assert "secrets.yaml" in detected
    assert "config.local" in detected


@patch("chegi.services.guard.security.DEFAULT_SENSITIVE_PATTERNS", [".env"])
def test_find_sensitive_files_extra_patterns_only():
    """Test detection when only extra patterns match (not defaults)."""
    files_to_check = ["main.py", "custom.secret", "regular.txt"]
    extra = {"custom.secret"}
    detected = SecurityGuard.find_sensitive_files(files_to_check, extra)

    assert detected == ["custom.secret"]


@patch("chegi.services.guard.security.DEFAULT_SENSITIVE_PATTERNS", [".env"])
def test_find_sensitive_files_extra_patterns_empty():
    """Test that empty extra_patterns does not affect behavior."""
    files_to_check = [".env", "main.py"]
    detected = SecurityGuard.find_sensitive_files(files_to_check, set())

    assert detected == [".env"]


@patch("chegi.services.guard.security.DEFAULT_SENSITIVE_PATTERNS", [".env"])
def test_find_sensitive_files_extra_patterns_none():
    """Test that None extra_patterns does not affect behavior."""
    files_to_check = [".env", "main.py"]
    detected = SecurityGuard.find_sensitive_files(files_to_check, None)

    assert detected == [".env"]


@patch("chegi.services.guard.security.DEFAULT_SENSITIVE_PATTERNS", [".env", "*.pem"])
def test_find_sensitive_files_extra_matches_in_defaults():
    """Test that extra patterns already covered by defaults don't duplicate."""
    files_to_check = [".env", "key.pem"]
    extra = {".env"}  # already in defaults
    detected = SecurityGuard.find_sensitive_files(files_to_check, extra)

    assert len(detected) == 2


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


# --- get_unstaged_files tests ---


@patch("subprocess.run")
def test_get_unstaged_files_success(mock_run):
    """Test retrieving unstaged files successfully via git diff."""
    mock_result = MagicMock()
    mock_result.stdout = "main.py\nconfig.json\n\n"
    mock_run.return_value = mock_result

    files = SecurityGuard.get_unstaged_files(TEST_REPO_PATH)

    assert files == ["main.py", "config.json"]
    mock_run.assert_called_once_with(
        ["git", "diff", "--name-only"],
        cwd=TEST_REPO_PATH,
        capture_output=True,
        text=True,
        check=True,
    )


@patch("subprocess.run")
def test_get_unstaged_files_failure(mock_run):
    """Test that an empty list is returned when the git command fails."""
    mock_run.side_effect = subprocess.CalledProcessError(1, ["git"])

    files = SecurityGuard.get_unstaged_files(TEST_REPO_PATH)

    assert files == []


# --- scan_strict tests ---


@patch.object(SecurityGuard, "get_unstaged_files")
@patch.object(SecurityGuard, "get_staged_files")
def test_scan_strict_both_clean(mock_get_staged, mock_get_unstaged):
    """Test scan_strict when both staged and unstaged are clean."""
    mock_get_staged.return_value = ["main.py"]
    mock_get_unstaged.return_value = []

    staged_result, unstaged_result = SecurityGuard.scan_strict(TEST_REPO_PATH)

    assert staged_result.is_safe is True
    assert unstaged_result.is_safe is True


@patch.object(SecurityGuard, "get_unstaged_files")
@patch.object(SecurityGuard, "get_staged_files")
def test_scan_strict_staged_sensitive(mock_get_staged, mock_get_unstaged):
    """Test scan_strict detects sensitive files in staging."""
    mock_get_staged.return_value = [".env"]
    mock_get_unstaged.return_value = []

    staged_result, unstaged_result = SecurityGuard.scan_strict(TEST_REPO_PATH)

    assert staged_result.is_safe is False
    assert staged_result.sensitive_files == [".env"]
    assert unstaged_result.is_safe is True


@patch.object(SecurityGuard, "get_unstaged_files")
@patch.object(SecurityGuard, "get_staged_files")
def test_scan_strict_unstaged_sensitive(mock_get_staged, mock_get_unstaged):
    """Test scan_strict detects sensitive files in working directory."""
    mock_get_staged.return_value = ["clean.py"]
    mock_get_unstaged.return_value = [".env"]

    staged_result, unstaged_result = SecurityGuard.scan_strict(TEST_REPO_PATH)

    assert staged_result.is_safe is True
    assert unstaged_result.is_safe is False
    assert unstaged_result.sensitive_files == [".env"]


@patch.object(SecurityGuard, "get_unstaged_files")
@patch.object(SecurityGuard, "get_staged_files")
def test_scan_strict_both_sensitive(mock_get_staged, mock_get_unstaged):
    """Test scan_strict detects sensitive files in both areas."""
    mock_get_staged.return_value = [".env"]
    mock_get_unstaged.return_value = ["key.pem"]

    staged_result, unstaged_result = SecurityGuard.scan_strict(TEST_REPO_PATH)

    assert staged_result.is_safe is False
    assert staged_result.sensitive_files == [".env"]
    assert unstaged_result.is_safe is False
    assert unstaged_result.sensitive_files == ["key.pem"]


# --- scan_directory tests ---


@patch(
    "chegi.services.guard.security.DEFAULT_SENSITIVE_PATTERNS",
    [".env", "*.pem"],
)
def test_scan_directory_no_sensitive(tmp_path):
    """Test scan_directory returns safe for clean directory."""
    (tmp_path / "main.py").write_text("x")
    (tmp_path / "readme.md").write_text("x")

    result = SecurityGuard.scan_directory(tmp_path)

    assert result.is_safe is True
    assert result.sensitive_files == []


@patch(
    "chegi.services.guard.security.DEFAULT_SENSITIVE_PATTERNS",
    [".env", "*.pem"],
)
def test_scan_directory_finds_sensitive(tmp_path):
    """Test scan_directory finds sensitive files recursively."""
    (tmp_path / ".env").write_text("SECRET=1")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "key.pem").write_text("key data")

    result = SecurityGuard.scan_directory(tmp_path)

    assert result.is_safe is False
    assert len(result.sensitive_files) == 2


@patch(
    "chegi.services.guard.security.DEFAULT_SENSITIVE_PATTERNS",
    [".env"],
)
def test_scan_directory_skips_git(tmp_path):
    """Test scan_directory skips .git directory."""
    (tmp_path / ".env").write_text("SECRET=1")
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / ".env").write_text("should be skipped")

    result = SecurityGuard.scan_directory(tmp_path)

    assert len(result.sensitive_files) == 1
    assert str(git_dir / ".env") not in result.sensitive_files


def test_scan_directory_not_exists(tmp_path):
    """Test scan_directory returns safe for non-existent path."""
    nonexistent = tmp_path / "does-not-exist"
    result = SecurityGuard.scan_directory(nonexistent)

    assert result.is_safe is True
    assert result.sensitive_files == []
