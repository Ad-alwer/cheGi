"""Service for interacting with the GitHub CLI (gh)."""

import subprocess
from typing import Optional


class GhService:
    """Service for checking and managing GitHub CLI (gh) installation and auth."""

    @staticmethod
    def get_version() -> Optional[str]:
        """Returns the installed gh version, or None if not installed.

        Returns:
            Version string (e.g. 2.45.0) or None.
        """
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout.strip()
            if output:
                parts = output.split()
                for part in parts:
                    part = part.strip(" ,v")
                    if part.replace(".", "").isdigit():
                        return part
            return None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    @staticmethod
    def check_installed() -> bool:
        """Checks if gh CLI is installed.

        Returns:
            True if gh is installed, False otherwise.
        """
        return GhService.get_version() is not None

    @staticmethod
    def check_auth() -> bool:
        """Checks if the user is authenticated with gh CLI.

        Returns:
            True if authenticated, False otherwise.
        """
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    @staticmethod
    def login() -> bool:
        """Initiates gh auth login interactively.

        Returns:
            True if login succeeded, False otherwise.
        """
        try:
            result = subprocess.run(
                ["gh", "auth", "login"],
                capture_output=False,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    @staticmethod
    def ensure_authenticated() -> bool:
        """Ensures the user is authenticated with gh CLI.

        If not authenticated, attempts to log in interactively.

        Returns:
            True if authenticated after the attempt, False otherwise.
        """
        if GhService.check_auth():
            return True
        print()
        print("  GitHub CLI (gh) is not authenticated.")
        print("  You need to log in to use GitHub features.")
        print()
        from chegi.ui import console

        console.print("  [dim]Running [bold]gh auth login[/bold]...[/dim]")
        print()
        return GhService.login()
