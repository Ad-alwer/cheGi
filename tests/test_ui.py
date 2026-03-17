import pytest
from unittest.mock import patch
from rich.table import Table
from pathlib import Path

from chegi.ui import TerminalUI
from chegi.git_utils import GitStatus

@pytest.fixture
def ui() -> TerminalUI:
    """
    Provides a fresh TerminalUI instance for each test.

    Returns:
        TerminalUI: The initialized UI object.
    """
    return TerminalUI()

@patch("chegi.ui.Console.print")
def test_print_error(mock_print, ui: TerminalUI):
    """
    Tests if the error messages are printed with the correct red formatting.
    """
    ui.print_error("Test error message")
    mock_print.assert_called_once_with("[bold red]Error:[/bold red] Test error message")

@patch("chegi.ui.Console.print")
def test_print_warning(mock_print, ui: TerminalUI):
    """
    Tests if the warning messages are printed with the correct yellow formatting.
    """
    ui.print_warning("Test warning message")
    mock_print.assert_called_once_with("[bold yellow]Warning:[/bold yellow] Test warning message")

@patch("chegi.ui.Console.print")
def test_display_results_table_empty(mock_print, ui: TerminalUI):
    """
    Tests the table display logic when an empty list of statuses is provided.
    It should print a specific yellow warning message instead of an empty table.
    """
    ui.display_results_table([])
    mock_print.assert_called_once_with("[bold yellow]No Git repositories found in the specified path.[/bold yellow]")

@patch("chegi.ui.Console.print")
def test_display_results_table_with_data(mock_print, ui: TerminalUI):
    """
    Tests the table rendering logic when valid GitStatus objects are provided.
    Ensures that a rich.table.Table object is passed to the console.print method.
    """
    statuses = [
        # Clean and synced repo
        GitStatus(Path("/dummy/repo1"), "repo1", "main", is_dirty=False, has_remote=True),
        # Dirty and no remote repo
        GitStatus(Path("/dummy/repo2"), "repo2", "dev", is_dirty=True, has_remote=False),
        # Repo with error
        GitStatus(Path("/dummy/repo3"), "repo3", "Unknown", is_dirty=False, has_remote=False, error="Permission denied"),
    ]
    
    ui.display_results_table(statuses)
    
    # Extract the arguments passed to mock_print
    args, _ = mock_print.call_args
    
    # Assert that exactly one argument was passed and it's a Rich Table object
    assert len(args) == 1
    table_obj = args[0]
    assert isinstance(table_obj, Table)
    assert table_obj.title == "📦 Git Repositories Status"
