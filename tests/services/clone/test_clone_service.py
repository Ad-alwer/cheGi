"""Tests for the clone service module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from chegi.services.clone.clone_service import (
    CloneService,
    _parse_submodule_output,
    parse_url,
)
from chegi.services.clone.exceptions import CloneTargetExistsError, CloneUrlError
from chegi.services.clone.models import CloneConfig, CloneResult, CloneSource


class TestParseUrl:
    """Tests for parse_url function."""

    def test_parse_shorthand(self):
        """Tests that user/repo is expanded to GitHub HTTPS URL."""
        assert parse_url("user/repo") == "https://github.com/user/repo.git"

    def test_parse_shorthand_with_dots(self):
        """Tests that dotted shorthand is expanded correctly."""
        assert parse_url("my-org/my.repo") == "https://github.com/my-org/my.repo.git"

    def test_parse_https_unchanged(self):
        """Tests that full HTTPS URLs are kept as-is."""
        url = "https://github.com/user/repo.git"
        assert parse_url(url) == url

    def test_parse_ssh_unchanged(self):
        """Tests that SSH URLs are kept as-is."""
        url = "git@github.com:user/repo.git"
        assert parse_url(url) == url

    def test_parse_git_protocol_unchanged(self):
        """Tests that git:// URLs are kept as-is."""
        url = "git://example.com/repo.git"
        assert parse_url(url) == url

    def test_parse_empty_raises(self):
        """Tests that an empty URL raises CloneUrlError."""
        try:
            parse_url("")
            assert False, "Expected CloneUrlError"
        except CloneUrlError:
            pass

    def test_parse_invalid_raises(self):
        """Tests that garbage input raises CloneUrlError."""
        try:
            parse_url("not a url!!")
            assert False, "Expected CloneUrlError"
        except CloneUrlError:
            pass


class TestTargetDirName:
    """Tests for _target_dir_name."""

    def test_from_https(self):
        """Tests extracting name from HTTPS URL."""
        from chegi.services.clone.clone_service import _target_dir_name

        name = _target_dir_name("https://github.com/user/chegi.git")
        assert name == "chegi"

    def test_from_https_no_dot_git(self):
        """Tests extracting name from HTTPS URL without .git."""
        from chegi.services.clone.clone_service import _target_dir_name

        name = _target_dir_name("https://github.com/user/chegi")
        assert name == "chegi"

    def test_from_ssh(self):
        """Tests extracting name from SSH URL."""
        from chegi.services.clone.clone_service import _target_dir_name

        name = _target_dir_name("git@github.com:user/my-app.git")
        assert name == "my-app"


class TestCloneService:
    """Tests for CloneService."""

    def test_smart_detect_python(self, tmp_path: Path):
        """Tests detection of Python from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("")
        assert CloneService._smart_detect_techs(tmp_path) == ["python"]

    def test_smart_detect_javascript(self, tmp_path: Path):
        """Tests detection of JavaScript from package.json."""
        (tmp_path / "package.json").write_text("")
        assert CloneService._smart_detect_techs(tmp_path) == ["javascript"]

    def test_smart_detect_multiple(self, tmp_path: Path):
        """Tests detection of multiple technologies."""
        (tmp_path / "package.json").write_text("")
        (tmp_path / "Cargo.toml").write_text("")
        detected = CloneService._smart_detect_techs(tmp_path)
        assert "javascript" in detected
        assert "rust" in detected

    def test_smart_detect_none(self, tmp_path: Path):
        """Tests that no detection returns empty list."""
        assert CloneService._smart_detect_techs(tmp_path) == []

    def test_smart_detect_deduplicates(self, tmp_path: Path):
        """Tests that duplicate technologies are not returned."""
        (tmp_path / "pyproject.toml").write_text("")
        (tmp_path / "requirements.txt").write_text("")
        detected = CloneService._smart_detect_techs(tmp_path)
        assert detected == ["python"]

    @patch("chegi.services.clone.clone_service.InitService")
    @patch("chegi.services.clone.clone_service.EnvManager")
    @patch("chegi.services.clone.clone_service.GitClient")
    def test_execute_success(
        self,
        mock_git_client_cls: MagicMock,
        mock_env_mgr_cls: MagicMock,
        mock_init_svc: MagicMock,
        tmp_path: Path,
    ):
        """Tests that execute clones and detects branch."""
        mock_client = MagicMock()
        mock_client.run_command.return_value = "main"
        mock_git_client_cls.return_value = mock_client

        url = "https://github.com/user/test-repo.git"
        target = tmp_path / "test-repo"
        config = CloneConfig(
            url=url,
            source=CloneSource.EXTERNAL_URL,
            target_dir=target,
            repo_name="test-repo",
            chegi=False,
        )
        service = CloneService(config)
        result = service.execute()

        assert isinstance(result, CloneResult)
        assert result.target_dir == target
        assert result.repo_name == "test-repo"
        assert result.default_branch == "main"
        mock_client.clone.assert_called_once_with(
            url=url, target_dir=target, branch=None, depth=None
        )

    @patch("chegi.services.clone.clone_service.InitService")
    @patch("chegi.services.clone.clone_service.EnvManager")
    @patch("chegi.services.clone.clone_service.GitClient")
    def test_execute_with_submodules(
        self,
        mock_git_client_cls: MagicMock,
        mock_env_mgr_cls: MagicMock,
        mock_init_svc: MagicMock,
        tmp_path: Path,
    ):
        """Tests that execute detects .gitmodules and inits submodules."""
        mock_client = MagicMock()
        mock_client.run_command.return_value = "main"
        mock_client.submodule_update.return_value = (
            "Cloning into '/tmp/sub/foo'...\nCloning into '/tmp/sub/bar'..."
        )
        mock_git_client_cls.return_value = mock_client

        url = "https://github.com/user/test-repo.git"
        target = tmp_path / "test-repo"
        target.mkdir(parents=True)
        (target / ".gitmodules").write_text('[submodule "foo"]\n\tpath = foo')

        config = CloneConfig(
            url=url,
            source=CloneSource.EXTERNAL_URL,
            target_dir=target,
            repo_name="test-repo",
            chegi=False,
        )
        service = CloneService(config)
        # Patch _clone_repo to bypass safety check (target already exists)
        with patch.object(service, "_clone_repo") as mock_clone:
            mock_clone.return_value = CloneResult(
                target_dir=target, repo_name="test-repo"
            )
            result = service.execute()

        assert result.had_submodules is True
        assert len(result.submodules_inited) > 0
        mock_client.submodule_update.assert_called_once_with(recursive=True)

    @patch("chegi.services.clone.clone_service.InitService")
    @patch("chegi.services.clone.clone_service.EnvManager")
    @patch("chegi.services.clone.clone_service.GitClient")
    def test_execute_no_submodules_when_disabled(
        self,
        mock_git_client_cls: MagicMock,
        mock_env_mgr_cls: MagicMock,
        mock_init_svc: MagicMock,
        tmp_path: Path,
    ):
        """Tests that submodules are skipped when config.submodules is False."""
        mock_client = MagicMock()
        mock_client.run_command.return_value = "main"
        mock_git_client_cls.return_value = mock_client

        url = "https://github.com/user/test-repo.git"
        target = tmp_path / "test-repo"
        target.mkdir(parents=True)
        (target / ".gitmodules").write_text('[submodule "foo"]')

        config = CloneConfig(
            url=url,
            source=CloneSource.EXTERNAL_URL,
            target_dir=target,
            repo_name="test-repo",
            submodules=False,
            chegi=False,
        )
        service = CloneService(config)
        with patch.object(service, "_clone_repo") as mock_clone:
            mock_clone.return_value = CloneResult(
                target_dir=target, repo_name="test-repo"
            )
            result = service.execute()

        assert result.had_submodules is False
        mock_client.submodule_update.assert_not_called()

    @patch("chegi.services.clone.clone_service.InitService")
    @patch("chegi.services.clone.clone_service.EnvManager")
    @patch("chegi.services.clone.clone_service.GitClient")
    def test_execute_gitignore_created(
        self,
        mock_git_client_cls: MagicMock,
        mock_env_mgr_cls: MagicMock,
        mock_init_svc: MagicMock,
        tmp_path: Path,
    ):
        """Tests that .gitignore is created when missing and techs available."""
        mock_client = MagicMock()
        mock_client.run_command.return_value = "main"
        mock_git_client_cls.return_value = mock_client

        mock_env = MagicMock()
        mock_env_mgr_cls.return_value = mock_env

        url = "https://github.com/user/test-repo.git"
        target = tmp_path / "test-repo"

        config = CloneConfig(
            url=url,
            source=CloneSource.EXTERNAL_URL,
            target_dir=target,
            repo_name="test-repo",
            technologies=["python", "javascript"],
            chegi=False,
        )
        service = CloneService(config)
        with patch.object(service, "_clone_repo") as mock_clone:
            mock_clone.return_value = CloneResult(
                target_dir=target, repo_name="test-repo"
            )
            result = service.execute()

        assert result.gitignore_was_missing is True
        assert result.gitignore_created is True
        mock_env.generate_gitignore.assert_called_once_with(
            ["python", "javascript"], str(target)
        )

    @patch("chegi.services.clone.clone_service.InitService")
    @patch("chegi.services.clone.clone_service.EnvManager")
    @patch("chegi.services.clone.clone_service.GitClient")
    def test_execute_gitignore_skipped_when_exists(
        self,
        mock_git_client_cls: MagicMock,
        mock_env_mgr_cls: MagicMock,
        mock_init_svc: MagicMock,
        tmp_path: Path,
    ):
        """Tests that .gitignore creation is skipped when file already exists."""
        mock_client = MagicMock()
        mock_client.run_command.return_value = "main"
        mock_git_client_cls.return_value = mock_client

        url = "https://github.com/user/test-repo.git"
        target = tmp_path / "test-repo"

        config = CloneConfig(
            url=url,
            source=CloneSource.EXTERNAL_URL,
            target_dir=target,
            repo_name="test-repo",
            technologies=["python"],
            chegi=False,
        )
        service = CloneService(config)
        with patch.object(service, "_clone_repo") as mock_clone:
            mock_clone.return_value = CloneResult(
                target_dir=target, repo_name="test-repo"
            )
            # Create .gitignore in the target dir set by mock
            target.mkdir(parents=True)
            (target / ".gitignore").write_text("node_modules/\n")
            result = service.execute()

        assert result.gitignore_was_missing is False
        assert result.gitignore_created is False

    @patch("chegi.services.clone.clone_service.InitService")
    @patch("chegi.services.clone.clone_service.EnvManager")
    @patch("chegi.services.clone.clone_service.GitClient")
    def test_execute_chegi_created(
        self,
        mock_git_client_cls: MagicMock,
        mock_env_mgr_cls: MagicMock,
        mock_init_svc: MagicMock,
        tmp_path: Path,
    ):
        """Tests that .chegi/ directory is created."""
        mock_client = MagicMock()
        mock_client.run_command.return_value = "main"
        mock_git_client_cls.return_value = mock_client

        url = "https://github.com/user/test-repo.git"
        target = tmp_path / "test-repo"

        config = CloneConfig(
            url=url,
            source=CloneSource.EXTERNAL_URL,
            target_dir=target,
            repo_name="test-repo",
            chegi=True,
        )
        service = CloneService(config)
        with patch.object(service, "_clone_repo") as mock_clone:
            mock_clone.return_value = CloneResult(
                target_dir=target, repo_name="test-repo"
            )
            result = service.execute()

        assert result.chegi_created is True
        mock_init_svc.create_project_directory.assert_called_once_with(target)

    @patch("chegi.services.clone.clone_service.InitService")
    @patch("chegi.services.clone.clone_service.EnvManager")
    @patch("chegi.services.clone.clone_service.GitClient")
    def test_execute_chegi_skipped_when_disabled(
        self,
        mock_git_client_cls: MagicMock,
        mock_env_mgr_cls: MagicMock,
        mock_init_svc: MagicMock,
        tmp_path: Path,
    ):
        """Tests that .chegi/ is skipped when config.chegi is False."""
        mock_client = MagicMock()
        mock_client.run_command.return_value = "main"
        mock_git_client_cls.return_value = mock_client

        url = "https://github.com/user/test-repo.git"
        target = tmp_path / "test-repo"

        config = CloneConfig(
            url=url,
            source=CloneSource.EXTERNAL_URL,
            target_dir=target,
            repo_name="test-repo",
            chegi=False,
        )
        service = CloneService(config)
        with patch.object(service, "_clone_repo") as mock_clone:
            mock_clone.return_value = CloneResult(
                target_dir=target, repo_name="test-repo"
            )
            result = service.execute()

        assert result.chegi_created is False
        mock_init_svc.create_project_directory.assert_not_called()

    @patch("chegi.services.clone.clone_service.GitClient")
    def test_execute_target_exists_error(
        self,
        mock_git_client_cls: MagicMock,
        tmp_path: Path,
    ):
        """Tests that CloneTargetExistsError is raised for non-empty target."""
        url = "https://github.com/user/test-repo.git"
        target = tmp_path / "test-repo"
        target.mkdir(parents=True)
        (target / "some_file.txt").write_text("hello")

        config = CloneConfig(
            url=url,
            source=CloneSource.EXTERNAL_URL,
            target_dir=target,
            repo_name="test-repo",
        )
        service = CloneService(config)

        import pytest

        with pytest.raises(CloneTargetExistsError):
            service.execute()


class TestParseSubmoduleOutput:
    """Tests for _parse_submodule_output."""

    def test_parses_cloning_lines(self):
        """Tests extraction of submodule names from git output."""
        output = (
            "Cloning into '/home/user/proj/sub/foo'...\n"
            "Cloning into '/home/user/proj/sub/bar'...\n"
        )
        assert _parse_submodule_output(output) == ["foo", "bar"]

    def test_empty_output(self):
        """Tests that empty output returns empty list."""
        assert _parse_submodule_output("") == []

    def test_no_cloning_lines(self):
        """Tests output without Cloning lines returns placeholder."""
        assert _parse_submodule_output("Already up to date.") == ["<unknown>"]
