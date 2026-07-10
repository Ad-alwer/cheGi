from unittest.mock import MagicMock

import pytest

from chegi.services.git.client import GitClient
from chegi.services.git.exceptions import GitCommandError
from chegi.services.reword.reword_service import RewordService


@pytest.fixture
def mock_git_client():
    """Provides a mocked GitClient."""
    client = MagicMock(spec=GitClient)
    return client


@pytest.fixture
def reword_service(mock_git_client):
    """Provides an instance of RewordService with mocked dependencies."""
    return RewordService(mock_git_client)


class TestCalculatePagination:
    def test_start_and_end_valid(self, reword_service):
        skip, limit = reword_service.calculate_pagination(last=None, start=2, end=5)
        assert skip == 2
        assert limit == 3

    def test_start_and_end_invalid(self, reword_service):
        with pytest.raises(ValueError, match="--start must be less than --end"):
            reword_service.calculate_pagination(last=None, start=5, end=2)

    def test_only_start(self, reword_service):
        skip, limit = reword_service.calculate_pagination(last=None, start=3, end=None)
        assert skip == 3
        assert limit == 10

    def test_only_end_greater_than_10(self, reword_service):
        skip, limit = reword_service.calculate_pagination(last=None, start=None, end=15)
        assert skip == 5
        assert limit == 10

    def test_only_end_less_than_10(self, reword_service):
        skip, limit = reword_service.calculate_pagination(last=None, start=None, end=8)
        assert skip == 0
        assert limit == 8

    def test_only_last(self, reword_service):
        skip, limit = reword_service.calculate_pagination(last=7, start=None, end=None)
        assert skip == 0
        assert limit == 7

    def test_defaults(self, reword_service):
        skip, limit = reword_service.calculate_pagination(
            last=None, start=None, end=None
        )
        assert skip == 0
        assert limit == 10


class TestGitOperations:
    def test_get_commits_success(self, reword_service, mock_git_client):
        # Mocking git log output with an empty trailing line to test filtering
        mock_git_client.run_command.return_value = (
            "abc1234 First msg\ndef5678 Second msg\n"
        )

        commits = reword_service.get_commits(skip=2, limit=5)

        mock_git_client.run_command.assert_called_once_with(
            ["git", "log", "--max-count=5", "--skip=2", "--format=%h %s"]
        )
        assert len(commits) == 2
        assert commits[0] == "abc1234 First msg"
        assert commits[1] == "def5678 Second msg"

    def test_get_commits_error(self, reword_service, mock_git_client):
        mock_git_client.run_command.side_effect = Exception("git error")
        with pytest.raises(GitCommandError, match="Failed to fetch git history"):
            reword_service.get_commits(0, 10)

    def test_is_head_true(self, reword_service, mock_git_client):
        mock_git_client.run_command.return_value = "abc1234"
        assert reword_service.is_head("abc1234") is True

    def test_is_head_false(self, reword_service, mock_git_client):
        mock_git_client.run_command.return_value = "def5678"
        assert reword_service.is_head("abc1234") is False

    def test_is_head_error(self, reword_service, mock_git_client):
        mock_git_client.run_command.side_effect = Exception("git error")
        with pytest.raises(GitCommandError, match="Failed to resolve HEAD"):
            reword_service.is_head("abc1234")

    def test_get_commit_message_success(self, reword_service, mock_git_client):
        mock_git_client.run_command.return_value = "Original commit message"
        msg = reword_service.get_commit_message("abc1234")

        mock_git_client.run_command.assert_called_once_with(
            ["git", "log", "--format=%B", "-n", "1", "abc1234"]
        )
        assert msg == "Original commit message"

    def test_get_commit_message_error(self, reword_service, mock_git_client):
        mock_git_client.run_command.side_effect = Exception("git error")
        with pytest.raises(GitCommandError, match="Failed to fetch commit message"):
            reword_service.get_commit_message("abc1234")

    def test_amend_head_success(self, reword_service, mock_git_client):
        reword_service.amend_head("New msg")
        mock_git_client.run_command.assert_called_once_with(
            ["git", "commit", "--amend", "-m", "New msg"]
        )

    def test_amend_head_error(self, reword_service, mock_git_client):
        mock_git_client.run_command.side_effect = Exception("git error")
        with pytest.raises(GitCommandError, match="Failed to amend HEAD commit"):
            reword_service.amend_head("New msg")


class TestHashValidation:
    def test_validate_hash_valid_short(self, reword_service):
        reword_service._validate_hash("abc1234")

    def test_validate_hash_valid_long(self, reword_service):
        reword_service._validate_hash("abcdef0123456789abcdef0123456789abcdef01")

    def test_validate_hash_head(self, reword_service):
        reword_service._validate_hash("HEAD")

    def test_validate_hash_invalid_chars(self, reword_service):
        with pytest.raises(ValueError, match="Invalid commit hash format"):
            reword_service._validate_hash("abc123; rm -rf /")

    def test_validate_hash_empty(self, reword_service):
        with pytest.raises(ValueError, match="Invalid commit hash format"):
            reword_service._validate_hash("")

    def test_validate_hash_too_short(self, reword_service):
        with pytest.raises(ValueError, match="Invalid commit hash format"):
            reword_service._validate_hash("abc123")

    def test_is_head_rejects_invalid_hash(self, reword_service):
        with pytest.raises(ValueError, match="Invalid commit hash format"):
            reword_service.is_head("abc'; echo pwned #")

    def test_get_commit_message_rejects_invalid_hash(self, reword_service):
        with pytest.raises(ValueError, match="Invalid commit hash format"):
            reword_service.get_commit_message("abc'; rm -rf / #")

    def test_perform_automated_rebase_rejects_invalid_hash(
        self, reword_service, mock_git_client
    ):
        with pytest.raises(ValueError, match="Invalid commit hash format"):
            reword_service.perform_automated_rebase("abc'; pwn #", "new msg")


class TestAutomatedRebase:
    def test_perform_automated_rebase_success(self, reword_service, mock_git_client):
        target_hash = "abc1234"
        new_message = "Updated message via rebase"

        reword_service.perform_automated_rebase(target_hash, new_message)

        # Verify 3 git commands were executed in order
        assert mock_git_client.run_command.call_count == 3

        call_args = mock_git_client.run_command.call_args_list

        # 1. Start interactive rebase
        rebase_start_args = call_args[0]
        assert rebase_start_args.args[0] == ["git", "rebase", "-i", f"{target_hash}~1"]
        assert "env" in rebase_start_args.kwargs
        assert target_hash in rebase_start_args.kwargs["env"]["GIT_SEQUENCE_EDITOR"]

        # 2. Amend commit
        amend_args = call_args[1]
        assert amend_args.args[0] == ["git", "commit", "--amend", "-m", new_message]

        # 3. Continue rebase
        rebase_continue_args = call_args[2]
        assert rebase_continue_args.args[0] == ["git", "rebase", "--continue"]

    def test_perform_automated_rebase_abort_on_error(
        self, reword_service, mock_git_client
    ):
        # Simulate a failure during the second step (commit --amend)
        mock_git_client.run_command.side_effect = [None, Exception("conflict"), None]

        with pytest.raises(GitCommandError, match="Automated rebase failed"):
            reword_service.perform_automated_rebase("abc1234", "New msg")

        # Ensure 'git rebase --abort' was called to clean up
        mock_git_client.run_command.assert_called_with(
            ["git", "rebase", "--abort"], check=False
        )
