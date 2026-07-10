from unittest.mock import patch

import pytest

from chegi.ui.console import TerminalUI, console


@pytest.mark.parametrize("method, expected_prefix, expected_color", [
    ("print_success", "✔", "bold green"),
    ("print_error", "✖", "bold red"),
    ("print_warning", "⚠", "bold yellow"),
    ("print_info", "ℹ", "bold blue"),
])
def test_terminal_ui_standard_messages(method, expected_prefix, expected_color):
    """Test standard messaging methods for correct formatting and styling tags."""
    with patch.object(console, "print") as mock_print:
        test_message = "Sample message"
        
        ui_method = getattr(TerminalUI, method)
        ui_method(test_message)
        
        mock_print.assert_called_once()
        called_args, _ = mock_print.call_args
        output_string = called_args[0]
        
        assert expected_color in output_string
        assert expected_prefix in output_string
        assert test_message in output_string

def test_terminal_ui_print_message_neutral():
    """Test the base print_message method with default neutral styling."""
    with patch.object(console, "print") as mock_print:
        TerminalUI.print_message("Neutral text")
        
        mock_print.assert_called_once_with("[white]Neutral text[/]")
