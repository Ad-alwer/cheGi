import shutil
import subprocess

import typer

from chegi.cli.core.checks import PreflightCheck
from chegi.installer import SystemInstaller
from chegi.ui import TerminalUI


class GitRequirementCheck(PreflightCheck):
    """Checks for Git installation globally and handles automatic setup.

    Attributes:
        ui (TerminalUI): The UI instance for terminal interactions.
    """

    def __init__(self) -> None:
        """Initializes the GitRequirementCheck with UI components."""
        self.ui = TerminalUI()

    def _check_git_globally(self) -> tuple[bool, str]:
        """Validates if Git is installed and functioning on the system OS.

        Returns:
            tuple[bool, str]: A boolean indicating success, and a message.
        """
        if not shutil.which("git"):
            return False, "Git is not installed or not found in system PATH."

        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            return True, f"Git is ready ({result.stdout.strip()})."
        except Exception as e:
            return False, f"Failed to execute Git command: {str(e)}"

    def execute(self) -> None:
        """Executes the Git environment check.

        Raises:
            typer.Exit: If Git is missing and the user aborts installation, 
                or if the installation fails.
        """
        is_valid, message = self._check_git_globally()

        if is_valid:
            return

        self.ui.print_error(f"Environment Check Failed: {message}")

        install_now = typer.confirm(
            "Git is missing or outdated. Do you want cheGi to automatically install it for you?"
        )

        if not install_now:
            self.ui.print_error(
                "Installation aborted. cheGi requires Git to function properly."
            )
            raise typer.Exit(code=1)

        self._handle_installation()

    def _handle_installation(self) -> None:
        """Handles the automatic installation of Git using SystemInstaller.

        Raises:
            typer.Exit: With code 0 on success, or code 1 on failure.
        """
        self.ui.console.print("\n[bold cyan]Starting installation process...[/bold cyan]")
        
        success = SystemInstaller.install_package("git")

        if success:
            self.ui.print_success("Git has been installed successfully.")
            self.ui.console.print(
                "[bold magenta]IMPORTANT: Please restart your terminal to apply changes.[/bold magenta]"
            )
            raise typer.Exit(code=0)

        self.ui.print_error(
            "Failed to install Git automatically. Please install it manually."
        )
        raise typer.Exit(code=1)
