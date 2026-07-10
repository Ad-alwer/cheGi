"""Unit tests for the sync CLI command."""

from unittest.mock import patch

from typer.testing import CliRunner

from chegi.cli.main import app
from chegi.services.git.exceptions import GitCoreError

runner = CliRunner()


@patch("chegi.cli.commands.sync.SyncService")
@patch("chegi.cli.commands.sync.GitClient")
def test_sync_cli_clean_success(mock_git_client_class, mock_sync_service_class):
    mock_git_client = mock_git_client_class.return_value
    mock_git_client.is_workspace_clean.return_value = True

    mock_sync_service = mock_sync_service_class.return_value

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert "Repository synced successfully!" in result.stdout

    # Assert correct service methods were called
    mock_sync_service.stash_changes.assert_not_called()
    mock_sync_service.pull_rebase.assert_called_once()
    mock_sync_service.push_changes.assert_called_once()
    mock_sync_service.pop_stash.assert_not_called()


@patch("chegi.cli.commands.sync.SyncService")
@patch("chegi.cli.commands.sync.GitClient")
def test_sync_cli_dirty_success_with_stash(
    mock_git_client_class, mock_sync_service_class
):
    mock_git_client = mock_git_client_class.return_value
    mock_git_client.is_workspace_clean.return_value = False

    mock_sync_service = mock_sync_service_class.return_value

    # No input is needed anymore because stash is automatic
    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert "Workspace is not clean. Stashing changes" in result.stdout
    assert "Repository synced successfully!" in result.stdout
    assert "Popping stashed changes" in result.stdout

    # Assert stash and pop were handled properly
    mock_sync_service.stash_changes.assert_called_once()
    mock_sync_service.pull_rebase.assert_called_once()
    mock_sync_service.push_changes.assert_called_once()
    mock_sync_service.pop_stash.assert_called_once()


@patch("chegi.cli.commands.sync.SyncService")
@patch("chegi.cli.commands.sync.GitClient")
def test_sync_cli_failure_triggers_pop_stash(
    mock_git_client_class, mock_sync_service_class
):
    mock_git_client = mock_git_client_class.return_value
    mock_git_client.is_workspace_clean.return_value = False

    mock_sync_service = mock_sync_service_class.return_value
    # Simulate a pull failure
    mock_sync_service.pull_rebase.side_effect = GitCoreError("Pull rebase failed")

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "Sync Failed" in result.stdout
    assert "Pull rebase failed" in result.stdout

    # Assert stash was created, pull failed, push was skipped, BUT pop was still executed (finally block)
    mock_sync_service.stash_changes.assert_called_once()
    mock_sync_service.pull_rebase.assert_called_once()
    mock_sync_service.push_changes.assert_not_called()
    mock_sync_service.pop_stash.assert_called_once()
