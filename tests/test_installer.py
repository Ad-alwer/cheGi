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
