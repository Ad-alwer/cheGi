"""Service for the first-run wizard."""

import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

from chegi.services.wizard.constants import (
    BANNER,
    WELCOME_MESSAGE,
    WIZARD_MARKER_DIR,
    WIZARD_MARKER_FILE,
)
from chegi.ui import TerminalUI, console


class WizardService:
    """First-run wizard that guides new users through setup.

    Triggers on the first cheGi command, checks the environment,
    and offers to configure Git identity and project defaults.
    """

    def __init__(self, base_path: Optional[Path] = None) -> None:
        """Initializes the wizard.

        Args:
            base_path: The project base path. Defaults to CWD.
        """
        self.base_path = base_path or Path.cwd()

    def should_run(self) -> bool:
        """Checks if the wizard should run on this invocation.

        Returns:
            True if the wizard marker file does not exist.
        """
        return not os.path.isfile(WIZARD_MARKER_FILE)

    def _mark_completed(self) -> None:
        """Writes the marker file to prevent future wizard runs."""
        os.makedirs(WIZARD_MARKER_DIR, exist_ok=True)
        with open(WIZARD_MARKER_FILE, "w", encoding="utf-8") as f:
            f.write("done\n")

    @staticmethod
    def _check_git_installed() -> bool:
        """Checks if Git is available on the system.

        Returns:
            True if Git is installed.
        """
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def _get_git_config(key: str) -> Optional[str]:
        """Reads a single git config value.

        Args:
            key: The git config key to read.

        Returns:
            The value, or None if not set.
        """
        try:
            result = subprocess.run(
                ["git", "config", "--global", key],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip() or None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    @staticmethod
    def _set_git_identity(name: str, email: str) -> None:
        """Sets the global Git user name and email.

        Args:
            name: The user name to set.
            email: The user email to set.
        """
        subprocess.run(
            ["git", "config", "--global", "user.name", name],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "--global", "user.email", email],
            check=True,
            capture_output=True,
            text=True,
        )

    def execute(self) -> None:
        """Runs the first-run wizard."""
        if not self.should_run():
            return

        if not sys.stdin.isatty():
            return

        console.print()
        console.print(BANNER)
        console.print()
        console.print(WELCOME_MESSAGE)
        console.print()

        self._step_git_check()
        self._step_identity()
        self._step_project_config()

        self._mark_completed()
        console.print()
        TerminalUI.print_success("Wizard complete! Happy coding with cheGi. 🐆")

    def _step_git_check(self) -> None:
        """Step 1: Check if Git is installed."""
        if self._check_git_installed():
            TerminalUI.print_success("Git is installed.")
        else:
            TerminalUI.print_error("Git is not installed. Please install Git first.")
            raise typer.Exit(code=1)
        console.print()

    def _step_identity(self) -> None:
        """Step 2: Check and configure Git identity."""
        user_name = self._get_git_config("user.name")
        user_email = self._get_git_config("user.email")

        if user_name and user_email:
            TerminalUI.print_success(
                f"Git identity is set: [cyan]{user_name}[/cyan] <[cyan]{user_email}[/cyan]>"
            )
            console.print()
            return

        if not user_name and not user_email:
            TerminalUI.print_warning("Git identity is not configured.")
            console.print(
                "[dim]Commits need a name and email to be attributed correctly.[/dim]"
            )
        elif not user_name:
            TerminalUI.print_warning("Git [cyan]user.name[/cyan] is not set.")
        elif not user_email:
            TerminalUI.print_warning("Git [cyan]user.email[/cyan] is not set.")

        console.print()
        should_set = typer.confirm(
            "Would you like to configure Git identity now?", default=True
        )
        if not should_set:
            console.print(
                "[dim]Skipping identity setup. You can run [bold]chegi setup git[/bold] later.[/dim]"
            )
            console.print()
            return

        name_input = typer.prompt(
            "What is your name?",
            default=user_name or "",
            show_default=False,
        )
        email_input = typer.prompt(
            "What is your email?",
            default=user_email or "",
            show_default=False,
        )

        if not name_input or not email_input:
            TerminalUI.print_error(
                "Name and email are required. Skipping identity setup."
            )
            console.print()
            return

        try:
            self._set_git_identity(name_input, email_input)
            TerminalUI.print_success(
                f"Git identity set to: [cyan]{name_input}[/cyan] <[cyan]{email_input}[/cyan]>"
            )
        except subprocess.CalledProcessError:
            TerminalUI.print_error(
                "Failed to set Git identity. Please configure it manually."
            )
        console.print()

    def _step_project_config(self) -> None:
        """Step 3: Offer to create .chegi/ project config."""
        chegi_dir = self.base_path / ".chegi"
        if chegi_dir.is_dir():
            return

        should_create = typer.confirm(
            "Would you like to create a [bold].chegi/[/bold] project directory?"
            "\n[dim]This enables project-specific guard rules and config overrides.[/dim]",
            default=True,
        )
        if not should_create:
            console.print("[dim]Skipping project setup.[/dim]")
            console.print()
            return

        from chegi.services.init import InitService

        try:
            InitService.create_project_directory(self.base_path)
            TerminalUI.print_success(
                f".chegi/ created at [cyan]{shlex.quote(str(chegi_dir))}[/cyan]"
            )
        except Exception as e:
            TerminalUI.print_error(f"Failed to create .chegi/: {e}")

        console.print()
