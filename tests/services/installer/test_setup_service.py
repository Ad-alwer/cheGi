import pytest
import typer
from unittest.mock import patch

from chegi.services.environment.models import EnvironmentPreset
from chegi.services.installer.setup_service import SetupService
from chegi.services.installer.exceptions import UserAbortedSetupError

# Fixtures

@pytest.fixture
@patch("chegi.services.installer.setup_service.ChegiConfig")
@patch("chegi.services.installer.setup_service.EnvManager")
@patch("chegi.services.installer.setup_service.SystemInstaller")
def setup_service(mock_installer_class, mock_env_manager_class, mock_config_class):
    """Fixture to provide a SetupService instance with mocked external dependencies."""
    mock_installer_class.get_os_package_manager.return_value = "apt"
    
    service = SetupService(environment="python", auto_yes=True)
    
    # Attach the mocked instance for easier access in test functions
    service.mock_env_manager = mock_env_manager_class.return_value
    return service


# Tests

def test_resolve_target_success(setup_service):
    """Test successful resolution of a target environment."""
    setup_service.mock_env_manager.find_setup_target.return_value = EnvironmentPreset(
        name="PythonEnv",
        description="Test environment",
        tools={},
        gitignore=[],
    )
    
    setup_service._resolve_target()
    
    assert setup_service.display_name == "PythonEnv"
    assert setup_service.env_data is not None


@patch("chegi.services.installer.setup_service.TerminalUI")
def test_resolve_target_unsupported_exits(mock_ui, setup_service):
    """Test that resolving an unsupported target raises Typer Exit."""
    setup_service.mock_env_manager.find_setup_target.return_value = None
    setup_service.mock_env_manager.get_available_envs.return_value = ["go", "rust"]
    
    with pytest.raises(typer.Exit) as exc_info:
        setup_service._resolve_target()
        
    assert exc_info.value.exit_code == 1
    mock_ui.print_error.assert_called_once()


def test_normalize_data_standalone_app(setup_service):
    """Test data normalization for a standalone app (no 'levels' defined)."""
    setup_service.env_data = EnvironmentPreset(
        name="python",
        description="Test standalone tool",
        tools={},
        gitignore=[],
    )
    setup_service.environment = "python"
    
    levels, levels_info, tools_data = setup_service._normalize_data()
    
    assert "standalone" in levels
    assert levels["standalone"] == ["python"]


def test_normalize_data_full_environment(setup_service):
    """Test data normalization for a full environment with levels and tools."""
    setup_service.env_data = EnvironmentPreset(
        name="python",
        description="Full Python environment",
        tools={},
        gitignore=[],
        levels={"1": ["python", "pip"], "2": ["black"]},
        levels_info={"1": "Essential", "2": "Recommended"},
        raw_tools={
            "python": {"check_cmd": "python --version", "install": {"apt": "apt install python"}},
            "pip": {"check_cmd": "pip --version", "install": {"default": "pip install --upgrade pip"}},
            "black": {"check_cmd": "black --version", "install": {"default": "pip install black"}},
        },
    )
    setup_service.environment = "python"
    
    levels, levels_info, tools_data = setup_service._normalize_data()
    
    assert levels == {"1": ["python", "pip"], "2": ["black"]}
    assert levels_info == {"1": "Essential", "2": "Recommended"}
    assert set(tools_data.keys()) == {"python", "pip", "black"}
    assert tools_data["python"]["check_cmd"] == "python --version"
    assert tools_data["black"]["install"]["default"] == "pip install black"


def test_sort_dependencies(setup_service):
    """Test the dependency sorting logic."""
    unsorted_tools = [
        {"name": "AppC", "requires": ["AppA"]},
        {"name": "AppA", "requires": ["BaseTool"]},
        {"name": "BaseTool", "requires": []},
    ]
    
    sorted_tools = setup_service._sort_dependencies(unsorted_tools)
    
    assert sorted_tools[0]["name"] == "BaseTool"
    assert sorted_tools[1]["name"] == "AppA"
    assert sorted_tools[2]["name"] == "AppC"


@patch("chegi.services.installer.setup_service.TerminalUI")
@patch("chegi.services.installer.setup_service.SystemInstaller.run_custom_command")
def test_execute_installations_skips_missing_deps(mock_run_cmd, mock_ui, setup_service):
    """Test that tools with missing dependencies are skipped."""
    tools_to_install = [
        {"name": "ToolB", "cmd": "install b", "requires": ["ToolA"], "level": "App"}
    ]
    setup_service.installed_tools = set()
    
    setup_service._execute_installations(tools_to_install, session_mirrors={})
    
    mock_run_cmd.assert_not_called()
    mock_ui.print_warning.assert_called_once()


@patch("chegi.services.installer.setup_service.SystemInstaller.run_custom_command")
def test_execute_installations_success(mock_run_cmd, setup_service):
    """Test successful execution of installation commands."""
    mock_run_cmd.return_value = True
    tools_to_install = [
        {"name": "ToolA", "cmd": "apt install a", "requires": [], "level": "App"}
    ]
    setup_service.installed_tools = set()
    
    setup_service._execute_installations(tools_to_install, session_mirrors={})
    
    mock_run_cmd.assert_called_once_with("apt install a", pm_name=None, mirror_url=None)
    assert "ToolA" in setup_service.installed_tools


@patch("chegi.services.installer.setup_service.console")
@patch("chegi.services.installer.setup_service.SystemInstaller.run_custom_command")
def test_execute_installations_handles_user_abort(mock_run_cmd, mock_console, setup_service):
    """Test that execution handles UserAbortedSetupError correctly and exits gracefully."""
    mock_run_cmd.side_effect = UserAbortedSetupError("Installation aborted by user.")
    tools_to_install = [
        {"name": "ToolA", "cmd": "apt install a", "requires": [], "level": "App"}
    ]
    setup_service.installed_tools = set()
    
    with pytest.raises(typer.Exit) as exc_info:
        setup_service._execute_installations(tools_to_install, session_mirrors={})
    
    assert exc_info.value.exit_code == 1
    mock_console.print.assert_any_call("\n[bold red]❌ Installation interrupted by user (Ctrl+C).[/bold red]")
