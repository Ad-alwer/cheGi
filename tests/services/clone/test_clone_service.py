"""Tests for the clone service module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from chegi.services.clone.clone_service import CloneService, parse_url
from chegi.services.clone.exceptions import CloneUrlError
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

    @patch("chegi.services.clone.clone_service.GitClient")
    def test_execute_success(self, mock_git_client_cls: MagicMock, tmp_path: Path):
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
