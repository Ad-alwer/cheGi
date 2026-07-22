"""Tests for the GitConfigService class."""

from unittest.mock import MagicMock, patch

import pytest

from chegi.services.git_config.exceptions import GitConfigError
from chegi.services.git_config.models import (
    CATEGORY_MAP,
    GitConfigCategory,
    GitConfigEntry,
    categorize_key,
)
from chegi.services.git_config.service import GitConfigService


class TestCategorizeKey:
    """Tests for the categorize_key helper function."""

    def test_user_key(self) -> None:
        """Test that user keys are categorized correctly."""
        assert categorize_key("user.name") == GitConfigCategory.USER
        assert categorize_key("user.email") == GitConfigCategory.USER

    def test_core_key(self) -> None:
        """Test that core keys are categorized correctly."""
        assert categorize_key("core.editor") == GitConfigCategory.CORE

    def test_alias_key(self) -> None:
        """Test that alias keys are categorized correctly."""
        assert categorize_key("alias.co") == GitConfigCategory.ALIAS

    def test_credential_key(self) -> None:
        """Test that credential keys are categorized correctly."""
        assert categorize_key("credential.helper") == GitConfigCategory.CREDENTIAL

    def test_init_key(self) -> None:
        """Test that init keys are categorized correctly."""
        assert categorize_key("init.defaultBranch") == GitConfigCategory.INIT

    def test_pull_key(self) -> None:
        """Test that pull keys are categorized correctly."""
        assert categorize_key("pull.rebase") == GitConfigCategory.PULL

    def test_fetch_key(self) -> None:
        """Test that fetch keys are categorized correctly."""
        assert categorize_key("fetch.prune") == GitConfigCategory.FETCH

    def test_unknown_key(self) -> None:
        """Test that unknown keys default to OTHER category."""
        assert categorize_key("unknown.key") == GitConfigCategory.OTHER


class TestGitConfigEntry:
    """Tests for the GitConfigEntry dataclass."""

    def test_entry_auto_categorizes(self) -> None:
        """Test that entry automatically assigns category based on key."""
        entry = GitConfigEntry(key="user.name", value="Test User")
        assert entry.category == GitConfigCategory.USER

    def test_entry_core_category(self) -> None:
        """Test that core.editor is categorized as CORE."""
        entry = GitConfigEntry(key="core.editor", value="vim")
        assert entry.category == GitConfigCategory.CORE


class TestGitConfigServiceGetAll:
    """Tests for GitConfigService.get_all()."""

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_get_all_returns_entries(self, mock_run: MagicMock) -> None:
        """Test that get_all parses git config output into entries."""
        mock_run.return_value = MagicMock(
            stdout="user.name=Test User\nuser.email=test@example.com\n",
            returncode=0,
        )
        entries = GitConfigService.get_all()
        assert len(entries) == 2
        assert entries[0].key == "user.name"
        assert entries[0].value == "Test User"

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_get_all_skips_empty_lines(self, mock_run: MagicMock) -> None:
        """Test that get_all skips empty lines."""
        mock_run.return_value = MagicMock(
            stdout="user.name=Test\n\n\nuser.email=test@test.com\n",
            returncode=0,
        )
        entries = GitConfigService.get_all()
        assert len(entries) == 2

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_get_all_empty_output(self, mock_run: MagicMock) -> None:
        """Test that get_all handles empty output."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        entries = GitConfigService.get_all()
        assert entries == []

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_get_all_git_not_installed(self, mock_run: MagicMock) -> None:
        """Test that get_all raises GitConfigError when git is missing."""
        mock_run.side_effect = FileNotFoundError
        with pytest.raises(GitConfigError, match="Git is not installed"):
            GitConfigService.get_all()


class TestGitConfigServiceGet:
    """Tests for GitConfigService.get()."""

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_get_returns_value(self, mock_run: MagicMock) -> None:
        """Test that get returns the config value."""
        mock_run.return_value = MagicMock(stdout="Test User\n", returncode=0)
        result = GitConfigService.get("user.name")
        assert result == "Test User"

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_get_returns_none_when_not_set(self, mock_run: MagicMock) -> None:
        """Test that get returns None when key is not set."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = GitConfigService.get("nonexistent.key")
        assert result is None

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_get_returns_none_on_error(self, mock_run: MagicMock) -> None:
        """Test that get returns None on git config error."""
        mock_run.side_effect = GitConfigError("failed")
        result = GitConfigService.get("user.name")
        assert result is None


class TestGitConfigServiceSet:
    """Tests for GitConfigService.set()."""

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_set_calls_git_config(self, mock_run: MagicMock) -> None:
        """Test that set calls git config with correct args."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        GitConfigService.set("user.name", "New Name")
        mock_run.assert_called_once_with(
            ["git", "config", "--global", "user.name", "New Name"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_set_raises_on_failure(self, mock_run: MagicMock) -> None:
        """Test that set raises GitConfigError on failure."""
        mock_run.side_effect = GitConfigError("permission denied")
        with pytest.raises(GitConfigError, match="permission denied"):
            GitConfigService.set("user.name", "value")


class TestGitConfigServiceUnset:
    """Tests for GitConfigService.unset()."""

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_unset_calls_git_config(self, mock_run: MagicMock) -> None:
        """Test that unset calls git config --unset-all."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        GitConfigService.unset("user.name")
        mock_run.assert_called_once_with(
            ["git", "config", "--global", "--unset-all", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_unset_swallows_error(self, mock_run: MagicMock) -> None:
        """Test that unset does not raise when key doesn't exist."""
        mock_run.side_effect = GitConfigError("key not found")
        GitConfigService.unset("nonexistent.key")


class TestGitConfigServiceIdentity:
    """Tests for GitConfigService identity methods."""

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_set_identity(self, mock_run: MagicMock) -> None:
        """Test that set_identity sets both name and email."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        GitConfigService.set_identity("Test", "test@test.com")
        assert mock_run.call_count == 2

    @patch("chegi.services.git_config.service.subprocess.run")
    def test_get_identity(self, mock_run: MagicMock) -> None:
        """Test that get_identity returns name and email tuple."""
        mock_run.return_value = MagicMock(stdout="Test User\n", returncode=0)
        name, email = GitConfigService.get_identity()
        assert name == "Test User"
        assert email == "Test User"


class TestGitConfigServiceToDict:
    """Tests for GitConfigService.to_dict()."""

    def test_to_dict(self) -> None:
        """Test that to_dict converts entries to flat dict."""
        entries = [
            GitConfigEntry(key="user.name", value="Test"),
            GitConfigEntry(key="user.email", value="test@test.com"),
        ]
        result = GitConfigService.to_dict(entries)
        assert result == {"user.name": "Test", "user.email": "test@test.com"}

    def test_to_dict_empty(self) -> None:
        """Test that to_dict handles empty list."""
        result = GitConfigService.to_dict([])
        assert result == {}
