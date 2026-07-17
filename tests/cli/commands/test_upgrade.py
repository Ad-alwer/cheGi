"""Tests for the chegi upgrade CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app
from chegi.services.upgrade import UpgradeInfo, UpgradeService

runner = CliRunner()


class TestUpgradeCliCheck:
    """Tests for 'chegi upgrade --check'."""

    @patch.object(UpgradeService, "check_version")
    @patch.object(UpgradeService, "get_current_version", return_value="0.0.1")
    def test_check_up_to_date(
        self, mock_current: MagicMock, mock_check: MagicMock
    ) -> None:
        """Test that 'chegi upgrade --check' shows up-to-date message."""
        mock_check.return_value = UpgradeInfo(
            current_version="0.0.1",
            latest_version="0.0.1",
            is_outdated=False,
        )
        result = runner.invoke(app, ["upgrade", "--check"])
        assert result.exit_code == 0
        assert "latest version" in result.stdout.lower()

    @patch.object(UpgradeService, "check_version")
    @patch.object(UpgradeService, "get_current_version", return_value="0.0.1")
    def test_check_outdated(
        self, mock_current: MagicMock, mock_check: MagicMock
    ) -> None:
        """Test that 'chegi upgrade --check' shows new version info."""
        mock_check.return_value = UpgradeInfo(
            current_version="0.0.1",
            latest_version="99.99.99",
            is_outdated=True,
        )
        result = runner.invoke(app, ["upgrade", "--check"])
        assert result.exit_code == 0
        assert "99.99.99" in result.stdout
        assert "chegi upgrade" in result.stdout

    @patch.object(UpgradeService, "check_version")
    @patch.object(UpgradeService, "get_current_version", return_value="0.0.1")
    def test_check_with_error(
        self, mock_current: MagicMock, mock_check: MagicMock
    ) -> None:
        """Test that 'chegi upgrade --check' shows errors."""
        mock_check.return_value = UpgradeInfo(
            current_version="0.0.1",
            error="Network error",
        )
        result = runner.invoke(app, ["upgrade", "--check"])
        assert result.exit_code == 1
        assert "Network error" in result.stdout


class TestUpgradeCliDirect:
    """Tests for 'chegi upgrade' with upgrade flow."""

    @patch.object(UpgradeService, "check_version")
    @patch.object(UpgradeService, "get_current_version", return_value="0.0.1")
    def test_up_to_date(self, mock_current: MagicMock, mock_check: MagicMock) -> None:
        """Test that 'chegi upgrade' shows up-to-date message."""
        mock_check.return_value = UpgradeInfo(
            current_version="0.0.1",
            latest_version="0.0.1",
            is_outdated=False,
        )
        result = runner.invoke(app, ["upgrade"])
        assert result.exit_code == 0
        assert "latest version" in result.stdout.lower()

    @patch.object(UpgradeService, "upgrade")
    @patch.object(UpgradeService, "check_version")
    @patch.object(UpgradeService, "get_current_version", return_value="0.0.1")
    def test_upgrade_with_yes(
        self, mock_current: MagicMock, mock_check: MagicMock, mock_upgrade: MagicMock
    ) -> None:
        """Test that 'chegi upgrade --yes' upgrades without prompt."""
        mock_check.return_value = UpgradeInfo(
            current_version="0.0.1",
            latest_version="99.99.99",
            is_outdated=True,
        )
        mock_upgrade.return_value = "Successfully installed chegi"
        result = runner.invoke(app, ["upgrade", "--yes"])
        assert result.exit_code == 0
        assert "Successfully" in result.stdout
        mock_upgrade.assert_called_once_with(yes=True)

    @patch.object(UpgradeService, "upgrade", side_effect=Exception("pip failed"))
    @patch.object(UpgradeService, "check_version")
    @patch.object(UpgradeService, "get_current_version", return_value="0.0.1")
    def test_upgrade_failure(
        self, mock_current: MagicMock, mock_check: MagicMock, mock_upgrade: MagicMock
    ) -> None:
        """Test that upgrade failure shows error."""
        from chegi.services.upgrade import UpgradeError

        mock_upgrade.side_effect = UpgradeError("pip failed")
        mock_check.return_value = UpgradeInfo(
            current_version="0.0.1",
            latest_version="99.99.99",
            is_outdated=True,
        )
        result = runner.invoke(app, ["upgrade", "--yes"])
        assert result.exit_code == 1
        assert "pip failed" in result.stdout

    @patch.object(UpgradeService, "check_version")
    @patch.object(UpgradeService, "get_current_version", return_value="0.0.1")
    def test_upgrade_cancelled(
        self, mock_current: MagicMock, mock_check: MagicMock
    ) -> None:
        """Test that cancelling upgrade shows hint."""
        mock_check.return_value = UpgradeInfo(
            current_version="0.0.1",
            latest_version="99.99.99",
            is_outdated=True,
        )
        result = runner.invoke(app, ["upgrade"], input="n\n")
        assert result.exit_code == 0
        assert "chegi upgrade" in result.stdout

    @patch.object(UpgradeService, "check_version")
    @patch.object(UpgradeService, "get_current_version", return_value="0.0.1")
    def test_upgrade_with_changelog(
        self, mock_current: MagicMock, mock_check: MagicMock
    ) -> None:
        """Test that changelog diff is displayed when available."""
        mock_check.return_value = UpgradeInfo(
            current_version="0.0.1",
            latest_version="99.99.99",
            is_outdated=True,
            changelog_diff="## [99.99.99]\n\n### Added\n\n- Super feature",
        )
        result = runner.invoke(app, ["upgrade", "--yes"])
        assert result.exit_code == 0
        assert "Super feature" in result.stdout
