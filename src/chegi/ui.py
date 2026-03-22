from typing import List
from rich.console import Console
from rich.table import Table
from chegi.git_utils import GitStatus

class TerminalUI:
    """Handles all visual outputs in the terminal using the Rich library.

    Attributes:
        console (Console): The main entry point for Rich terminal features.
    """

    def __init__(self):
        """Initializes the TerminalUI."""
        self.console = Console()

    def print_error(self, message: str) -> None:
        """Prints a formatted error message in red.

        Args:
            message (str): The error message to display.

        Returns:
            None
        """
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_warning(self, message: str) -> None:
        """Prints a formatted warning message in yellow.

        Args:
            message (str): The warning message to display.

        Returns:
            None
        """
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def display_results_table(self, statuses: List[GitStatus]) -> None:
        """Builds and displays a formatted, color-coded table of Git repository statuses.

        Args:
            statuses (List[GitStatus]): A list of parsed GitStatus objects to render.

        Returns:
            None
        """
        if not statuses:
            self.console.print("[bold yellow]No Git repositories found in the specified path.[/bold yellow]")
            return

        show_security = any(s.security_status is not None for s in statuses)

        table = Table(
            title="📦 Git Repositories Status",
            show_header=True,
            header_style="bold magenta",
            title_style="bold cyan",
            title_justify="left"
        )

        table.add_column("Repository", style="cyan", no_wrap=True)
        table.add_column("Branch", style="blue")
        table.add_column("Local Status", justify="center")
        table.add_column("Remote", justify="center")

        if show_security:
            table.add_column("Security 🛡️", justify="left")

        sorted_statuses = sorted(statuses, key=lambda s: s.repo_name.lower())

        for status in sorted_statuses:
            if status.error:
                row_data = [
                    status.repo_name, 
                    "N/A", 
                    "[red]Error[/red]", 
                    f"[dim]{status.error}[/dim]"
                ]
                if show_security:
                    row_data.append("-")
                
                table.add_row(*row_data)
                continue

            if status.is_dirty:
                local_status_ui = "[red]✗ Dirty[/red]"
            else:
                local_status_ui = "[green]✓ Clean[/green]"

            if status.has_remote:
                remote_ui = "[green]✓ Synced[/green]"
            else:
                remote_ui = "[yellow]⚠ No Remote[/yellow]"

            row_data = [
                status.repo_name,
                status.branch,
                local_status_ui,
                remote_ui
            ]

            if show_security:
                sec_display = status.security_status if status.security_status else "[dim]N/A[/dim]"
                row_data.append(sec_display)

            table.add_row(*row_data)

        self.console.print(table)
