import platform
import shlex
import shutil
import subprocess
from typing import List, Optional, Tuple, Union

import typer

from .exceptions import TargetNotSupportedError, UserAbortedSetupError


class SystemInstaller:
    """System and package installer for dependencies.

    This class provides scalable methods to install system-level dependencies
    across different operating systems, and acts as the execution engine for
    dynamic tools loaded from environment JSON databases.

    Attributes:
        SUPPORTED_PACKAGES (List[str]): A list of package names currently
            supported for hardcoded automated installation.
    """

    SUPPORTED_PACKAGES: List[str] = ["git"]

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
    def get_install_command(cls, tool_info: dict, pkg_manager: str) -> Optional[str]:
        """Gets the appropriate installation command based on the OS and package manager."""

        # 1. Check if it uses the simple 'install' key mapping
        if "install" in tool_info:
            return tool_info["install"].get(pkg_manager) or tool_info["install"].get(
                "default"
            )

        # 2. Check if it uses the detailed 'platforms' key mapping
        elif "platforms" in tool_info:
            os_name = platform.system().lower()
            if os_name == "darwin":
                os_name = "mac"

            platform_cmds = tool_info["platforms"].get(os_name, {})

            if isinstance(platform_cmds, dict):
                return platform_cmds.get(pkg_manager) or platform_cmds.get("default")
            elif isinstance(platform_cmds, str):
                return platform_cmds

        # 3. Fallback for newer potential keys
        install_data = tool_info.get("install_cmd") or tool_info.get("install_command")
        if isinstance(install_data, str):
            return install_data
        elif isinstance(install_data, dict):
            return install_data.get(pkg_manager) or install_data.get("default")

        return None

    @classmethod
    def is_tool_installed(
        cls, check_cmd: str, is_gui: bool = False
    ) -> Tuple[bool, str]:
        """Runs a check command to determine if a dynamic tool is installed.

        Args:
            check_cmd (str): The shell command to execute to check for the tool
                (e.g., 'python --version').
            is_gui (bool): If True, avoids executing the command (which would open
                the GUI application) and only checks if the executable is in PATH.

        Returns:
            Tuple[bool, str]: A tuple where the first element is a boolean indicating
            success (True if installed), and the second element is the command's
            output or an error message.
        """
        # --- Handle GUI Tools ---
        # If the tool is a graphical app, running its command will open the app and freeze the terminal.
        # Instead, we just check if its executable exists in the system PATH.
        if is_gui:
            executable_name = check_cmd.split()[
                0
            ]  # e.g., gets "postman" from "postman --version"
            if shutil.which(executable_name):
                return True, "Installed (GUI Tool)"
            return False, "Not installed"

        # --- Handle CLI Tools ---
        try:
            result = subprocess.run(
                shlex.split(check_cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0:
                output = result.stdout.strip().split("\n")[0]
                return True, output if output else "Installed"
            return False, "Not installed"
        except Exception as e:
            return False, str(e)

    @classmethod
    def _build_command_with_mirror(
        cls,
        base_cmd: str,
        pm_name: Optional[str],
        mirror_url: Optional[Union[str, List[str]]],
    ) -> str:
        """Constructs the final command string with a mirror/registry flag if applicable.

        This helper intelligently injects the correct flag for supported package
        managers. For 'pip', it inserts the flag after 'install'. For 'npm',
        it appends the flag to the end.

        Args:
            base_cmd (str): The original command (e.g., "pip install some-package").
            pm_name (Optional[str]): The lowercased name of the package manager (e.g., "pip").
            mirror_url (Optional[Union[str, List[str]]]): The mirror URL (or list of URLs) to use.

        Returns:
            str: The modified command string or the original if no mirror is needed.
        """
        if not pm_name or not mirror_url:
            return base_cmd

        # Extract the primary URL if a list of mirrors is provided
        primary_mirror = (
            mirror_url[0] if isinstance(mirror_url, list) and mirror_url else mirror_url
        )
        if not isinstance(primary_mirror, str):
            return base_cmd

        parts = base_cmd.split()

        if pm_name == "pip":
            # For pip, the --index-url flag must come right after the 'install' action.
            # Example: "pip install package" -> "pip install --index-url <url> package"
            try:
                install_index = parts.index("install")
                parts.insert(install_index + 1, primary_mirror)
                parts.insert(install_index + 1, "--index-url")
                return " ".join(parts)
            except ValueError:
                # If 'install' is not in the command, we cannot safely inject the flag.
                return base_cmd

        elif pm_name == "npm":
            # For npm, the --registry flag can be safely appended to the command.
            # Example: "npm install package" -> "npm install package --registry <url>"
            return f"{base_cmd} --registry {primary_mirror}"

        # If the package manager is not supported for mirrors, return the original command.
        return base_cmd

    @classmethod
    def run_custom_command(
        cls,
        cmd: str,
        pm_name: Optional[str] = None,
        mirror_url: Optional[Union[str, List[str]]] = None,
    ) -> bool:
        """Executes a dynamic installation shell command, with optional mirror support.

        Args:
            cmd (str): The exact shell command to run (e.g., 'pip install django').
            pm_name (Optional[str]): The package manager being used (e.g., 'pip').
            mirror_url (Optional[Union[str, List[str]]]): The mirror URL(s), if provided by the user.

        Returns:
            bool: True if the command executed with a zero return code, False otherwise.

        Raises:
            UserAbortedSetupError: If the user interrupts execution (e.g., Ctrl+C),
                allowing higher CLI layers to handle the graceful exit.
        """
        final_cmd = cls._build_command_with_mirror(cmd, pm_name, mirror_url)

        typer.secho(f"Executing: {final_cmd}", fg=typer.colors.CYAN)
        try:
            result = subprocess.run(shlex.split(final_cmd))
            if result.returncode == 130 or result.returncode < 0:
                raise KeyboardInterrupt
            return result.returncode == 0

        except KeyboardInterrupt:
            # Re-raise to let the caller handle SIGINT cleanly without standard traceback.
            raise UserAbortedSetupError("Installation aborted by user.")
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
            typer.secho(
                f"Package '{package_name}' is not supported.", fg=typer.colors.RED
            )
            raise TargetNotSupportedError(f"Package '{package_name}' is not supported.")

        os_name = platform.system()

        if os_name == "Windows":
            return cls._install_package_windows(package_name)
        elif os_name == "Linux":
            return cls._install_package_linux(package_name)
        elif os_name == "Darwin":
            return cls._install_package_mac(package_name)
        else:
            typer.secho(f"OS '{os_name}' is not supported.", fg=typer.colors.RED)
            raise TargetNotSupportedError(f"OS '{os_name}' is not supported.")

    @classmethod
    def _install_package_windows(cls, package_name: str) -> bool:
        """Installs a package on Windows OS using the winget package manager.

        Args:
            package_name (str): The name of the package to install.

        Returns:
            bool: True if winget installs the package successfully, False otherwise.

        Raises:
            UserAbortedSetupError: If the installation is interrupted by the user.
        """
        winget_map = {"git": "Git.Git"}
        winget_id = winget_map.get(package_name.lower(), package_name)

        if shutil.which("winget"):
            typer.secho(
                f"Using 'winget' to install {package_name}...", fg=typer.colors.CYAN
            )
            try:
                result = subprocess.run(
                    ["winget", "install", "--id", winget_id, "-e", "--source", "winget"]
                )
                return result.returncode == 0
            except KeyboardInterrupt:
                raise UserAbortedSetupError("Installation aborted by user.")

        typer.secho(
            "Error: 'winget' not found. Please install manually.", fg=typer.colors.RED
        )
        return False

    @classmethod
    def _install_package_linux(cls, package_name: str) -> bool:
        """Installs a package on Linux using the available package manager.

        Args:
            package_name (str): The name of the package to install.

        Returns:
            bool: True on successful installation, False otherwise.

        Raises:
            UserAbortedSetupError: If the installation is interrupted by the user.
        """
        try:
            if shutil.which("apt"):
                typer.secho(
                    f"Using 'apt' to install {package_name}...", fg=typer.colors.CYAN
                )
                result = subprocess.run(["sudo", "apt", "update"])
                if result.returncode != 0:
                    return False
                result = subprocess.run(
                    ["sudo", "apt", "install", "-y", package_name]
                )
                return result.returncode == 0

            elif shutil.which("dnf"):
                typer.secho(
                    f"Using 'dnf' to install {package_name}...", fg=typer.colors.CYAN
                )
                result = subprocess.run(
                    ["sudo", "dnf", "install", "-y", package_name]
                )
                return result.returncode == 0

            elif shutil.which("pacman"):
                typer.secho(
                    f"Using 'pacman' to install {package_name}...", fg=typer.colors.CYAN
                )
                result = subprocess.run(
                    ["sudo", "pacman", "-Sy", "--noconfirm", package_name]
                )
                return result.returncode == 0

            typer.secho("Error: Unsupported Linux distribution.", fg=typer.colors.RED)
            return False
        except KeyboardInterrupt:
            raise UserAbortedSetupError("Installation aborted by user.")

    @classmethod
    def _install_package_mac(cls, package_name: str) -> bool:
        """Installs a package on macOS using Homebrew or OS-specific fallbacks.

        Args:
            package_name (str): The name of the package to install.

        Returns:
            bool: True on successful installation, False otherwise.

        Raises:
            UserAbortedSetupError: If the installation is interrupted by the user.
        """
        try:
            if shutil.which("brew"):
                typer.secho(
                    f"Using 'Homebrew' to install {package_name}...",
                    fg=typer.colors.CYAN,
                )
                result = subprocess.run(["brew", "install", package_name])
                return result.returncode == 0

            if package_name.lower() == "git":
                typer.secho(
                    "Homebrew not found. Attempting via xcode-select...",
                    fg=typer.colors.CYAN,
                )
                result = subprocess.run(["xcode-select", "--install"])
                return result.returncode == 0

            typer.secho(
                f"Error: 'brew' not found. Cannot install {package_name}.",
                fg=typer.colors.RED,
            )
            return False
        except KeyboardInterrupt:
            raise UserAbortedSetupError("Installation aborted by user.")
