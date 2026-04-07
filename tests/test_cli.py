from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

# Updated import to point to the new main architecture
from chegi.cli.main import app

# Initialize the CLI Runner for testing
runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_valid_git_env():
    """Automatically mocks the Git environment check to pass for all tests."""
    with patch("chegi.cli.check_git_environment") as mock_check:
        mock_check.return_value = (True, "")
        yield mock_check


# ==========================================
# Gitignore Command Tests
# ==========================================


@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
def test_gitignore_success_without_commit(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests successful .gitignore creation but user declines commit."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = ["python", "node"]
    mock_instance.has_existing_gitignore.return_value = False
    mock_instance.is_git_repo.return_value = True

    mock_checkbox.return_value.ask.return_value = ["Python"]

    result = runner.invoke(app, ["gitignore"], input="n\n")

    assert result.exit_code == 0
    assert "Created:" in result.stdout
    assert "Skipping commit" in result.stdout
    mock_instance.generate_gitignore.assert_called_once_with(["python"], ".")
    mock_instance.commit_gitignore.assert_not_called()


@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
def test_gitignore_success_with_commit(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests .gitignore creation with user accepting the automatic commit."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = ["python"]
    mock_instance.has_existing_gitignore.return_value = False
    mock_instance.is_git_repo.return_value = True
    mock_instance.commit_gitignore.return_value = "chore(gitignore): auto add..."

    mock_checkbox.return_value.ask.return_value = ["Python"]

    result = runner.invoke(app, ["gitignore"], input="y\n")

    assert result.exit_code == 0
    assert "Committed with message:" in result.stdout
    mock_instance.commit_gitignore.assert_called_once_with(".")


@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
@patch("chegi.cli.Confirm.ask")
def test_gitignore_overwrite_abort(
    mock_confirm: MagicMock, mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests that the command asks before overwriting and aborts if declined."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = ["python"]
    mock_instance.has_existing_gitignore.return_value = True

    mock_checkbox.return_value.ask.return_value = ["Python"]
    mock_confirm.return_value = False

    result = runner.invoke(app, ["gitignore"])

    assert result.exit_code == 0
    assert "Aborted" in result.stdout
    mock_instance.generate_gitignore.assert_not_called()


@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
def test_gitignore_multiple_languages(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests if multiple selected templates are correctly passed to EnvManager."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = ["python", "node", "ruby"]
    mock_instance.has_existing_gitignore.return_value = False

    mock_checkbox.return_value.ask.return_value = ["Python", "Node"]

    result = runner.invoke(app, ["gitignore"], input="n\n")

    assert result.exit_code == 0
    mock_instance.generate_gitignore.assert_called_once_with(["python", "node"], ".")


@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
def test_gitignore_no_selection_abort(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests the command behavior when the user cancels or selects no languages."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = ["python"]

    mock_checkbox.return_value.ask.return_value = []

    result = runner.invoke(app, ["gitignore"])

    assert result.exit_code == 1
    assert "cancelled or no technologies selected" in result.stdout
    mock_instance.generate_gitignore.assert_not_called()


@patch("chegi.cli.EnvManager")
def test_gitignore_no_templates_found(mock_env_manager: MagicMock):
    """Tests exit with error if no gitignore templates are found in the database."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = []

    result = runner.invoke(app, ["gitignore"])

    assert result.exit_code == 1
    assert "No gitignore templates found" in result.stdout


@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
def test_gitignore_not_a_git_repo(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests that the commit prompt is skipped if the target is not a git repository."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = ["python"]
    mock_instance.has_existing_gitignore.return_value = False
    mock_instance.is_git_repo.return_value = False

    mock_checkbox.return_value.ask.return_value = ["Python"]

    result = runner.invoke(app, ["gitignore"])

    assert result.exit_code == 0
    assert "Skipped commit: Not a git repository" in result.stdout
    mock_instance.commit_gitignore.assert_not_called()
