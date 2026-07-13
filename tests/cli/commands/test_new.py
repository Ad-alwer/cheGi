"""Tests for the chegi new CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app
from chegi.services.new_project.models import NewProjectResult

runner = CliRunner()


class TestNewCli:
    """Tests for the chegi new CLI command."""

    @patch("chegi.cli.commands.new.NewProjectService")
    def test_new_basic_non_interactive(
        self,
        mock_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that chegi new <name> -y creates a project in non-interactive mode."""
        mock_service.return_value.create.return_value = NewProjectResult(
            project_path=tmp_path / "test-proj",
            files_created=[".git", ".gitignore", ".chegi/", "README.md"],
            commit_hash="abc1234",
        )

        result = runner.invoke(app, ["new", "test-proj", "--path", str(tmp_path), "-y"])
        assert result.exit_code == 0, result.stdout
        assert "test-proj" in result.stdout

    @patch("chegi.cli.commands.new.NewProjectService")
    def test_new_with_template(
        self,
        mock_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that chegi new <name> -t python passes correct config."""
        mock_service.return_value.create.return_value = NewProjectResult(
            project_path=tmp_path / "py-app",
            files_created=[".git", ".gitignore", ".chegi/", "README.md"],
            commit_hash="abc123",
        )

        result = runner.invoke(
            app, ["new", "py-app", "--path", str(tmp_path), "-t", "python"]
        )
        assert result.exit_code == 0, result.stdout
        assert "py-app" in result.stdout

    @patch("chegi.cli.commands.new.NewProjectService")
    def test_new_with_license(
        self,
        mock_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that chegi new <name> --license mit includes a LICENSE file."""
        mock_service.return_value.create.return_value = NewProjectResult(
            project_path=tmp_path / "lic-app",
            files_created=[".git", ".gitignore", ".chegi/", "README.md", "LICENSE"],
            commit_hash="abc123",
        )

        result = runner.invoke(
            app, ["new", "lic-app", "--path", str(tmp_path), "--license", "mit", "-y"]
        )
        assert result.exit_code == 0, result.stdout
        assert "LICENSE" in result.stdout

    @patch("chegi.cli.commands.new.NewProjectService")
    def test_new_no_readme(
        self,
        mock_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that chegi new <name> --no-readme skips README.md."""
        mock_service.return_value.create.return_value = NewProjectResult(
            project_path=tmp_path / "no-rm",
            files_created=[".git", ".gitignore", ".chegi/"],
            commit_hash="abc123",
        )

        result = runner.invoke(
            app, ["new", "no-rm", "--path", str(tmp_path), "--no-readme", "-y"]
        )
        assert result.exit_code == 0, result.stdout
        assert "README" not in result.stdout

    @patch("chegi.cli.commands.new.NewProjectService")
    def test_new_no_gitignore(
        self,
        mock_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that chegi new <name> --no-gitignore skips .gitignore."""
        mock_service.return_value.create.return_value = NewProjectResult(
            project_path=tmp_path / "no-gi",
            files_created=[".git", ".chegi/", "README.md"],
            commit_hash="abc123",
        )

        result = runner.invoke(
            app, ["new", "no-gi", "--path", str(tmp_path), "--no-gitignore", "-y"]
        )
        assert result.exit_code == 0, result.stdout
        assert ".gitignore" not in result.stdout

    @patch("chegi.cli.commands.new.NewProjectService")
    def test_new_fails_on_existing_dir(
        self,
        mock_service: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that chegi new fails when the project directory already exists."""
        from chegi.services.new_project.exceptions import ProjectAlreadyExistsError

        mock_service.return_value.create.side_effect = ProjectAlreadyExistsError(
            "Directory 'exists' already exists."
        )

        result = runner.invoke(app, ["new", "exists", "--path", str(tmp_path), "-y"])
        assert result.exit_code == 1
        assert "already exists" in result.stdout
