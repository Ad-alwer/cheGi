"""Tests for the UpgradeService class."""

import json
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chegi.services.upgrade import UpgradeError, UpgradeService
from chegi.services.upgrade.constants import AUTO_CHECK_COOLDOWN, CHECK_MARKER_FILE


class TestGetCurrentVersion:
    """Tests for UpgradeService.get_current_version()."""

    def test_returns_version_string(self) -> None:
        """Test that get_current_version returns a non-empty string."""
        version = UpgradeService.get_current_version()
        assert isinstance(version, str)
        assert len(version) > 0

    @patch("importlib.metadata.version")
    def test_fallback_to_zero(self, mock_version: MagicMock) -> None:
        """Test that get_current_version falls back to 0.0.0 on failure."""
        from importlib.metadata import PackageNotFoundError

        mock_version.side_effect = PackageNotFoundError
        assert UpgradeService.get_current_version() == "0.0.0"


class TestCompareVersions:
    """Tests for _compare_versions."""

    def test_equal(self) -> None:
        """Test that equal versions return 0."""
        assert UpgradeService._compare_versions("1.0.0", "1.0.0") == 0

    def test_older(self) -> None:
        """Test that an older version returns negative."""
        assert UpgradeService._compare_versions("0.9.0", "1.0.0") < 0

    def test_newer(self) -> None:
        """Test that a newer version returns positive."""
        assert UpgradeService._compare_versions("2.0.0", "1.9.9") > 0

    def test_different_lengths(self) -> None:
        """Test versions with different segment counts."""
        assert UpgradeService._compare_versions("1.0", "1.0.0") == 0
        assert UpgradeService._compare_versions("1.0.1", "1.0") > 0


class TestCheckVersion:
    """Tests for UpgradeService.check_version()."""

    @patch("urllib.request.urlopen")
    def test_up_to_date(self, mock_urlopen: MagicMock) -> None:
        """Test that check_version returns not outdated when on latest."""
        current = UpgradeService.get_current_version()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"info": {"version": current}}
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        service = UpgradeService()
        info = service.check_version()

        assert info.is_outdated is False
        assert info.latest_version == current
        assert info.error is None

    @patch("urllib.request.urlopen")
    def test_outdated(self, mock_urlopen: MagicMock) -> None:
        """Test that check_version returns outdated when newer exists."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"info": {"version": "99.99.99"}}
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        service = UpgradeService()
        info = service.check_version()

        assert info.is_outdated is True
        assert info.latest_version == "99.99.99"

    @patch("urllib.request.urlopen")
    def test_network_error(self, mock_urlopen: MagicMock) -> None:
        """Test that check_version handles network errors gracefully."""
        mock_urlopen.side_effect = Exception("Connection refused")

        service = UpgradeService()
        info = service.check_version()

        assert info.error is not None
        assert "Connection refused" in info.error

    @patch("urllib.request.urlopen")
    def test_bad_response(self, mock_urlopen: MagicMock) -> None:
        """Test that check_version handles bad JSON response."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        service = UpgradeService()
        info = service.check_version()

        assert info.error is not None


class TestUpgrade:
    """Tests for UpgradeService.upgrade()."""

    @patch("subprocess.run")
    def test_upgrade_success(self, mock_run: MagicMock) -> None:
        """Test that upgrade runs pip install successfully."""
        mock_run.return_value.stdout = "Successfully installed chegi"
        mock_run.return_value.stderr = ""

        result = UpgradeService().upgrade(yes=True)

        assert "Successfully installed" in result
        mock_run.assert_called_once()

    @patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "pip", stderr="error"))
    def test_upgrade_pip_error(self, mock_run: MagicMock) -> None:
        """Test that upgrade raises UpgradeError on pip failure."""
        with pytest.raises(UpgradeError):
            UpgradeService().upgrade(yes=True)

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_upgrade_pip_not_found(self, mock_run: MagicMock) -> None:
        """Test that upgrade raises UpgradeError when pip is missing."""
        with pytest.raises(UpgradeError):
            UpgradeService().upgrade(yes=True)


class TestCooldown:
    """Tests for should_check and mark_checked."""

    def test_first_check_returns_true(self, tmp_path: Path) -> None:
        """Test that should_check returns True when no marker exists."""
        service = UpgradeService(repo_path=tmp_path)
        assert service.should_check() is True

    def test_after_mark_returns_false(self, tmp_path: Path) -> None:
        """Test that should_check returns False right after marking."""
        (tmp_path / ".chegi").mkdir(parents=True)
        service = UpgradeService(repo_path=tmp_path)
        service.mark_checked()
        assert service.should_check() is False

    def test_after_cooldown_returns_true(self, tmp_path: Path) -> None:
        """Test that should_check returns True after cooldown expires."""
        (tmp_path / ".chegi").mkdir(parents=True)
        marker = tmp_path / ".chegi" / ".last_upgrade_check"
        # Write a timestamp from way in the past
        marker.write_text(str(int(time.time() - AUTO_CHECK_COOLDOWN - 1)))
        service = UpgradeService(repo_path=tmp_path)
        assert service.should_check() is True

    def test_mark_creates_marker_file(self, tmp_path: Path) -> None:
        """Test that mark_checked creates the marker file in .chegi/."""
        (tmp_path / ".chegi").mkdir(parents=True)
        service = UpgradeService(repo_path=tmp_path)
        service.mark_checked()
        marker = tmp_path / ".chegi" / CHECK_MARKER_FILE
        assert marker.exists()

    def test_corrupted_marker_returns_true(self, tmp_path: Path) -> None:
        """Test that a corrupted marker file triggers a check."""
        (tmp_path / ".chegi").mkdir(parents=True)
        marker = tmp_path / ".chegi" / ".last_upgrade_check"
        marker.write_text("not a number")
        service = UpgradeService(repo_path=tmp_path)
        assert service.should_check() is True


class TestChangelogDiff:
    """Tests for _fetch_changelog_diff."""

    @patch("urllib.request.urlopen")
    def test_fetch_diff_success(self, mock_urlopen: MagicMock) -> None:
        """Test that changelog diff is extracted correctly."""
        changelog_content = """# Changelog

## [2.0.0] - 2026-07-17

### Added

- New feature A
- New feature B

## [1.0.0] - 2026-06-01

### Added

- Initial release
"""
        mock_resp = MagicMock()
        mock_resp.read.return_value = changelog_content.encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        diff = UpgradeService._fetch_changelog_diff("1.0.0", "2.0.0")
        assert diff is not None
        assert "2.0.0" in diff
        assert "New feature A" in diff
        assert "Initial release" not in diff

    @patch("urllib.request.urlopen", side_effect=Exception("fail"))
    def test_fetch_failure_returns_none(self, mock_urlopen: MagicMock) -> None:
        """Test that a fetch failure returns None."""
        diff = UpgradeService._fetch_changelog_diff("1.0.0", "2.0.0")
        assert diff is None
