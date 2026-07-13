"""Tests for the GuardHistoryService class."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chegi.services.guard.exceptions import HistoryScanError
from chegi.services.guard.history import GuardHistoryService
from chegi.services.guard.models import HistoryFinding, HistoryScanResult

TEST_REPO = Path("/fake/repo")


@pytest.fixture
def scanner():
    """Create a GuardHistoryService instance for testing."""
    return GuardHistoryService(repo_path=TEST_REPO)


class TestHistoryScan:
    """Tests for GuardHistoryService scan method."""

    @patch.object(GuardHistoryService, "_get_all_commits")
    @patch("chegi.services.git.client.GitClient.is_valid_repo")
    def test_scan_not_a_repo(
        self, mock_is_valid: MagicMock, mock_get_commits: MagicMock, scanner
    ):
        """Test that scan raises HistoryScanError when not in a valid repo."""
        mock_is_valid.return_value = False

        with pytest.raises(HistoryScanError, match="Not a valid Git repository"):
            scanner.scan()

        mock_get_commits.assert_not_called()

    @patch.object(GuardHistoryService, "_get_all_commits")
    @patch("chegi.services.git.client.GitClient.is_valid_repo")
    def test_scan_no_commits(
        self, mock_is_valid: MagicMock, mock_get_commits: MagicMock, scanner
    ):
        """Test that scan returns empty result when no commits exist."""
        mock_is_valid.return_value = True
        mock_get_commits.return_value = []

        result = scanner.scan()

        assert result.total_commits_scanned == 0
        assert result.total_findings == 0
        assert result.findings == []

    @patch.object(GuardHistoryService, "_get_commit_info")
    @patch.object(GuardHistoryService, "_get_commit_files")
    @patch.object(GuardHistoryService, "_get_all_commits")
    @patch("chegi.services.git.client.GitClient.is_valid_repo")
    def test_scan_no_findings(
        self,
        mock_is_valid: MagicMock,
        mock_get_commits: MagicMock,
        mock_get_files: MagicMock,
        mock_get_info: MagicMock,
        scanner,
    ):
        """Test that scan returns no findings when all files are clean."""
        mock_is_valid.return_value = True
        mock_get_commits.return_value = ["abc123"]
        mock_get_files.return_value = ["main.py", "README.md"]
        mock_get_info.return_value = {
            "hash": "abc123",
            "author": "Test",
            "date": "2026-01-01",
            "message": "Initial commit",
        }

        result = scanner.scan()

        assert result.total_commits_scanned == 1
        assert result.total_findings == 0
        assert result.findings == []

    @patch.object(GuardHistoryService, "_get_commit_info")
    @patch.object(GuardHistoryService, "_get_commit_files")
    @patch.object(GuardHistoryService, "_get_all_commits")
    @patch("chegi.services.git.client.GitClient.is_valid_repo")
    def test_scan_finds_sensitive_files(
        self,
        mock_is_valid: MagicMock,
        mock_get_commits: MagicMock,
        mock_get_files: MagicMock,
        mock_get_info: MagicMock,
        scanner,
    ):
        """Test that scan detects sensitive files in commit history."""
        mock_is_valid.return_value = True
        mock_get_commits.return_value = ["abc123", "def456"]
        mock_get_files.side_effect = [
            [".env", "main.py"],
            ["README.md", "key.pem"],
        ]
        mock_get_info.side_effect = [
            {
                "hash": "abc123",
                "author": "Alice",
                "date": "2026-01-01",
                "message": "Add config",
            },
            {
                "hash": "def456",
                "author": "Bob",
                "date": "2026-01-02",
                "message": "Add key",
            },
        ]

        result = scanner.scan()

        assert result.total_commits_scanned == 2
        assert result.total_findings == 2
        assert len(result.findings) == 2

        finding1 = result.findings[0]
        assert finding1.commit_hash == "abc123"
        assert finding1.file_path == ".env"
        assert finding1.pattern_matched
        assert finding1.author == "Alice"

        finding2 = result.findings[1]
        assert finding2.commit_hash == "def456"
        assert finding2.file_path == "key.pem"
        assert finding2.pattern_matched
        assert finding2.author == "Bob"


class TestHistoryHelpers:
    """Tests for GuardHistoryService helper methods."""

    def test_should_exclude_matches_filename(self, scanner):
        """Test that _should_exclude matches a file name against exclude patterns."""
        scanner.exclude_patterns = ["*.example.env", "docs/*"]
        assert scanner._should_exclude("config.example.env") is True
        assert scanner._should_exclude("docs/README.md") is True

    def test_should_exclude_no_match(self, scanner):
        """Test that _should_exclude returns False when no patterns match."""
        scanner.exclude_patterns = ["*.example.env"]
        assert scanner._should_exclude(".env") is False
        assert scanner._should_exclude("main.py") is False

    def test_match_pattern_matches_filename(self, scanner):
        """Test that _match_pattern detects sensitive file names."""
        scanner.patterns = [".env*", "*.pem"]
        assert scanner._match_pattern(".env") == ".env*"
        assert scanner._match_pattern("key.pem") == "*.pem"

    def test_match_pattern_no_match(self, scanner):
        """Test that _match_pattern returns None for clean files."""
        scanner.patterns = [".env*", "*.pem"]
        assert scanner._match_pattern("main.py") is None
        assert scanner._match_pattern("README.md") is None


class TestGenerateReport:
    """Tests for GuardHistoryService.generate_report."""

    def test_generates_html_with_findings(self, tmp_path: Path):
        """Test that generate_report creates an HTML file with findings."""
        result = HistoryScanResult(
            findings=[
                HistoryFinding(
                    commit_hash="abc123",
                    file_path=".env",
                    pattern_matched=".env*",
                    commit_message="Add config",
                    author="Alice",
                    date="2026-01-01",
                ),
            ],
            total_commits_scanned=10,
            total_findings=1,
            repo_path=str(tmp_path),
        )

        report_path = GuardHistoryService.generate_report(result, tmp_path)

        assert report_path.exists()
        content = report_path.read_text()
        assert "cheGi History Scan Report" in content
        assert ".env" in content
        assert ".env*" in content
        assert "abc123" in content

    def test_generates_html_no_findings(self, tmp_path: Path):
        """Test that generate_report creates an HTML file when no secrets found."""
        result = HistoryScanResult(
            findings=[],
            total_commits_scanned=5,
            total_findings=0,
            repo_path=str(tmp_path),
        )

        report_path = GuardHistoryService.generate_report(result, tmp_path)

        assert report_path.exists()
        content = report_path.read_text()
        assert "No secrets found" in content


class TestRemoveFromHistory:
    """Tests for GuardHistoryService.remove_file_from_history."""

    @patch("chegi.services.git.client.GitClient.run_command")
    def test_remove_success(self, mock_run: MagicMock, scanner):
        """Test that remove_file_from_history returns True on success."""
        mock_run.return_value = ""
        result = scanner.remove_file_from_history("secret.env")
        assert result is True
        mock_run.assert_called_once()

    @patch("chegi.services.git.client.GitClient.run_command")
    def test_remove_failure(self, mock_run: MagicMock, scanner):
        """Test that remove_file_from_history returns False on failure."""
        from chegi.services.git.exceptions import GitCommandError

        mock_run.side_effect = GitCommandError("filter-branch failed")
        result = scanner.remove_file_from_history("secret.env")
        assert result is False
        mock_run.assert_called_once()
