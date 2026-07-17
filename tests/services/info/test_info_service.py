"""Tests for the InfoService class."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from chegi.services.info.info_service import InfoService
from chegi.services.info.models import InfoReport


class TestInfoServiceCollect:
    """Tests for InfoService.collect()."""

    def test_collect_not_a_git_repo(self, tmp_path: Path) -> None:
        """Test that collect() returns is_git_repo=False outside a git repo."""
        report = InfoService(tmp_path).collect()
        assert report.is_git_repo is False
        assert "git" in report.errors

    @patch("chegi.services.info.info_service.GitClient")
    def test_collect_clean_repo(self, mock_git_cls: MagicMock, tmp_path: Path) -> None:
        """Test that collect() returns clean state for a clean repo."""
        mock_git = MagicMock()
        mock_git.is_valid_repo.return_value = True
        mock_git_cls.return_value = mock_git

        _mock_git_clean(mock_git)

        report = InfoService(tmp_path).collect()
        assert report.is_git_repo is True
        assert report.branch == "main"
        assert report.ahead == 0
        assert report.behind == 0
        assert report.staged == 0
        assert report.modified == 0
        assert report.untracked == 0
        assert report.stash_count == 0
        assert report.last_commit is not None
        assert report.last_commit.hash == "abc1234"
        assert report.last_commit.author == "Ali"
        assert report.contributor_count == 3
        assert report.git_identity_set is True
        assert report.has_sensitive_files is False

    @patch("chegi.services.info.info_service.GitClient")
    def test_collect_dirty_repo(self, mock_git_cls: MagicMock, tmp_path: Path) -> None:
        """Test that collect() counts changes correctly."""
        mock_git = MagicMock()
        mock_git.is_valid_repo.return_value = True
        mock_git_cls.return_value = mock_git

        _setup_mock_git(mock_git, status_output=_DIRTY_STATUS)

        report = InfoService(tmp_path).collect()
        assert report.modified == 1, f"modified={report.modified}"
        assert report.staged == 1, f"staged={report.staged}"
        assert report.untracked == 1, f"untracked={report.untracked}"

    @patch("chegi.services.info.info_service.GitClient")
    def test_collect_ahead_behind(
        self, mock_git_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Test that collect() parses ahead/behind correctly."""
        mock_git = MagicMock()
        mock_git.is_valid_repo.return_value = True
        mock_git_cls.return_value = mock_git

        _setup_mock_git(mock_git, rev_list_output="3\t1")

        report = InfoService(tmp_path).collect()
        assert report.ahead == 3
        assert report.behind == 1

    @patch("chegi.services.info.info_service.GitClient")
    def test_collect_no_remote(self, mock_git_cls: MagicMock, tmp_path: Path) -> None:
        """Test that collect() handles no remote gracefully."""
        mock_git = MagicMock()
        mock_git.is_valid_repo.return_value = True
        mock_git_cls.return_value = mock_git

        _setup_mock_git(mock_git, remote_output="")

        report = InfoService(tmp_path).collect()
        assert report.remote_name is None
        assert report.ahead == 0
        assert report.behind == 0

    @patch("chegi.services.info.info_service.GitClient")
    def test_collect_no_identity(self, mock_git_cls: MagicMock, tmp_path: Path) -> None:
        """Test that collect() detects missing git identity."""
        mock_git = MagicMock()
        mock_git.is_valid_repo.return_value = True
        mock_git_cls.return_value = mock_git

        _setup_mock_git(mock_git, identity_name="", identity_email="")

        report = InfoService(tmp_path).collect()
        assert report.git_identity_set is False

    @patch("chegi.services.info.info_service.GitClient")
    def test_collect_with_tag(self, mock_git_cls: MagicMock, tmp_path: Path) -> None:
        """Test that collect() finds the latest tag and commits since."""
        mock_git = MagicMock()
        mock_git.is_valid_repo.return_value = True
        mock_git_cls.return_value = mock_git

        _setup_mock_git(mock_git, tag_output="v0.2.0", since_output="12")

        report = InfoService(tmp_path).collect()
        assert report.latest_tag == "v0.2.0"
        assert report.commits_since_tag == 12

    @patch("chegi.services.info.info_service.GitClient")
    def test_collect_no_tag(self, mock_git_cls: MagicMock, tmp_path: Path) -> None:
        """Test that collect() handles no tags gracefully."""
        mock_git = MagicMock()
        mock_git.is_valid_repo.return_value = True
        mock_git_cls.return_value = mock_git

        _setup_mock_git(mock_git, tag_raises=True)

        report = InfoService(tmp_path).collect()
        assert report.latest_tag is None
        assert report.commits_since_tag == 0

    @patch("chegi.services.info.info_service.GitClient")
    @patch("chegi.services.info.info_service.SecurityGuard")
    def test_collect_sensitive_files(
        self, mock_guard: MagicMock, mock_git_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Test that collect() detects sensitive files."""
        mock_git = MagicMock()
        mock_git.is_valid_repo.return_value = True
        mock_git_cls.return_value = mock_git
        _mock_git_clean(mock_git)

        mock_guard.scan_repo.return_value = MagicMock(
            is_safe=False, sensitive_files=[".env", "key.pem"]
        )

        report = InfoService(tmp_path).collect()
        assert report.has_sensitive_files is True
        assert report.sensitive_file_count == 2

    @patch("chegi.services.info.info_service.GitClient")
    @patch("chegi.services.info.info_service.HooksService")
    def test_collect_hooks_installed(
        self, mock_hooks_cls: MagicMock, mock_git_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Test that collect() detects installed hooks."""
        mock_git = MagicMock()
        mock_git.is_valid_repo.return_value = True
        mock_git_cls.return_value = mock_git
        _mock_git_clean(mock_git)

        mock_hook_info = MagicMock()
        mock_hook_info.installed = True
        mock_hooks = MagicMock()
        mock_hooks.is_installed.return_value = mock_hook_info
        mock_hooks_cls.return_value = mock_hooks

        report = InfoService(tmp_path).collect()
        assert report.has_hooks is True

    @patch("chegi.services.info.info_service.GitClient")
    def test_collect_stash_count(self, mock_git_cls: MagicMock, tmp_path: Path) -> None:
        """Test that collect() counts stashes."""
        mock_git = MagicMock()
        mock_git.is_valid_repo.return_value = True
        mock_git_cls.return_value = mock_git

        _setup_mock_git(mock_git, stash_output="stash@{0}\nstash@{1}")

        report = InfoService(tmp_path).collect()
        assert report.stash_count == 2


class TestInfoServiceToJson:
    """Tests for InfoService.to_json()."""

    def test_to_json_returns_dict(self) -> None:
        """Test that to_json() returns a serializable dict."""
        service = InfoService()
        report = InfoReport(path=Path("/test"), is_git_repo=True, branch="main")
        data = service.to_json(report)
        assert data["is_git_repo"] is True
        assert data["branch"] == "main"
        assert data["path"] == "/test"

    def test_to_json_not_git(self) -> None:
        """Test that to_json() works for non-git repos."""
        service = InfoService()
        report = InfoReport(path=Path("/tmp"), is_git_repo=False)
        data = service.to_json(report)
        assert data["is_git_repo"] is False
        assert "branch" not in data


class TestInfoServiceToShort:
    """Tests for InfoService.to_short()."""

    def test_to_short_not_git(self) -> None:
        """Test that to_short() returns error message for non-git."""
        service = InfoService()
        report = InfoReport(path=Path("/tmp"), is_git_repo=False)
        result = service.to_short(report)
        assert "Not a git repository" in result

    def test_to_short_clean(self) -> None:
        """Test that to_short() returns clean status."""
        service = InfoService()
        report = InfoReport(path=Path("/test"), is_git_repo=True, branch="main")
        result = service.to_short(report)
        assert "main" in result
        assert "clean" in result

    def test_to_short_with_changes(self) -> None:
        """Test that to_short() shows change count."""
        service = InfoService()
        report = InfoReport(
            path=Path("/test"),
            is_git_repo=True,
            branch="main",
            modified=2,
            staged=1,
        )
        result = service.to_short(report)
        assert "3 changed" in result


# --- Helpers ---

_CLEAN_STATUS = ""
_DIRTY_STATUS = " M file1.py\nM  file2.py\n?? file3.py"


def _mock_git_clean(mock_git: MagicMock) -> None:
    """Configures mock git for a clean repo state.

    Args:
        mock_git: The mock GitClient instance.
    """
    _setup_mock_git(mock_git)


def _setup_mock_git(
    mock_git: MagicMock,
    status_output: str = _CLEAN_STATUS,
    rev_list_output: str = "0\t0",
    remote_output: str = "origin",
    remote_url: str = "git@github.com:user/repo.git",
    identity_name: str = "Ali",
    identity_email: str = "ali@example.com",
    branch: str = "main",
    log_output: str = "abc1234\nAli\n2 hours ago\nfix: typo",
    shortlog_output: str = "     5\tAli\n     3\tSara\n     1\tReza",
    tag_output: str = "",
    since_output: str = "",
    tag_raises: bool = False,
    stash_output: str = "",
) -> None:
    """Configures a mock GitClient with the given outputs.

    Args:
        mock_git: The mock GitClient instance.
        status_output: Output of git status --porcelain.
        rev_list_output: Output of rev-list ahead/behind.
        remote_output: Output of git remote.
        remote_url: Output of git remote get-url.
        identity_name: Output of git config user.name.
        identity_email: Output of git config user.email.
        branch: Output of git branch --show-current.
        log_output: Output of git log -1.
        shortlog_output: Output of git shortlog -sn HEAD.
        tag_output: Output of git describe --tags.
        since_output: Output of rev-list --count tag..HEAD.
        tag_raises: If True, git describe raises GitCommandError.
        stash_output: Output of git stash list.
    """

    def run_command_side_effect(cmd, check=True, **kwargs):
        cmd_str = " ".join(cmd)
        if "status --porcelain" in cmd_str:
            return status_output
        if "rev-list --left-right" in cmd_str:
            return rev_list_output
        if "remote" in cmd_str and "get-url" in cmd_str:
            return remote_url
        if cmd == ["git", "remote"]:
            return remote_output
        if "branch --show-current" in cmd_str:
            return branch
        if "config user.name" in cmd_str:
            return identity_name
        if "config user.email" in cmd_str:
            return identity_email
        if "stash list" in cmd_str:
            return stash_output
        if "log" in cmd_str and "-1" in cmd_str:
            return log_output
        if "shortlog" in cmd_str:
            return shortlog_output
        if "describe" in cmd_str:
            if tag_raises:
                from chegi.services.git.exceptions import GitCommandError

                raise GitCommandError(cmd, 128, "fatal: no tags")
            return tag_output
        if "rev-list --count" in cmd_str and "..HEAD" in cmd_str:
            return since_output
        return ""

    mock_git.run_command.side_effect = run_command_side_effect
