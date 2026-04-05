"""Unit tests for Git synchronization operations and error handling in SyncService."""

import pytest
from unittest.mock import MagicMock

from chegi.services.sync.sync_service import SyncService
from chegi.services.sync.exceptions import SyncError

@pytest.fixture
def mock_git_client():
    return MagicMock()

@pytest.fixture
def sync_service(mock_git_client):
    return SyncService(git_client=mock_git_client)

def test_stash_changes(sync_service, mock_git_client):
    sync_service.stash_changes()
    mock_git_client.run_command.assert_called_once_with(
        ["git", "stash", "push", "-m", "cheGi auto-stash"]
    )

def test_pop_stash(sync_service, mock_git_client):
    sync_service.pop_stash()
    mock_git_client.run_command.assert_called_once_with(["git", "stash", "pop"])

def test_pull_rebase_success(sync_service, mock_git_client):
    sync_service.pull_rebase()
    mock_git_client.run_command.assert_called_once_with(["git", "pull", "--rebase"])

def test_pull_rebase_failure_triggers_abort(sync_service, mock_git_client):
    # Pass a list to side_effect: 
    # 1st call (git pull) raises Exception, 2nd call (git rebase --abort) returns None (success)
    mock_git_client.run_command.side_effect = [Exception("Merge conflict"), None]
    
    with pytest.raises(SyncError) as exc_info:
        sync_service.pull_rebase()
        
    assert "Pull rebase failed" in str(exc_info.value)
    assert "Merge conflict" in str(exc_info.value)
    mock_git_client.run_command.assert_any_call(["git", "rebase", "--abort"], check=False)

def test_push_changes_success(sync_service, mock_git_client):
    sync_service.push_changes()
    mock_git_client.run_command.assert_called_once_with(["git", "push"])

def test_push_changes_failure(sync_service, mock_git_client):
    mock_git_client.run_command.side_effect = Exception("Remote rejected")
    
    with pytest.raises(SyncError) as exc_info:
        sync_service.push_changes()
        
    assert "Push failed" in str(exc_info.value)
    assert "Remote rejected" in str(exc_info.value)
