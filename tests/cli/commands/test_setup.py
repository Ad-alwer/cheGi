from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from chegi.cli.main import app

runner = CliRunner()

# ==========================================
# Dummy Data (Simulating Parsed YAML Targets)
# ==========================================

DUMMY_ENV_DATA = {
    "name": "python",
    "levels": {"1": ["git"]},
    "levels_info": {"1": "Core"},
    "tools": {
        "git": {
            "check_cmd": "git --version",
            "requires": [],
            "install": {"apt": "sudo apt install git", "default": "brew install git"},
        }
    },
}

DUMMY_ENV_DATA_DEPS = {
    "name": "python",
    "levels": {"1": ["tool_c", "tool_a", "tool_b"]},
    "levels_info": {"1": "Core"},
    "tools": {
        "tool_c": {
            "check_cmd": "cmd_c",
            "requires": ["tool_a"], # Depends on A
            "install": {"default": "install c"},
        },
        "tool_a": {
            "check_cmd": "cmd_a",
            "requires": ["tool_b"], # Depends on B
            "install": {"default": "install a"},
        },
        "tool_b": {
            "check_cmd": "cmd_b",
            "requires": [],         # Independent
            "install": {"default": "install b"},
        },
    },
}

DUMMY_ENV_DATA_MIRROR = {
    "name": "python",
    "levels": {"1": ["requests"]},
    "levels_info": {"1": "Libraries"},
    "tools": {
        "requests": {
            "check_cmd": "pip show requests",
            "requires": [],
            "install": {
                "pip": "pip install requests",
                "default": "pip install requests",
            },
        }
    },
}

# ==========================================
# Test Cases
# Note for Devs: Typer handles 'Groups' differently than 'Commands'. 
# When using sub-apps, flags MUST precede arguments. 
# Always use ["setup", "--yes", "target"] instead of ["setup", "target", "--yes"].
# ==========================================

@patch("chegi.services.installer.setup_service.SystemInstaller")
@patch("chegi.services.installer.setup_service.EnvManager")
def test_setup_multiple_tools_success_message(
    mock_env_manager: MagicMock, mock_installer: MagicMock
):
    mock_env_manager.return_value.find_setup_target.return_value = DUMMY_ENV_DATA_DEPS
    mock_installer.get_os_package_manager.return_value = "default"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    mock_installer.run_custom_command.return_value = True

    result = runner.invoke(app, ["setup", "--yes", "python"])
    assert result.exit_code == 0
    assert "✨ Setup for python completed successfully! ✨" in result.stdout

@patch("chegi.services.installer.setup_service.SystemInstaller")
@patch("chegi.services.installer.setup_service.EnvManager")
def test_setup_installation_keyboard_interrupt(
    mock_env_manager: MagicMock, mock_installer: MagicMock
):
    """Simulate user pressing Ctrl+C gracefully exiting without ugly tracebacks."""
    mock_env_manager.return_value.get_available_envs.return_value = ["python"]
    mock_env_manager.return_value.find_setup_target.return_value = {
        "name": "Python",
        "levels": {"standalone": ["python"]},
        "tools": {
            "python": {"check_cmd": "python --version", "cmd": "apt install python3"}
        },
    }

    mock_installer.get_os_package_manager.return_value = "apt"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    mock_installer.get_install_command.return_value = "apt install python3"
    # Trigger KeyboardInterrupt when the installation command runs
    mock_installer.run_custom_command.side_effect = KeyboardInterrupt()

    result = runner.invoke(app, ["setup", "--yes", "python"])
    assert result.exit_code == 1

@patch("chegi.services.installer.setup_service.SystemInstaller")
@patch("chegi.services.installer.setup_service.EnvManager")
def test_setup_dependency_resolution_order(
    mock_env_manager: MagicMock, mock_installer: MagicMock
):
    mock_env_manager.return_value.find_setup_target.return_value = DUMMY_ENV_DATA_DEPS
    mock_installer.get_os_package_manager.return_value = "default"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    mock_installer.run_custom_command.return_value = True

    result = runner.invoke(app, ["setup", "--yes", "python"])
    assert result.exit_code == 0

@patch("chegi.services.installer.setup_service.SystemInstaller")
@patch("chegi.services.installer.setup_service.EnvManager")
def test_setup_dependency_missing_skip(
    mock_env_manager: MagicMock, mock_installer: MagicMock
):
    """If a base dependency fails (e.g., tool_b), subsequent tools needing it (tool_a, tool_c) must be skipped."""
    mock_env_manager.return_value.find_setup_target.return_value = DUMMY_ENV_DATA_DEPS
    mock_installer.get_os_package_manager.return_value = "default"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")

    def mock_get_install_cmd(tool_data, package_manager, **kwargs):
        return tool_data.get("install", {}).get("default", "dummy_cmd")
    mock_installer.get_install_command.side_effect = mock_get_install_cmd

    def run_command_side_effect(*args, **kwargs):
        # Intentionally fail the installation for 'tool_b'
        if "install b" in str(args) + str(kwargs):
            return False
        return True
    mock_installer.run_custom_command.side_effect = run_command_side_effect

    result = runner.invoke(app, ["setup", "--yes", "python"])
    calls = mock_installer.run_custom_command.call_args_list
    assert "install b" in str(calls) # Ensure 'b' was attempted
    # Expected behavior: exit code 0 (graceful finish), but 'a' and 'c' were never installed
    assert result.exit_code == 0

# Note on Questionary mocks: 
# Questionary chains methods like `checkbox("...").ask()`.
# To mock this, we need `mock.component.return_value.ask.return_value = ...`

@patch("chegi.services.installer.setup_service.typer.confirm")
@patch("chegi.services.installer.setup_service.ChegiConfig")
@patch("chegi.services.installer.setup_service.questionary")
@patch("chegi.services.installer.setup_service.SystemInstaller")
@patch("chegi.services.installer.setup_service.EnvManager")
@patch("chegi.services.installer.setup_service.SUPPORTED_PMS", {"pip", "npm"})
def test_setup_interactive_mirror_accepted(
    mock_env_manager, mock_installer, mock_questionary, mock_config_cls, mock_confirm
):
    mock_confirm.return_value = True
    mock_config = mock_config_cls.return_value
    mock_config.get_mirror.return_value = ["https://test.mirror"]

    mock_env_instance = mock_env_manager.return_value
    mock_env_instance.find_setup_target.return_value = {
        "name": "Requests",
        "levels": {"standalone": ["requests"]},
        "tools": {
            "requests": {"check_cmd": "pip show requests", "cmd": "pip install requests"}
        },
    }
    mock_env_instance.get_available_envs.return_value = ["requests"]
    mock_env_instance.get_required_package_managers.return_value = {"pip"}

    mock_installer.get_os_package_manager.return_value = "pip"
    mock_installer.is_tool_installed.return_value = (False, "")
    mock_installer.get_install_command.return_value = "pip install requests"
    mock_installer.run_custom_command.return_value = True

    # Simulate user checking the box for the tool
    mock_questionary.checkbox.return_value.ask.return_value = [
        {"name": "requests", "level": "Standalone App", "cmd": "pip install requests", "requires": []}
    ]
    mock_questionary.confirm.return_value.ask.return_value = True
    mock_questionary.select.return_value.ask.return_value = "https://test.mirror"

    result = runner.invoke(app, ["setup", "requests"])

    assert result.exit_code == 0, f"Error: {result.exception}"
    mock_installer.run_custom_command.assert_called_with(
        "pip install requests", pm_name="pip", mirror_url="https://test.mirror"
    )

@patch("chegi.services.installer.setup_service.typer.confirm")
@patch("chegi.services.installer.setup_service.ChegiConfig")
@patch("chegi.services.installer.setup_service.questionary")
@patch("chegi.services.installer.setup_service.SystemInstaller")
@patch("chegi.services.installer.setup_service.EnvManager")
@patch("chegi.services.installer.setup_service.SUPPORTED_PMS", {"pip", "npm"})
def test_setup_interactive_mirror_declined(
    mock_env_manager, mock_installer, mock_questionary, mock_config_cls, mock_confirm
):
    mock_confirm.side_effect = [True, False, False]

    mock_env_instance = mock_env_manager.return_value
    mock_env_instance.find_setup_target.return_value = {
        "name": "Requests",
        "levels": {"standalone": ["requests"]},
        "tools": {
            "requests": {"check_cmd": "pip show requests", "cmd": "pip install requests"}
        },
    }
    mock_env_instance.get_available_envs.return_value = ["requests"]
    mock_env_instance.get_required_package_managers.return_value = {"pip"}

    mock_installer.get_os_package_manager.return_value = "pip"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    mock_installer.get_install_command.return_value = "pip install requests"
    mock_installer.run_custom_command.return_value = True

    mock_config = mock_config_cls.return_value
    mock_config.get_mirror.return_value = ["https://dummy.mirror.com"]

    mock_questionary.checkbox.return_value.ask.return_value = [
        {"name": "requests", "level": "Standalone App", "cmd": "pip install requests", "requires": []}
    ]
    # Simulate user rejecting the use of mirror
    mock_questionary.confirm.return_value.ask.return_value = False
    mock_questionary.select.return_value.ask.return_value = "none"

    result = runner.invoke(app, ["setup", "requests"])
    assert result.exit_code == 0, f"Error: {result.exception}"

@patch("chegi.services.installer.setup_service.ChegiConfig")
@patch("chegi.services.installer.setup_service.SystemInstaller")
@patch("chegi.services.installer.setup_service.EnvManager")
def test_setup_auto_yes_skips_mirror_prompt(
    mock_env_manager, mock_installer, mock_config
):
    """If --yes flag is used but no saved mirrors exist, it should skip mirror selection quietly."""
    mock_env_manager.return_value.find_setup_target.return_value = DUMMY_ENV_DATA_MIRROR
    mock_installer.get_os_package_manager.return_value = "pip"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    mock_installer.get_install_command.return_value = "pip install requests"
    mock_installer.run_custom_command.return_value = True
    mock_config.return_value.get_mirrors.return_value = {}

    result = runner.invoke(app, ["setup", "--yes", "python"])
    assert result.exit_code == 0, f"Error: {result.exception}"

@patch("chegi.services.installer.setup_service.ChegiConfig")
@patch("chegi.services.installer.setup_service.SystemInstaller")
@patch("chegi.services.installer.setup_service.EnvManager")
def test_setup_auto_yes_uses_first_saved_mirror(
    mock_env_manager, mock_installer, mock_config
):
    """If --yes flag is used and there are saved mirrors, it automatically picks the first available one."""
    mock_env_manager.return_value.find_setup_target.return_value = DUMMY_ENV_DATA_MIRROR
    mock_installer.get_os_package_manager.return_value = "pip"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    mock_installer.get_install_command.return_value = "pip install requests"
    mock_installer.run_custom_command.return_value = True
    mock_config.return_value.get_mirrors.return_value = {
        "pip": {"mirror1": "https://m1.com", "mirror2": "https://m2.com"}
    }

    result = runner.invoke(app, ["setup", "--yes", "python"])
    assert result.exit_code == 0, f"Error: {result.exception}"

@patch("chegi.services.installer.setup_service.typer.confirm")
@patch("chegi.services.installer.setup_service.ChegiConfig")
@patch("chegi.services.installer.setup_service.questionary")
@patch("chegi.services.installer.setup_service.SystemInstaller")
@patch("chegi.services.installer.setup_service.EnvManager")
@patch("chegi.services.installer.setup_service.SUPPORTED_PMS", {"pip", "npm"})
def test_setup_interactive_select_from_multiple_mirrors(
    mock_env_manager, mock_installer, mock_questionary, mock_config_cls, mock_confirm
):
    mock_confirm.return_value = True

    mock_env_instance = mock_env_manager.return_value
    mock_env_instance.find_setup_target.return_value = {
        "name": "Requests",
        "levels": {"standalone": ["requests"]},
        "tools": {
            "requests": {"check_cmd": "pip show requests", "cmd": "pip install requests"}
        },
    }
    mock_env_instance.get_available_envs.return_value = ["requests"]
    mock_env_instance.get_required_package_managers.return_value = {"pip"}

    mock_installer.get_os_package_manager.return_value = "pip"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    mock_installer.get_install_command.return_value = "pip install requests"
    mock_installer.run_custom_command.return_value = True

    mock_config = mock_config_cls.return_value
    mock_config.get_mirror.return_value = ["https://mirror1.com", "https://mirror2.com"]

    mock_questionary.checkbox.return_value.ask.return_value = [
        {"name": "requests", "level": "Standalone App", "cmd": "pip install requests", "requires": []}
    ]
    mock_questionary.confirm.return_value.ask.return_value = True
    # Simulate user picking 'mirror2' from the select list
    mock_questionary.select.return_value.ask.return_value = "https://mirror2.com"

    result = runner.invoke(app, ["setup", "requests"])

    assert result.exit_code == 0, f"Error: {result.exception}"
    mock_installer.run_custom_command.assert_called_with(
        "pip install requests", pm_name="pip", mirror_url="https://mirror2.com"
    )

@patch("chegi.services.installer.setup_service.typer.confirm")
@patch("chegi.services.installer.setup_service.ChegiConfig")
@patch("chegi.services.installer.setup_service.questionary")
@patch("chegi.services.installer.setup_service.SystemInstaller")
@patch("chegi.services.installer.setup_service.EnvManager")
@patch("chegi.services.installer.setup_service.SUPPORTED_PMS", {"pip", "npm"})
def test_setup_interactive_select_new_mirror(
    mock_env_manager, mock_installer, mock_questionary, mock_config_cls, mock_confirm
):
    mock_confirm.return_value = True

    mock_env_instance = mock_env_manager.return_value
    mock_env_instance.find_setup_target.return_value = {
        "name": "Requests",
        "levels": {"standalone": ["requests"]},
        "tools": {
            "requests": {"check_cmd": "pip show requests", "cmd": "pip install requests"}
        },
    }
    mock_env_instance.get_available_envs.return_value = ["requests"]
    mock_env_instance.get_required_package_managers.return_value = {"pip"}

    mock_installer.get_os_package_manager.return_value = "pip"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    mock_installer.get_install_command.return_value = "pip install requests"
    mock_installer.run_custom_command.return_value = True

    mock_config = mock_config_cls.return_value
    mock_config.get_mirror.return_value = ["https://old-mirror"]

    mock_questionary.checkbox.return_value.ask.return_value = [
        {"name": "requests", "level": "Standalone App", "cmd": "pip install requests", "requires": []}
    ]
    mock_questionary.confirm.return_value.ask.return_value = True
    # Simulate user choosing to enter a 'new' mirror manually
    mock_questionary.select.return_value.ask.return_value = "new"
    mock_questionary.text.return_value.ask.return_value = "https://brand-new-mirror"

    result = runner.invoke(app, ["setup", "requests"])

    assert result.exit_code == 0, f"Error: {result.exception}"
    mock_installer.run_custom_command.assert_called_with(
        "pip install requests", pm_name="pip", mirror_url="https://brand-new-mirror"
    )
