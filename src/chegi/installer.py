import platform
import subprocess
import shutil
import typer

class SystemInstaller:
    """System and package installer for Chegi dependencies.

    This class provides scalable methods to install system-level dependencies
    across different operating systems.

    Attributes:
        SUPPORTED_PACKAGES (list): A list of package names currently supported 
            for automated installation.
    """

    SUPPORTED_PACKAGES = ["git"]

    @classmethod
    def install_package(cls, package_name: str) -> bool:
        """Installs a specified package based on the host operating system.

        Args:
            package_name (str): The name of the package to install.

        Returns:
            bool: True if the installation was successful, False otherwise.
        """
        if package_name.lower() not in cls.SUPPORTED_PACKAGES:
            typer.secho(f"Package '{package_name}' is not supported by Chegi installer.", fg=typer.colors.RED)
            return False

        os_name = platform.system()
        
        if os_name == "Windows":
            return cls._install_package_windows(package_name)
        elif os_name == "Linux":
            return cls._install_package_linux(package_name)
        elif os_name == "Darwin":
            return cls._install_package_mac(package_name)
        else:
            typer.secho(f"OS '{os_name}' is not supported for automatic installation.", fg=typer.colors.RED)
            return False

    @classmethod
    def _install_package_windows(cls, package_name: str) -> bool:
        """Installs a package on Windows using winget.

        Maps general package names to their specific winget IDs before installation.

        Args:
            package_name (str): The general name of the package.

        Returns:
            bool: True if the installation was successful, False otherwise.
        """
        winget_map = {
            "git": "Git.Git"
        }
        winget_id = winget_map.get(package_name.lower(), package_name)

        if shutil.which("winget"):
            typer.secho(f"Using 'winget' to install {package_name} on Windows...", fg=typer.colors.CYAN)
            result = subprocess.run(["winget", "install", "--id", winget_id, "-e", "--source", "winget"])
            return result.returncode == 0
            
        typer.secho("Error: 'winget' not found. Please install manually.", fg=typer.colors.RED)
        return False

    @classmethod
    def _install_package_linux(cls, package_name: str) -> bool:
        """Installs a package on Linux using the available package manager.

        Supports apt, dnf, and pacman package managers.

        Args:
            package_name (str): The name of the package.

        Returns:
            bool: True if the installation was successful, False otherwise.
        """
        if shutil.which("apt"):
            typer.secho(f"Using 'apt' to install {package_name}...", fg=typer.colors.CYAN)
            cmd = f"sudo apt update && sudo apt install -y {package_name}"
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0
            
        elif shutil.which("dnf"):
            typer.secho(f"Using 'dnf' to install {package_name}...", fg=typer.colors.CYAN)
            cmd = f"sudo dnf install -y {package_name}"
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0
            
        elif shutil.which("pacman"):
            typer.secho(f"Using 'pacman' to install {package_name}...", fg=typer.colors.CYAN)
            cmd = f"sudo pacman -Sy --noconfirm {package_name}"
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0
            
        typer.secho(f"Error: Unsupported Linux distribution for installing {package_name}.", fg=typer.colors.RED)
        return False

    @classmethod
    def _install_package_mac(cls, package_name: str) -> bool:
        """Installs a package on macOS using Homebrew or OS-specific fallbacks.

        Attempts to use Homebrew first. If Homebrew is missing and the requested
        package is Git, it falls back to using xcode-select.

        Args:
            package_name (str): The name of the package.

        Returns:
            bool: True if the installation was successful, False otherwise.
        """
        if shutil.which("brew"):
            typer.secho(f"Using 'Homebrew' to install {package_name}...", fg=typer.colors.CYAN)
            result = subprocess.run(["brew", "install", package_name])
            return result.returncode == 0
            
        if package_name.lower() == "git":
            typer.secho("Homebrew not found. Attempting to install via xcode-select...", fg=typer.colors.CYAN)
            result = subprocess.run(["xcode-select", "--install"])
            return result.returncode == 0
            
        typer.secho(f"Error: 'brew' not found. Cannot install {package_name}.", fg=typer.colors.RED)
        return False
