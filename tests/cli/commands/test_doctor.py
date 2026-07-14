"""Tests for the chegi doctor CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app
from chegi.services.doctor.models import CheckResult, DoctorReport

runner = CliRunner()


class TestDoctorCli:
    """Tests for the chegi doctor CLI command."""

    @patch("chegi.cli.commands.doctor.DoctorService")
    def test_doctor_runs_on_directory(
        self, mock_service: MagicMock, tmp_path: Path
    ) -> None:
        """Test that chegi doctor runs and produces output."""
        mock_service.return_value.run.return_value = DoctorReport(
            repo_path=str(tmp_path),
        )

        result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
        assert result.exit_code == 0

    @patch("chegi.cli.commands.doctor.DoctorService")
    def test_doctor_shows_passing_checks(
        self, mock_service: MagicMock, tmp_path: Path
    ) -> None:
        """Test that chegi doctor displays passing checks."""
        from chegi.services.doctor.models import CheckCategory, CheckStatus

        report = DoctorReport(repo_path=str(tmp_path))
        report.results.append(
            CheckResult(
                name="Git Installed",
                category=CheckCategory.HEALTH,
                status=CheckStatus.PASS,
                message="Git is installed.",
            )
        )
        mock_service.return_value.run.return_value = report

        result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "Git Installed" in result.stdout

    @patch("chegi.cli.commands.doctor.DoctorService")
    def test_doctor_shows_failing_checks(
        self, mock_service: MagicMock, tmp_path: Path
    ) -> None:
        """Test that chegi doctor displays failing checks and exits with code 1."""
        from chegi.services.doctor.models import CheckCategory, CheckStatus

        report = DoctorReport(repo_path=str(tmp_path))
        report.results.append(
            CheckResult(
                name="Git Installed",
                category=CheckCategory.HEALTH,
                status=CheckStatus.FAIL,
                message="Git is not installed.",
                suggestion="Install Git.",
            )
        )
        mock_service.return_value.run.return_value = report

        result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "Git is not installed" in result.stdout

    def test_doctor_fails_on_nonexistent_path(self) -> None:
        """Test that chegi doctor fails when the path does not exist."""
        result = runner.invoke(
            app, ["doctor", "--path", "/path/that/does/not/exist/99999"]
        )
        assert result.exit_code == 1
        assert "Directory does not exist" in result.stdout

    @patch("chegi.cli.commands.doctor.DoctorService")
    def test_doctor_shows_warning_checks(
        self, mock_service: MagicMock, tmp_path: Path
    ) -> None:
        """Test that chegi doctor displays warnings and exits with code 1."""
        from chegi.services.doctor.models import CheckCategory, CheckStatus

        report = DoctorReport(repo_path=str(tmp_path))
        report.results.append(
            CheckResult(
                name="Pre-commit Hook",
                category=CheckCategory.SECURITY,
                status=CheckStatus.WARN,
                message="No pre-commit hook installed.",
                suggestion="Install a pre-commit hook.",
            )
        )
        report.results.append(
            CheckResult(
                name="Git Installed",
                category=CheckCategory.HEALTH,
                status=CheckStatus.PASS,
                message="Git is installed.",
            )
        )
        mock_service.return_value.run.return_value = report

        result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "Pre-commit Hook" in result.stdout
        assert "Git Installed" in result.stdout
