import platform
import subprocess
import shutil
import typer
from typing import Tuple


class SystemInstaller:
    """System and package installer for dependencies.

    This class provides scalable methods to install system-level dependencies
    across different operating systems, and acts as the execution engine forrun_custom_command
    dynamic tools loaded from environment JSON databases.

    Attributes:
        SUPPORTED_PACKAGES (list[str]): A list of package names currently 
            supported for hardcoded automated installation.
    """

    SUPPORTED_PACKAGES = ["git"]

    @classmethod
    def get_os_package_manager(cls) -> str:
        """Detects the active system package manager based on the host OS.

        Returns:
            str: The name of the detected package manager ('apt', 'brew', 
            'winget', 'dnf', 'pacman') or 'default' if no match is found.
        """
        os_name = platform.system()

        if os_name == "Windows" and shutil.which("winget"):
            return "winget"
        elif os_name == "Darwin" and shutil.which("brew"):
            return "brew"
        elif os_name == "Linux":
            if shutil.which("apt"):
                return "apt"
            elif shutil.which("dnf"):
                return "dnf"
            elif shutil.which("pacman"):
                return "pacman"
                
        return "default"

    @classmethod
    def is_tool_installed(cls, check_cmd: str) -> Tuple[bool, str]:
        """Runs a check command to determine if a dynamic tool is installed.

        Args:
            check_cmd (str): The shell command to execute to check for the tool 
                (e.g., 'python --version').

        Returns:
            Tuple[bool, str]: A tuple where the first element is a boolean indicating 
            success (True if installed), and the second element is the command's 
            output or an error message.
        """
        try:
            result = subprocess.run(
                check_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                # Extract only the first line of stdout to prevent multi-line 
                # outputs from breaking the CLI layout.
                output = result.stdout.strip().split('\n')[0]
                return True, output if output else "Installed"
            return False, "Not installed"
        except Exception as e:
            return False, str(e)

    @classmethod
    def run_custom_command(cls, cmd: str) -> bool:
        """Executes a dynamic installation shell command.

        Args:
            cmd (str): The exact shell command to run (e.g., 'pip install django').

        Returns:
            bool: True if the command executed with a zero return code, False otherwise.

        Raises:
            KeyboardInterrupt: If the user interrupts the execution (e.g., Ctrl+C), 
                allowing the higher CLI layers to handle the graceful exit.
        """
        typer.secho(f"Executing: {cmd}", fg=typer.colors.CYAN)
        try:
            result = subprocess.run(cmd, shell=True)
            if result.returncode == 130 or result.returncode < 0:
                raise KeyboardInterrupt
            return result.returncode == 0
            
        except KeyboardInterrupt:
            # Re-raise to let the caller handle SIGINT cleanly without standard traceback.
            raise
        except Exception as e:
            typer.secho(f"Error executing command: {e}", fg=typer.colors.RED)
            return False

    @classmethod
    def install_package(cls, package_name: str) -> bool:
        """Installs a hardcoded specified package based on the host OS.

        Args:
            package_name (str): The name of the package to install.

        Returns:
            bool: True if the installation was successful, False otherwise.
        """
        if package_name.lower() not in cls.SUPPORTED_PACKAGES:
            typer.secho(f"Package '{package_name}' is not supported.", fg=typer.colors.RED)
            return False

        os_name = platform.system()
        
        if os_name == "Windows":
            return cls._install_package_windows(package_name)
        elif os_name == "Linux":
            return cls._install_package_linux(package_name)
        elif os_name == "Darwin":
            return cls._install_package_mac(package_name)
        else:
            typer.secho(f"OS '{os_name}' is not supported.", fg=typer.colors.RED)
            return False

    @classmethod
    def _install_package_windows(cls, package_name: str) -> bool:
        """Installs a package on Windows OS using the winget package manager.

        Args:
            package_name (str): The name of the package to install.

        Returns:
            bool: True if winget installs the package successfully, False otherwise.

        Raises:
            KeyboardInterrupt: If the installation is interrupted by the user.
        """
        winget_map = {
            "git": "Git.Git"
        }
        winget_id = winget_map.get(package_name.lower(), package_name)

        if shutil.which("winget"):
            typer.secho(f"Using 'winget' to install {package_name}...", fg=typer.colors.CYAN)
            try:
                result = subprocess.run(["winget", "install", "--id", winget_id, "-e", "--source", "winget"])
                return result.returncode == 0
            except KeyboardInterrupt:
                raise
            
        typer.secho("Error: 'winget' not found. Please install manually.", fg=typer.colors.RED)
        return False

    @classmethod
    def _install_package_linux(cls, package_name: str) -> bool:
        """Installs a package on Linux using the available package manager.

        Checks for apt, dnf, or pacman in that order, and uses the first one found.

        Args:
            package_name (str): The name of the package to install.

        Returns:
            bool: True on successful installation, False if the package manager 
            fails or no supported package manager is found.

        Raises:
            KeyboardInterrupt: If the installation is interrupted by the user.
        """
        try:
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
                
            typer.secho("Error: Unsupported Linux distribution.", fg=typer.colors.RED)
            return False
        except KeyboardInterrupt:
            raise

    @classmethod
    def _install_package_mac(cls, package_name: str) -> bool:
        """Installs a package on macOS using Homebrew or OS-specific fallbacks.

        Args:
            package_name (str): The name of the package to install.

        Returns:
            bool: True on successful installation, False otherwise.

        Raises:
            KeyboardInterrupt: If the installation is interrupted by the user.
        """
        try:
            if shutil.which("brew"):
                typer.secho(f"Using 'Homebrew' to install {package_name}...", fg=typer.colors.CYAN)
                result = subprocess.run(["brew", "install", package_name])
                return result.returncode == 0
                
            if package_name.lower() == "git":
                typer.secho("Homebrew not found. Attempting via xcode-select...", fg=typer.colors.CYAN)
                result = subprocess.run(["xcode-select", "--install"])
                return result.returncode == 0
                
            typer.secho(f"Error: 'brew' not found. Cannot install {package_name}.", fg=typer.colors.RED)
            return False
        except KeyboardInterrupt:
            raise
