from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from chegi.cli.main import app
from chegi.config import GITIGNORE_COMMIT_MESSAGE

runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_preflight():
    """Automatically mocks the preflight checks to pass for all tests."""
    with patch("chegi.cli.main.run_preflight_checks") as mock_check:
        yield mock_check


@patch("chegi.cli.commands.gitignore.GitClient")
@patch("chegi.cli.commands.gitignore.EnvManager")
@patch("chegi.cli.commands.gitignore.questionary.checkbox")
def test_gitignore_success_without_commit(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock, mock_git_client: MagicMock
):
    """Tests successful .gitignore creation but user declines commit."""
    mock_env_instance = mock_env_manager.return_value
    mock_env_instance.get_envs_with_gitignore.return_value = ["python", "node"]
    mock_env_instance.has_existing_gitignore.return_value = False

    mock_git_instance = mock_git_client.return_value
    mock_git_instance.is_valid_repo.return_value = True

    mock_checkbox.return_value.ask.return_value = ["Python"]

    result = runner.invoke(app, ["gitignore"], input="n\n")

    assert result.exit_code == 0
    assert "Created:" in result.stdout
    assert "Skipping commit" in result.stdout
    mock_env_instance.generate_gitignore.assert_called_once()
    mock_git_instance.commit_file.assert_not_called()


@patch("chegi.cli.commands.gitignore.GitClient")
@patch("chegi.cli.commands.gitignore.EnvManager")
@patch("chegi.cli.commands.gitignore.questionary.checkbox")
def test_gitignore_success_with_commit(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock, mock_git_client: MagicMock
):
    mock_env_instance = mock_env_manager.return_value
    mock_env_instance.get_envs_with_gitignore.return_value = ["python"]
    mock_env_instance.has_existing_gitignore.return_value = False

    mock_git_instance = mock_git_client.return_value
    mock_git_instance.is_valid_repo.return_value = True

    mock_checkbox.return_value.ask.return_value = ["Python"]

    result = runner.invoke(app, ["gitignore"], input="y\n")

    assert result.exit_code == 0
    assert "Committed with message:" in result.stdout
    mock_git_instance.commit_file.assert_called_once_with(
        ".gitignore", GITIGNORE_COMMIT_MESSAGE
    )


@patch("chegi.cli.commands.gitignore.EnvManager")
@patch("chegi.cli.commands.gitignore.questionary.checkbox")
@patch("chegi.cli.commands.gitignore.Confirm.ask")
def test_gitignore_overwrite_abort(
    mock_confirm: MagicMock, mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests that the command asks before overwriting and aborts if declined."""
    mock_env_instance = mock_env_manager.return_value
    mock_env_instance.get_envs_with_gitignore.return_value = ["python"]
    mock_env_instance.has_existing_gitignore.return_value = True

    mock_checkbox.return_value.ask.return_value = ["Python"]
    mock_confirm.return_value = False

    result = runner.invoke(app, ["gitignore"])

    assert result.exit_code == 1
    assert "Aborted" in result.stdout
    mock_env_instance.generate_gitignore.assert_not_called()


@patch("chegi.cli.commands.gitignore.EnvManager")
@patch("chegi.cli.commands.gitignore.questionary.checkbox")
def test_gitignore_multiple_languages(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests if multiple selected templates are correctly passed to EnvManager."""
    mock_env_instance = mock_env_manager.return_value
    mock_env_instance.get_envs_with_gitignore.return_value = ["python", "node", "ruby"]
    mock_env_instance.has_existing_gitignore.return_value = False

    mock_checkbox.return_value.ask.return_value = ["Python", "Node"]

    result = runner.invoke(app, ["gitignore"], input="n\n")

    assert result.exit_code == 0
    # verify that the languages are passed as lowercase list
    args, _ = mock_env_instance.generate_gitignore.call_args
    assert args[0] == ["python", "node"]


@patch("chegi.cli.commands.gitignore.EnvManager")
@patch("chegi.cli.commands.gitignore.questionary.checkbox")
def test_gitignore_no_selection_abort(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests the command behavior when the user cancels or selects no languages."""
    mock_env_instance = mock_env_manager.return_value
    mock_env_instance.get_envs_with_gitignore.return_value = ["python"]

    mock_checkbox.return_value.ask.return_value = []

    result = runner.invoke(app, ["gitignore"])

    assert result.exit_code == 1
    assert "cancelled or no technologies selected" in result.stdout
    mock_env_instance.generate_gitignore.assert_not_called()


@patch("chegi.cli.commands.gitignore.EnvManager")
def test_gitignore_no_templates_found(mock_env_manager: MagicMock):
    """Tests exit with error if no gitignore templates are found in the database."""
    mock_env_instance = mock_env_manager.return_value
    mock_env_instance.get_envs_with_gitignore.return_value = []

    result = runner.invoke(app, ["gitignore"])

    assert result.exit_code == 1
    assert "No gitignore templates found" in result.stdout


@patch("chegi.cli.commands.gitignore.GitClient")
@patch("chegi.cli.commands.gitignore.EnvManager")
@patch("chegi.cli.commands.gitignore.questionary.checkbox")
def test_gitignore_not_a_git_repo(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock, mock_git_client: MagicMock
):
    """Tests that the commit prompt is skipped if the target is not a git repository."""
    mock_env_instance = mock_env_manager.return_value
    mock_env_instance.get_envs_with_gitignore.return_value = ["python"]
    mock_env_instance.has_existing_gitignore.return_value = False

    mock_git_instance = mock_git_client.return_value
    mock_git_instance.is_valid_repo.return_value = False

    mock_checkbox.return_value.ask.return_value = ["Python"]

    result = runner.invoke(app, ["gitignore"])

    assert result.exit_code == 0
    assert "Skipped commit: Not a git repository" in result.stdout
    mock_git_instance.commit_file.assert_not_called()
