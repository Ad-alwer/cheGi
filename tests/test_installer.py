import pytest
from unittest.mock import patch, MagicMock
from chegi.installer import SystemInstaller


def test_install_unsupported_package():
    """Tests if the installer correctly rejects unsupported packages.

    Args:
        None

    Returns:
        None
    """
    # 'node' is not in SUPPORTED_PACKAGES
    result = SystemInstaller.install_package("node")
    assert result is False


@patch("chegi.installer.platform.system")
def test_install_unsupported_os(mock_system: MagicMock):
    """Tests if the installer gracefully handles an unknown operating system.

    Args:
        mock_system (MagicMock): Mocked platform.system function.

    Returns:
        None
    """
    mock_system.return_value = "FreeBSD"
    result = SystemInstaller.install_package("git")
    
    assert result is False
    mock_system.assert_called_once()


@patch("chegi.installer.platform.system")
@patch.object(SystemInstaller, "_install_package_linux")
def test_install_routing_linux(mock_linux_installer: MagicMock, mock_system: MagicMock):
    """Tests if the main install_package method routes to Linux installer properly.

    Args:
        mock_linux_installer (MagicMock): Mocked _install_package_linux method.
        mock_system (MagicMock): Mocked platform.system function.

    Returns:
        None
    """
    mock_system.return_value = "Linux"
    mock_linux_installer.return_value = True
    
    result = SystemInstaller.install_package("git")
    
    assert result is True
    mock_linux_installer.assert_called_once_with("git")


@patch("chegi.installer.shutil.which")
@patch("chegi.installer.subprocess.run")
def test_windows_winget_success(mock_run: MagicMock, mock_which: MagicMock):
    """Tests successful package installation on Windows using winget.

    Args:
        mock_run (MagicMock): Mocked subprocess.run function.
        mock_which (MagicMock): Mocked shutil.which function.

    Returns:
        None
    """
    mock_which.return_value = "C:\\path\\to\\winget.exe"
    # Mock the return code of the subprocess
    mock_run.return_value.returncode = 0
    
    result = SystemInstaller._install_package_windows("git")
    
    assert result is True
    mock_run.assert_called_once()
    # Check if the winget specific ID was used
    args = mock_run.call_args[0][0]
    assert "Git.Git" in args


@patch("chegi.installer.shutil.which")
def test_windows_winget_missing(mock_which: MagicMock):
    """Tests Windows installation when winget is not available on the system.

    Args:
        mock_which (MagicMock): Mocked shutil.which function.

    Returns:
        None
    """
    mock_which.return_value = None
    
    result = SystemInstaller._install_package_windows("git")
    assert result is False


@patch("chegi.installer.shutil.which")
@patch("chegi.installer.subprocess.run")
def test_linux_apt_success(mock_run: MagicMock, mock_which: MagicMock):
    """Tests successful package installation on Linux using APT.

    Args:
        mock_run (MagicMock): Mocked subprocess.run function.
        mock_which (MagicMock): Mocked shutil.which function.

    Returns:
        None
    """
    # Simulate that 'apt' exists, but others do not
    mock_which.side_effect = lambda cmd: "/usr/bin/apt" if cmd == "apt" else None
    mock_run.return_value.returncode = 0
    
    result = SystemInstaller._install_package_linux("git")
    
    assert result is True
    mock_run.assert_called_once()
    assert "apt install" in mock_run.call_args[0][0]


@patch("chegi.installer.shutil.which")
@patch("chegi.installer.subprocess.run")
def test_linux_dnf_success(mock_run: MagicMock, mock_which: MagicMock):
    """Tests successful package installation on Linux using DNF.

    Args:
        mock_run (MagicMock): Mocked subprocess.run function.
        mock_which (MagicMock): Mocked shutil.which function.

    Returns:
        None
    """
    # Simulate that only 'dnf' exists
    mock_which.side_effect = lambda cmd: "/usr/bin/dnf" if cmd == "dnf" else None
    mock_run.return_value.returncode = 0
    
    result = SystemInstaller._install_package_linux("git")
    
    assert result is True
    assert "dnf install" in mock_run.call_args[0][0]


@patch("chegi.installer.shutil.which")
def test_linux_unsupported_distro(mock_which: MagicMock):
    """Tests Linux installation on an unsupported distribution (no apt, dnf, pacman).

    Args:
        mock_which (MagicMock): Mocked shutil.which function.

    Returns:
        None
    """
    # Simulate no supported package managers exist
    mock_which.return_value = None
    
    result = SystemInstaller._install_package_linux("git")
    assert result is False


@patch("chegi.installer.shutil.which")
@patch("chegi.installer.subprocess.run")
def test_mac_brew_success(mock_run: MagicMock, mock_which: MagicMock):
    """Tests successful package installation on macOS using Homebrew.

    Args:
        mock_run (MagicMock): Mocked subprocess.run function.
        mock_which (MagicMock): Mocked shutil.which function.

    Returns:
        None
    """
    mock_which.return_value = "/usr/local/bin/brew"
    mock_run.return_value.returncode = 0
    
    result = SystemInstaller._install_package_mac("git")
    
    assert result is True
    mock_run.assert_called_once_with(["brew", "install", "git"])


@patch("chegi.installer.shutil.which")
@patch("chegi.installer.subprocess.run")
def test_mac_xcode_fallback_success(mock_run: MagicMock, mock_which: MagicMock):
    """Tests macOS fallback to xcode-select when Homebrew is missing and package is Git.

    Args:
        mock_run (MagicMock): Mocked subprocess.run function.
        mock_which (MagicMock): Mocked shutil.which function.

    Returns:
        None
    """
    mock_which.return_value = None  # Brew not found
    mock_run.return_value.returncode = 0
    
    result = SystemInstaller._install_package_mac("git")
    
    assert result is True
    mock_run.assert_called_once_with(["xcode-select", "--install"])


@patch("chegi.installer.platform.system")
@patch("chegi.installer.shutil.which")
def test_get_os_package_manager(mock_which: MagicMock, mock_system: MagicMock) -> None:
    """Test detection of the host OS package manager."""
    # Simulate Windows environment with winget available
    mock_system.return_value = "Windows"
    mock_which.return_value = "C:\\path\\to\\winget.exe"
    assert SystemInstaller.get_os_package_manager() == "winget"

    # Simulate macOS environment with Homebrew available
    mock_system.return_value = "Darwin"
    mock_which.return_value = "/opt/homebrew/bin/brew"
    assert SystemInstaller.get_os_package_manager() == "brew"

    # Simulate Linux environment. We use side_effect to mimic shutil.which 
    # finding 'apt' but returning None for other package managers like 'dnf'.
    mock_system.return_value = "Linux"
    mock_which.side_effect = lambda cmd: "/usr/bin/apt" if cmd == "apt" else None
    assert SystemInstaller.get_os_package_manager() == "apt"

    # Simulate Linux environment with no supported package manager (fallback scenario)
    mock_system.return_value = "Linux"
    mock_which.side_effect = lambda cmd: None
    assert SystemInstaller.get_os_package_manager() == "default"


@patch("chegi.installer.subprocess.run")
def test_is_tool_installed_success(mock_run: MagicMock) -> None:
    """Test tool installation check when the tool is successfully found."""
    # Simulate successful command execution (return code 0)
    # Include multi-line output to test the stdout parsing logic
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "Python 3.10.12\nAdditional unwanted output"
    
    is_installed, output = SystemInstaller.is_tool_installed("python3 --version")
    
    assert is_installed is True
    # Ensure only the first line is extracted to maintain a clean UI table
    assert output == "Python 3.10.12"


@patch("chegi.installer.subprocess.run")
def test_is_tool_installed_failure(mock_run: MagicMock) -> None:
    """Test tool installation check when the tool is missing."""
    # Simulate a "command not found" scenario (return code != 0)
    mock_run.return_value.returncode = 127
    
    is_installed, output = SystemInstaller.is_tool_installed("unknown_tool --version")
    
    assert is_installed is False
    assert output == "Not installed"


@patch("chegi.installer.subprocess.run")
def test_is_tool_installed_exception(mock_run: MagicMock) -> None:
    """Test tool installation check when a system exception occurs."""
    # Simulate an unexpected OS-level exception during execution
    mock_run.side_effect = Exception("Permission denied")
    
    is_installed, output = SystemInstaller.is_tool_installed("restricted_cmd")
    
    assert is_installed is False
    assert "Permission denied" in output


@patch("chegi.installer.subprocess.run")
def test_run_custom_command_success(mock_run: MagicMock) -> None:
    """Test successful execution of a custom shell command."""
    mock_run.return_value.returncode = 0
    
    result = SystemInstaller.run_custom_command("pip install pytest")
    
    assert result is True
    mock_run.assert_called_once_with("pip install pytest", shell=True)


@patch("chegi.installer.subprocess.run")
def test_run_custom_command_failure(mock_run: MagicMock) -> None:
    """Test execution of a custom shell command that fails."""
    # Simulate a failed installation (e.g., package not found or network error)
    mock_run.return_value.returncode = 1
    
    result = SystemInstaller.run_custom_command("pip install invalid_pkg")
    
    assert result is False


@patch("chegi.installer.subprocess.run")
def test_run_custom_command_keyboard_interrupt(mock_run: MagicMock) -> None:
    """Test if run_custom_command correctly raises KeyboardInterrupt on Ctrl+C."""
    # Return code 130 is the standard POSIX exit code for a process 
    # terminated by SIGINT (Ctrl+C).
    mock_run.return_value.returncode = 130
    
    with pytest.raises(KeyboardInterrupt):
        SystemInstaller.run_custom_command("sleep 100")


def test_build_command_with_mirror_missing_args() -> None:
    """Tests command builder behavior when PM name or mirror URL is omitted."""
    base_cmd = "pip install requests"
    
    assert SystemInstaller._build_command_with_mirror(base_cmd, None, "http://mirror") == base_cmd
    assert SystemInstaller._build_command_with_mirror(base_cmd, "pip", None) == base_cmd


def test_build_command_with_mirror_pip_success() -> None:
    """Tests injecting the index-url flag correctly into a pip install command."""
    base_cmd = "pip install requests --upgrade"
    mirror_url = "https://mirror.local/pypi"
    expected = "pip install --index-url https://mirror.local/pypi requests --upgrade"
    
    result = SystemInstaller._build_command_with_mirror(base_cmd, "pip", mirror_url)
    assert result == expected


def test_build_command_with_mirror_pip_no_install() -> None:
    """Tests that pip commands without the 'install' keyword remain unmodified."""
    base_cmd = "pip download requests"
    mirror_url = "https://mirror.local/pypi"
    
    result = SystemInstaller._build_command_with_mirror(base_cmd, "pip", mirror_url)
    assert result == base_cmd


def test_build_command_with_mirror_npm_success() -> None:
    """Tests appending the registry flag correctly to an npm command."""
    base_cmd = "npm install express"
    mirror_url = "https://mirror.local/npm"
    expected = "npm install express --registry https://mirror.local/npm"
    
    result = SystemInstaller._build_command_with_mirror(base_cmd, "npm", mirror_url)
    assert result == expected


def test_build_command_with_mirror_unsupported_pm() -> None:
    """Tests that commands for unsupported package managers remain unmodified."""
    base_cmd = "apt install curl"
    mirror_url = "https://mirror.local/apt"
    
    result = SystemInstaller._build_command_with_mirror(base_cmd, "apt", mirror_url)
    assert result == base_cmd


@patch("chegi.installer.subprocess.run")
def test_run_custom_command_with_mirror_integration(mock_run: MagicMock) -> None:
    """Tests if run_custom_command properly passes mirror arguments to the builder and executes the modified command."""
    mock_run.return_value.returncode = 0
    
    result = SystemInstaller.run_custom_command(
        cmd="pip install django",
        pm_name="pip",
        mirror_url="http://custom.mirror"
    )
    
    assert result is True
    # Verify that the executed command is the modified version
    mock_run.assert_called_once_with(
        "pip install --index-url http://custom.mirror django", 
        shell=True
    )
    
def test_build_command_with_mirror_list_success() -> None:
    """Tests that the command builder extracts the primary mirror when given a list."""
    base_cmd = "pip install requests"
    mirror_urls = ["https://mirror1.local", "https://mirror2.local"]
    expected = "pip install --index-url https://mirror1.local requests"
    
    result = SystemInstaller._build_command_with_mirror(base_cmd, "pip", mirror_urls)
    assert result == expected


def test_build_command_with_mirror_empty_list() -> None:
    """Tests command builder behavior when an empty list is provided."""
    base_cmd = "npm install express"
    mirror_urls: list = []
    
    # Should safely fallback to the base command if the list is empty
    result = SystemInstaller._build_command_with_mirror(base_cmd, "npm", mirror_urls)
    assert result == base_cmd


@patch("chegi.installer.subprocess.run")
def test_run_custom_command_with_mirror_list_integration(mock_run: MagicMock) -> None:
    """Tests if run_custom_command handles a list of mirror URLs correctly."""
    mock_run.return_value.returncode = 0
    
    result = SystemInstaller.run_custom_command(
        cmd="pip install django",
        pm_name="pip",
        mirror_url=["http://primary.mirror", "http://secondary.mirror"]
    )
    
    assert result is True
    mock_run.assert_called_once_with(
        "pip install --index-url http://primary.mirror django", 
        shell=True
    )
