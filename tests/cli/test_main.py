import pytest
from typer.testing import CliRunner
from unittest.mock import patch

from chegi.cli.main import app, global_setup

runner = CliRunner()

def test_app_help_message():
    """Test that the main app displays the correct help description."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "cheGi - The ultimate Git companion" in result.stdout
    assert "Type less, do more" in result.stdout

def test_subcommands_are_registered():
    """Test that all expected subcommands are registered in the main app."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    
    expected_commands = [
        "setup", 
        "config", 
        "sync", 
        "scan", 
        "reword", 
        "guard", 
        "gitignore"
    ]
    
    for cmd in expected_commands:
        # Check if the command name appears in the help output
        assert cmd in result.stdout

@patch("chegi.cli.main.run_preflight_checks")
def test_no_args_is_help(mock_run_preflight):
    """Test that running the app without arguments shows the help menu."""
    result_no_args = runner.invoke(app, [])
    
    # Check if the help text is present in stdout
    assert "cheGi - The ultimate Git companion" in result_no_args.stdout
    
    mock_run_preflight.assert_not_called()

@patch("chegi.cli.main.run_preflight_checks")
def test_global_setup_callback(mock_run_preflight):
    """Test that the global callback executes the preflight checks."""
    # Call the callback directly to unit test its behavior
    global_setup()
    
    # Verify the preflight orchestrator was called exactly once
    mock_run_preflight.assert_called_once()
