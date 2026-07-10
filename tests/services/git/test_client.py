"""Core Git client tests."""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chegi.services.git.client import GitClient
from chegi.services.git.exceptions import GitCommandError, GitNotInstalledError


@pytest.fixture
def git_client():
    # Initialize with a dummy path for testing
    return GitClient(repo_path=Path("/fake/repo"))


@patch("subprocess.run")
def test_run_command_success(mock_run, git_client):
    # Mock subprocess success
    mock_result = MagicMock()
    mock_result.stdout = "mocked output\n"
    mock_run.return_value = mock_result

    output = git_client.run_command(["git", "status"])

    assert output == "mocked output"
    mock_run.assert_called_once()
    call_args, call_kwargs = mock_run.call_args
    assert call_args[0] == ["git", "status"]
    assert call_kwargs["cwd"] == Path("/fake/repo")
    assert call_kwargs["capture_output"] is True
    assert call_kwargs["text"] is True
    assert call_kwargs["check"] is True
    assert call_kwargs["env"] is not None
    assert "PATH" in call_kwargs["env"]


@patch("subprocess.run")
def test_run_command_called_process_error(mock_run, git_client):
    # Mock subprocess failure with exit code
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=["git", "status"], stderr="some error occurred"
    )

    with pytest.raises(GitCommandError) as exc_info:
        git_client.run_command(["git", "status"])

    assert "some error occurred" in str(exc_info.value)


@patch("subprocess.run")
def test_run_command_file_not_found(mock_run, git_client):
    # Mock missing git executable
    mock_run.side_effect = FileNotFoundError()

    with pytest.raises(GitNotInstalledError) as exc_info:
        git_client.run_command(["git", "status"])

    assert "Git executable not found" in str(exc_info.value)


@patch.object(GitClient, "run_command")
def test_check_git_installation_success(mock_run_command, git_client):
    # If run_command does not raise, it's installed
    mock_run_command.return_value = "git version 2.34.1"
    assert git_client.check_git_installation() is True


@patch.object(GitClient, "run_command")
def test_check_git_installation_failure(mock_run_command, git_client):
    # Simulate git not installed error from run_command
    mock_run_command.side_effect = GitNotInstalledError("Not installed")

    with pytest.raises(GitNotInstalledError):
        git_client.check_git_installation()


@patch.object(GitClient, "run_command")
def test_is_workspace_clean_true(mock_run_command, git_client):
    # Empty output from porcelain means clean workspace
    mock_run_command.return_value = ""
    assert git_client.is_workspace_clean() is True


@patch.object(GitClient, "run_command")
def test_is_workspace_clean_false(mock_run_command, git_client):
    # Any output means dirty workspace
    mock_run_command.return_value = " M file.py"
    assert git_client.is_workspace_clean() is False


@patch.object(GitClient, "run_command")
def test_is_valid_repo_true(mock_run_command, git_client):
    # Command success means it is a valid repo
    mock_run_command.return_value = "true"
    assert git_client.is_valid_repo() is True
    mock_run_command.assert_called_once_with(
        ["git", "rev-parse", "--is-inside-work-tree"]
    )


@patch.object(GitClient, "run_command")
def test_is_valid_repo_false_not_a_repo(mock_run_command, git_client):
    # Command error implies not inside a git repository
    mock_run_command.side_effect = GitCommandError("fatal: not a git repository")
    assert git_client.is_valid_repo() is False


@patch.object(GitClient, "run_command")
def test_is_valid_repo_false_git_not_installed(mock_run_command, git_client):
    # Missing git executable also means not a valid repo context
    mock_run_command.side_effect = GitNotInstalledError("Git executable not found")
    assert git_client.is_valid_repo() is False
