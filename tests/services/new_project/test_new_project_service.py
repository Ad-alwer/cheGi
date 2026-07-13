"""Tests for the NewProjectService class."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chegi.services.new_project import (
    NewProjectConfig,
    NewProjectResult,
    NewProjectService,
)
from chegi.services.new_project.exceptions import (
    GitInitError,
    NewProjectError,
    ProjectAlreadyExistsError,
    ProjectCreationError,
)


class TestNewProjectConfig:
    """Tests for NewProjectConfig dataclass."""

    def test_default_values(self) -> None:
        """Test that NewProjectConfig uses sensible defaults."""
        config = NewProjectConfig(name="test-proj")
        assert config.name == "test-proj"
        assert config.path == Path.cwd()
        assert config.template is None
        assert config.license_type is None
        assert config.technologies == []
        assert config.skip_readme is False
        assert config.skip_gitignore is False
        assert config.skip_chegi is False
        assert config.yes is False

    def test_explicit_values(self) -> None:
        """Test that NewProjectConfig stores all provided values."""
        config = NewProjectConfig(
            name="my-app",
            path=Path("/tmp"),
            template="python",
            license_type="mit",
            technologies=["python", "node"],
            skip_readme=True,
            skip_gitignore=True,
            skip_chegi=True,
            yes=True,
        )
        assert config.name == "my-app"
        assert config.path == Path("/tmp")
        assert config.template == "python"
        assert config.license_type == "mit"
        assert config.technologies == ["python", "node"]
        assert config.skip_readme is True
        assert config.skip_gitignore is True
        assert config.skip_chegi is True
        assert config.yes is True


class TestNewProjectResult:
    """Tests for NewProjectResult dataclass."""

    def test_default_values(self) -> None:
        """Test that NewProjectResult uses sensible defaults."""
        result = NewProjectResult(project_path=Path("/tmp/test"))
        assert result.project_path == Path("/tmp/test")
        assert result.files_created == []
        assert result.commit_hash is None
        assert result.is_successful is True


class TestNewProjectServiceCreate:
    """Tests for NewProjectService.create()."""

    def test_raises_error_when_dir_exists(self, tmp_path: Path) -> None:
        """Test that create raises ProjectAlreadyExistsError when target exists."""
        project_dir = tmp_path / "existing"
        project_dir.mkdir()

        config = NewProjectConfig(name="existing", path=tmp_path)
        service = NewProjectService(config)

        with pytest.raises(ProjectAlreadyExistsError, match="already exists"):
            service.create()

    @patch("chegi.services.new_project.new_project_service.subprocess.run")
    @patch(
        "chegi.services.new_project.new_project_service.InitService.create_project_directory"
    )
    def test_create_full_success(
        self,
        mock_init: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that create scaffolds all files and makes initial commit."""
        mock_run.return_value = MagicMock(
            stdout="[main abc1234] Initial commit",
            stderr="",
            returncode=0,
        )
        mock_init.return_value = MagicMock()

        config = NewProjectConfig(name="my-proj", path=tmp_path, license_type="mit")
        service = NewProjectService(config)
        result = service.create()

        assert result.is_successful
        assert result.project_path == tmp_path / "my-proj"
        assert result.project_path.is_dir()
        assert result.commit_hash == "abc1234"
        assert ".git" in result.files_created
        assert ".gitignore" in result.files_created
        assert ".chegi/" in result.files_created
        assert "README.md" in result.files_created
        assert "LICENSE" in result.files_created

    @patch("chegi.services.new_project.new_project_service.subprocess.run")
    def test_create_skips_readme(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test that create skips README.md when skip_readme is True."""
        mock_run.return_value = MagicMock(
            stdout="[main def5678] chore(new): initial project scaffold via cheGi 🐆",
            stderr="",
            returncode=0,
        )

        config = NewProjectConfig(name="no-readme", path=tmp_path, skip_readme=True)
        service = NewProjectService(config)
        result = service.create()

        assert "README.md" not in result.files_created
        assert not (tmp_path / "no-readme" / "README.md").exists()

    @patch("chegi.services.new_project.new_project_service.subprocess.run")
    @patch(
        "chegi.services.new_project.new_project_service.InitService.create_project_directory"
    )
    def test_create_skips_gitignore(
        self, mock_init: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test that create skips .gitignore when skip_gitignore is True."""
        mock_run.return_value = MagicMock(
            stdout="[main def5678] chore(new): initial project scaffold via cheGi 🐆",
            stderr="",
            returncode=0,
        )
        mock_init.return_value = MagicMock()

        config = NewProjectConfig(
            name="no-gitignore", path=tmp_path, skip_gitignore=True
        )
        service = NewProjectService(config)
        result = service.create()

        assert ".gitignore" not in result.files_created

    @patch("chegi.services.new_project.new_project_service.subprocess.run")
    def test_create_skips_chegi_dir(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test that create skips .chegi/ directory when skip_chegi is True."""
        mock_run.return_value = MagicMock(
            stdout="[main def5678] chore(new): initial project scaffold via cheGi 🐆",
            stderr="",
            returncode=0,
        )

        config = NewProjectConfig(name="no-chegi", path=tmp_path, skip_chegi=True)
        service = NewProjectService(config)
        result = service.create()

        assert ".chegi/" not in result.files_created
        assert not (tmp_path / "no-chegi" / ".chegi").exists()

    @patch("chegi.services.new_project.new_project_service.subprocess.run")
    def test_create_no_license(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test that create skips LICENSE when no license_type is set."""
        mock_run.return_value = MagicMock(
            stdout="[main abc] chore",
            stderr="",
            returncode=0,
        )

        config = NewProjectConfig(name="no-lic", path=tmp_path)
        service = NewProjectService(config)
        result = service.create()

        assert "LICENSE" not in result.files_created
        assert not (tmp_path / "no-lic" / "LICENSE").exists()

    @patch("chegi.services.new_project.new_project_service.subprocess.run")
    def test_git_init_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test that create raises GitInitError when git init fails."""
        mock_run.side_effect = GitInitError("Git is not installed.")

        config = NewProjectConfig(name="fail-init", path=tmp_path)
        service = NewProjectService(config)

        with pytest.raises(NewProjectError):
            service.create()


class TestNewProjectServiceCreateGitignore:
    """Tests for .gitignore generation."""

    @patch("chegi.services.new_project.new_project_service.subprocess.run")
    @patch("chegi.services.new_project.new_project_service.EnvManager")
    def test_gitignore_with_technologies(
        self,
        mock_env_mgr: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that create generates .gitignore with specific technologies."""
        mock_run.return_value = MagicMock(
            stdout="[main a1b2c3] init",
            stderr="",
            returncode=0,
        )
        mock_instance = mock_env_mgr.return_value
        mock_instance.get_envs_with_gitignore.return_value = ["python", "node"]

        config = NewProjectConfig(
            name="with-tech", path=tmp_path, technologies=["python", "node"]
        )
        service = NewProjectService(config)
        result = service.create()

        assert ".gitignore" in result.files_created
        mock_instance.generate_gitignore.assert_called_once_with(
            ["python", "node"], str(tmp_path / "with-tech")
        )

    @patch("chegi.services.new_project.new_project_service.subprocess.run")
    @patch("chegi.services.new_project.new_project_service.EnvManager")
    def test_gitignore_without_technologies_creates_minimal(
        self,
        mock_env_mgr: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that create generates a minimal .gitignore when no technologies."""
        mock_run.return_value = MagicMock(
            stdout="[main a1b2c3] init",
            stderr="",
            returncode=0,
        )

        config = NewProjectConfig(name="minimal", path=tmp_path)
        service = NewProjectService(config)
        result = service.create()

        assert ".gitignore" in result.files_created
        gitignore_path = tmp_path / "minimal" / ".gitignore"
        assert gitignore_path.is_file()
        content = gitignore_path.read_text()
        assert "node_modules/" in content
        assert ".env" in content
        assert mock_env_mgr.return_value.generate_gitignore.called is False


class TestNewProjectServiceLicense:
    """Tests for LICENSE generation."""

    @patch("chegi.services.new_project.new_project_service.subprocess.run")
    @patch(
        "chegi.services.new_project.new_project_service.NewProjectService._get_git_user",
        return_value="Test Author",
    )
    def test_license_with_git_user(
        self,
        mock_get_user: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that LICENSE uses the git user name when available."""
        mock_run.return_value = MagicMock(
            stdout="[main a1b2c3] init",
            stderr="",
            returncode=0,
        )

        config = NewProjectConfig(name="lic-user", path=tmp_path, license_type="mit")
        service = NewProjectService(config)
        result = service.create()

        assert "LICENSE" in result.files_created
        license_file = tmp_path / "lic-user" / "LICENSE"
        assert license_file.is_file()
        content = license_file.read_text()
        assert "Test Author" in content

    @patch("chegi.services.new_project.new_project_service.subprocess.run")
    @patch(
        "chegi.services.new_project.new_project_service.NewProjectService._get_git_user",
        return_value=None,
    )
    def test_license_with_placeholder_author(
        self,
        mock_get_user: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that LICENSE uses placeholder when git user is unavailable."""
        mock_run.return_value = MagicMock(
            stdout="[main a1b2c3] init",
            stderr="",
            returncode=0,
        )

        config = NewProjectConfig(name="lic-place", path=tmp_path, license_type="mit")
        service = NewProjectService(config)
        result = service.create()

        assert "LICENSE" in result.files_created
        license_file = tmp_path / "lic-place" / "LICENSE"
        assert license_file.is_file()
        content = license_file.read_text()
        assert "<author>" in content

    @patch("chegi.services.new_project.new_project_service.subprocess.run")
    def test_license_unknown_type(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that create raises ProjectCreationError for unknown license type."""
        mock_run.return_value = MagicMock(
            stdout="[main a1b2c3] init",
            stderr="",
            returncode=0,
        )

        config = NewProjectConfig(
            name="bad-lic", path=tmp_path, license_type="unknown_license"
        )
        service = NewProjectService(config)

        with pytest.raises(ProjectCreationError, match="Unknown license"):
            service.create()


class TestNewProjectServiceGitUser:
    """Tests for _get_git_user helper."""

    @patch(
        "chegi.services.new_project.new_project_service.subprocess.run",
        return_value=MagicMock(stdout="John Doe\n", stderr="", returncode=0),
    )
    def test_get_git_user_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test that _get_git_user returns the git user name."""
        config = NewProjectConfig(name="test", path=tmp_path)
        service = NewProjectService(config)
        user = service._get_git_user()
        assert user == "John Doe"

    @patch(
        "chegi.services.new_project.new_project_service.subprocess.run",
        side_effect=FileNotFoundError(),
    )
    def test_get_git_user_no_git(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test that _get_git_user returns None when git is not installed."""
        config = NewProjectConfig(name="test", path=tmp_path)
        service = NewProjectService(config)
        user = service._get_git_user()
        assert user is None


class TestNewProjectServiceInitialCommit:
    """Tests for initial commit."""

    @patch("chegi.services.new_project.new_project_service.subprocess.run")
    def test_initial_commit_extracts_hash(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _initial_commit extracts the commit hash from output."""
        mock_run.return_value = MagicMock(
            stdout="[main abc1234] chore(new): initial project scaffold via cheGi 🐆",
            stderr="",
            returncode=0,
        )

        config = NewProjectConfig(name="test", path=tmp_path)
        service = NewProjectService(config)
        # Manually create the directory and .git
        service.project_path.mkdir(parents=True)
        (service.project_path / ".git").mkdir()

        hash_val = service._initial_commit()
        assert hash_val == "abc1234"

    @patch(
        "chegi.services.new_project.new_project_service.subprocess.run",
        side_effect=FileNotFoundError(),
    )
    def test_initial_commit_failure_returns_none(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _initial_commit returns None when commit fails."""
        config = NewProjectConfig(name="test", path=tmp_path)
        service = NewProjectService(config)
        service.project_path.mkdir(parents=True)
        (service.project_path / ".git").mkdir()

        hash_val = service._initial_commit()
        assert hash_val is None
