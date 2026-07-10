"""
Tests for the reword CLI command.
This module contains unit tests to ensure the correct behavior of the 'reword' command,
including interactive prompts, pagination, and error handling.
"""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app
from chegi.services.git.exceptions import GitCoreError

runner = CliRunner()


@patch("chegi.cli.commands.reword.RewordService")
@patch("chegi.cli.commands.reword.GitClient")
def test_reword_head_direct_message(mock_git_client_class, mock_reword_service_class):
    """
    Test rewording the HEAD commit directly without the interactive menu.
    """
    mock_git_instance = mock_git_client_class.return_value
    mock_reword_instance = mock_reword_service_class.return_value

    mock_reword_instance.is_head.return_value = True
    mock_reword_instance.get_commit_message.return_value = "Old message"

    result = runner.invoke(app, ["reword", "New commit message"])

    assert result.exit_code == 0
    mock_reword_instance.amend_head.assert_called_once_with("New commit message")


@patch("chegi.cli.commands.reword.GitClient")
def test_reword_not_a_git_repo(mock_git_client_class):
    """
    Test the behavior when the command is run outside a git repository.
    """
    mock_git_instance = mock_git_client_class.return_value
    mock_git_instance.check_git_installation.side_effect = GitCoreError(
        "Not a git repository"
    )

    result = runner.invoke(app, ["reword", "Some message"])

    assert result.exit_code == 1
    assert "Not a git repository" in result.stdout


@patch("chegi.cli.commands.reword.questionary")
@patch("chegi.cli.commands.reword.RewordService")
@patch("chegi.cli.commands.reword.GitClient")
def test_reword_last_interactive_head(mock_git, mock_reword, mock_questionary):
    """
    Test rewording the HEAD commit using the interactive menu (--last).
    """
    mock_reword_inst = mock_reword.return_value
    mock_reword_inst.calculate_pagination.return_value = (0, 5)
    mock_reword_inst.get_commits.return_value = [
        "abc1234 Old HEAD message",
        "def5678 Older commit",
    ]
    mock_reword_inst.is_head.return_value = True
    mock_reword_inst.get_commit_message.return_value = "Old HEAD message"

    # Mock questionary.select().ask()
    mock_select = MagicMock()
    mock_select.ask.return_value = "abc1234 Old HEAD message"
    mock_questionary.select.return_value = mock_select

    # Mock questionary.text().ask()
    mock_text = MagicMock()
    mock_text.ask.return_value = "New interactive HEAD message"
    mock_questionary.text.return_value = mock_text

    result = runner.invoke(app, ["reword", "--last", "5"])

    assert result.exit_code == 0
    mock_reword_inst.amend_head.assert_called_once_with("New interactive HEAD message")


@patch("chegi.cli.commands.reword.questionary")
@patch("chegi.cli.commands.reword.RewordService")
@patch("chegi.cli.commands.reword.GitClient")
def test_reword_last_interactive_older_commit(mock_git, mock_reword, mock_questionary):
    """
    Test rewording an older commit using the interactive menu (triggers automated rebase).
    """
    mock_reword_inst = mock_reword.return_value
    mock_reword_inst.calculate_pagination.return_value = (0, 5)
    mock_reword_inst.get_commits.return_value = [
        "abc1234 HEAD message",
        "def5678 Older commit",
    ]
    mock_reword_inst.is_head.return_value = False
    mock_reword_inst.get_commit_message.return_value = "Older commit"

    mock_select = MagicMock()
    mock_select.ask.return_value = "def5678 Older commit"
    mock_questionary.select.return_value = mock_select

    mock_text = MagicMock()
    mock_text.ask.return_value = "New older commit message"
    mock_questionary.text.return_value = mock_text

    result = runner.invoke(app, ["reword", "--last", "5"])

    assert result.exit_code == 0
    mock_reword_inst.perform_automated_rebase.assert_called_once_with(
        "def5678", "New older commit message"
    )


@patch("chegi.cli.commands.reword.questionary")
@patch("chegi.cli.commands.reword.RewordService")
@patch("chegi.cli.commands.reword.GitClient")
def test_reword_unchanged_message(mock_git, mock_reword, mock_questionary):
    """
    Test the scenario where the user provides the exact same commit message.
    """
    mock_reword_inst = mock_reword.return_value
    mock_reword_inst.calculate_pagination.return_value = (0, 5)
    mock_reword_inst.get_commits.return_value = ["abc1234 Same message"]
    mock_reword_inst.is_head.return_value = True
    mock_reword_inst.get_commit_message.return_value = "Same message"

    mock_select = MagicMock()
    mock_select.ask.return_value = "abc1234 Same message"
    mock_questionary.select.return_value = mock_select

    mock_text = MagicMock()
    mock_text.ask.return_value = "Same message"
    mock_questionary.text.return_value = mock_text

    result = runner.invoke(app, ["reword", "--last", "5"])

    assert result.exit_code == 0
    assert "Message is unchanged" in result.stdout


@patch("chegi.cli.commands.reword.RewordService")
@patch("chegi.cli.commands.reword.GitClient")
def test_reword_pagination_invalid_range(mock_git, mock_reword):
    """
    Test handling of invalid pagination arguments (e.g., start > end).
    """
    mock_reword_inst = mock_reword.return_value
    mock_reword_inst.calculate_pagination.side_effect = ValueError("Invalid range")

    result = runner.invoke(app, ["reword", "--start", "10", "--end", "5"])

    assert result.exit_code == 1
    assert "Invalid range" in result.stdout


@patch("chegi.cli.commands.reword.questionary")
@patch("chegi.cli.commands.reword.RewordService")
@patch("chegi.cli.commands.reword.GitClient")
def test_reword_pagination_start_and_end(mock_git, mock_reword, mock_questionary):
    """
    Test fetching commits with specific start and end indices.
    """
    mock_reword_inst = mock_reword.return_value
    mock_reword_inst.calculate_pagination.return_value = (5, 5)
    mock_reword_inst.get_commits.return_value = ["abc1234 Test"]

    # Simulate user aborting the prompt
    mock_select = MagicMock()
    mock_select.ask.return_value = None
    mock_questionary.select.return_value = mock_select

    result = runner.invoke(app, ["reword", "--start", "5", "--end", "10"])

    mock_reword_inst.calculate_pagination.assert_called_once_with(None, 5, 10)
    mock_reword_inst.get_commits.assert_called_once_with(5, 5)
    assert result.exit_code == 0


@patch("chegi.cli.commands.reword.questionary")
@patch("chegi.cli.commands.reword.RewordService")
@patch("chegi.cli.commands.reword.GitClient")
def test_reword_pagination_only_end(mock_git, mock_reword, mock_questionary):
    """
    Test fetching commits using only the end index.
    """
    mock_reword_inst = mock_reword.return_value
    mock_reword_inst.calculate_pagination.return_value = (0, 10)
    mock_reword_inst.get_commits.return_value = ["abc1234 Test"]

    # Simulate user aborting the prompt
    mock_select = MagicMock()
    mock_select.ask.return_value = None
    mock_questionary.select.return_value = mock_select

    result = runner.invoke(app, ["reword", "--end", "10"])

    mock_reword_inst.calculate_pagination.assert_called_once_with(None, None, 10)
    mock_reword_inst.get_commits.assert_called_once_with(0, 10)
    assert result.exit_code == 0
