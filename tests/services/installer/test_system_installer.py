from unittest.mock import patch

import pytest

from chegi.services.installer.exceptions import (
    TargetNotSupportedError,
    UserAbortedSetupError,
)
from chegi.services.installer.system_installer import SystemInstaller

# To keep the patch decorators clean and short
MODULE_PATH = "chegi.services.installer.system_installer"


# Installation Routing Tests

def test_install_unsupported_package():
    """Test that installing a package not in SUPPORTED_PACKAGES raises an error."""
    with pytest.raises(TargetNotSupportedError, match="not supported"):
        SystemInstaller.install_package("node")


@patch(f"{MODULE_PATH}.platform.system")
def test_install_unsupported_os(mock_system):
    """Test that running the installer on an unknown OS raises an error."""
    mock_system.return_value = "FreeBSD"
    
    with pytest.raises(TargetNotSupportedError, match="is not supported"):
        SystemInstaller.install_package("git")


@patch(f"{MODULE_PATH}.platform.system")
@patch.object(SystemInstaller, "_install_package_linux")
def test_install_routing_linux(mock_linux_installer, mock_system):
    """Test that install_package routes correctly to the Linux sub-installer."""
    mock_system.return_value = "Linux"
    mock_linux_installer.return_value = True

    result = SystemInstaller.install_package("git")

    assert result is True
    mock_linux_installer.assert_called_once_with("git")


# OS Specific Installers Tests

@patch(f"{MODULE_PATH}.shutil.which")
@patch(f"{MODULE_PATH}.subprocess.run")
def test_windows_winget_success(mock_run, mock_which):
    """Test successful package installation on Windows using winget."""
    mock_which.return_value = "C:\\path\\to\\winget.exe"
    mock_run.return_value.returncode = 0

    result = SystemInstaller._install_package_windows("git")

    assert result is True
    assert "Git.Git" in mock_run.call_args[0][0]


@patch(f"{MODULE_PATH}.shutil.which")
@patch(f"{MODULE_PATH}.subprocess.run")
def test_windows_winget_aborted(mock_run, mock_which):
    """Test that a user abort (Ctrl+C) raises UserAbortedSetupError on Windows."""
    mock_which.return_value = "winget"
    mock_run.side_effect = KeyboardInterrupt()

    with pytest.raises(UserAbortedSetupError):
        SystemInstaller._install_package_windows("git")


@patch(f"{MODULE_PATH}.shutil.which")
@patch(f"{MODULE_PATH}.subprocess.run")
def test_linux_apt_success(mock_run, mock_which):
    """Test successful package installation on Linux using APT."""
    mock_which.side_effect = lambda cmd: "/usr/bin/apt" if cmd == "apt" else None
    mock_run.return_value.returncode = 0

    result = SystemInstaller._install_package_linux("git")

    assert result is True
    assert len(mock_run.call_args_list) == 2
    apt_update_call = mock_run.call_args_list[0]
    assert apt_update_call.args[0] == ["sudo", "apt", "update"]
    apt_install_call = mock_run.call_args_list[-1]
    assert apt_install_call.args[0] == ["sudo", "apt", "install", "-y", "git"]


@patch(f"{MODULE_PATH}.shutil.which")
@patch(f"{MODULE_PATH}.subprocess.run")
def test_linux_dnf_success(mock_run, mock_which):
    """Test successful package installation on Linux using DNF."""
    mock_which.side_effect = lambda cmd: "/usr/bin/dnf" if cmd == "dnf" else None
    mock_run.return_value.returncode = 0

    result = SystemInstaller._install_package_linux("git")

    assert result is True
    dnf_install_call = mock_run.call_args_list[-1]
    assert dnf_install_call.args[0] == ["sudo", "dnf", "install", "-y", "git"]


@patch(f"{MODULE_PATH}.shutil.which")
@patch(f"{MODULE_PATH}.subprocess.run")
def test_linux_aborted(mock_run, mock_which):
    """Test that a user abort raises UserAbortedSetupError on Linux."""
    mock_which.return_value = "apt"
    mock_run.side_effect = KeyboardInterrupt()

    with pytest.raises(UserAbortedSetupError):
        SystemInstaller._install_package_linux("git")


@patch(f"{MODULE_PATH}.shutil.which")
@patch(f"{MODULE_PATH}.subprocess.run")
def test_mac_brew_success(mock_run, mock_which):
    """Test successful package installation on macOS using Homebrew."""
    mock_which.return_value = "/usr/local/bin/brew"
    mock_run.return_value.returncode = 0

    result = SystemInstaller._install_package_mac("git")

    assert result is True
    mock_run.assert_called_once_with(["brew", "install", "git"])


@patch(f"{MODULE_PATH}.shutil.which")
@patch(f"{MODULE_PATH}.subprocess.run")
def test_mac_xcode_fallback_success(mock_run, mock_which):
    """Test macOS fallback to xcode-select when Homebrew is missing for Git."""
    mock_which.return_value = None 
    mock_run.return_value.returncode = 0

    result = SystemInstaller._install_package_mac("git")

    assert result is True
    mock_run.assert_called_once_with(["xcode-select", "--install"])


@patch(f"{MODULE_PATH}.shutil.which")
@patch(f"{MODULE_PATH}.subprocess.run")
def test_mac_aborted(mock_run, mock_which):
    """Test that a user abort raises UserAbortedSetupError on macOS."""
    mock_which.return_value = "brew"
    mock_run.side_effect = KeyboardInterrupt()

    with pytest.raises(UserAbortedSetupError):
        SystemInstaller._install_package_mac("git")


# Detection and Check Tests

@patch(f"{MODULE_PATH}.platform.system")
@patch(f"{MODULE_PATH}.shutil.which")
def test_get_os_package_manager(mock_which, mock_system):
    """Test detection of the host OS package manager."""
    mock_system.return_value = "Windows"
    mock_which.return_value = "winget"
    assert SystemInstaller.get_os_package_manager() == "winget"

    mock_system.return_value = "Darwin"
    mock_which.return_value = "brew"
    assert SystemInstaller.get_os_package_manager() == "brew"

    mock_system.return_value = "Linux"
    mock_which.side_effect = lambda cmd: "/usr/bin/apt" if cmd == "apt" else None
    assert SystemInstaller.get_os_package_manager() == "apt"


@patch(f"{MODULE_PATH}.subprocess.run")
def test_is_tool_installed_cli_success(mock_run):
    """Test CLI tool check extracts only the first line of output."""
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "Python 3.10.12\nExtra logs"

    is_installed, output = SystemInstaller.is_tool_installed("python --version")

    assert is_installed is True
    assert output == "Python 3.10.12"


@patch(f"{MODULE_PATH}.shutil.which")
@patch(f"{MODULE_PATH}.subprocess.run")
def test_is_tool_installed_gui_success(mock_run, mock_which):
    """Test GUI tool check bypasses subprocess to prevent opening the app."""
    mock_which.return_value = "/usr/bin/postman"

    is_installed, output = SystemInstaller.is_tool_installed("postman --version", is_gui=True)

    assert is_installed is True
    assert output == "Installed (GUI Tool)"
    mock_run.assert_not_called()


@patch(f"{MODULE_PATH}.subprocess.run")
def test_is_tool_installed_quoted_command(mock_run):
    """Test CLI tool check with a command containing quoted arguments."""
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "ok\n"

    is_installed, output = SystemInstaller.is_tool_installed(
        'python -c "import sys; print(sys.version)"'
    )

    assert is_installed is True
    cmd_arg = mock_run.call_args[0][0]
    assert cmd_arg == ["python", "-c", "import sys; print(sys.version)"]


@patch(f"{MODULE_PATH}.subprocess.run")
def test_is_tool_installed_empty_command_fails(mock_run):
    """Test CLI tool check with an empty command string."""
    mock_run.side_effect = FileNotFoundError("command not found")

    is_installed, output = SystemInstaller.is_tool_installed("")

    assert is_installed is False
    assert "not found" in output


# Custom Command Execution Tests

@patch(f"{MODULE_PATH}.subprocess.run")
def test_run_custom_command_success(mock_run):
    """Test successful execution of a custom shell command."""
    mock_run.return_value.returncode = 0

    result = SystemInstaller.run_custom_command("pip install pytest")

    assert result is True
    mock_run.assert_called_once_with(["pip", "install", "pytest"])


@patch(f"{MODULE_PATH}.subprocess.run")
def test_run_custom_command_quoted_args(mock_run):
    """Test custom command execution with quoted arguments."""
    mock_run.return_value.returncode = 0

    result = SystemInstaller.run_custom_command(
        'pip install "package>=1.0"'
    )

    assert result is True
    mock_run.assert_called_once_with(["pip", "install", "package>=1.0"])


@patch(f"{MODULE_PATH}.subprocess.run")
def test_run_custom_command_empty_fails(mock_run):
    """Test custom command with empty string."""
    mock_run.side_effect = FileNotFoundError()

    result = SystemInstaller.run_custom_command("")

    assert result is False


@patch(f"{MODULE_PATH}.subprocess.run")
def test_run_custom_command_user_abort(mock_run):
    """Test that a process returning SIGINT (130) raises UserAbortedSetupError."""
    mock_run.return_value.returncode = 130

    with pytest.raises(UserAbortedSetupError, match="aborted by user"):
        SystemInstaller.run_custom_command("sleep 100")


def test_build_command_with_mirror_pip():
    """Test injecting the index-url flag correctly into a pip command."""
    base_cmd = "pip install requests"
    expected = "pip install --index-url https://mirror requests"
    
    result = SystemInstaller._build_command_with_mirror(base_cmd, "pip", "https://mirror")
    assert result == expected


def test_build_command_with_mirror_npm():
    """Test appending the registry flag correctly to an npm command."""
    base_cmd = "npm install express"
    expected = "npm install express --registry https://mirror"
    
    result = SystemInstaller._build_command_with_mirror(base_cmd, "npm", "https://mirror")
    assert result == expected


def test_get_install_command_resolution():
    """Test command resolution using different JSON structure keys."""
    tool_info_simple = {"install": {"apt": "apt install x"}}
    assert SystemInstaller.get_install_command(tool_info_simple, "apt") == "apt install x"

    tool_info_fallback = {"install_cmd": "pip install y"}
    assert SystemInstaller.get_install_command(tool_info_fallback, "pip") == "pip install y"
    
    tool_info_missing = {"name": "tool"}
    assert SystemInstaller.get_install_command(tool_info_missing, "apt") is None
