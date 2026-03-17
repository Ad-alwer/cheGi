from typing import List
from rich.console import Console
from rich.table import Table
from chegi.git_utils import GitStatus

class TerminalUI:
    """
    Handles all visual outputs in the terminal using the Rich library.
    """
    def __init__(self):
        # The Console object is the main entry point for Rich features
        self.console = Console()

    def print_error(self, message: str) -> None:
        """
        Prints a formatted error message in red.

        Args:
            message (str): The error message to display.
        """
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_warning(self, message: str) -> None:
        """
        Prints a formatted warning message in yellow.

        Args:
            message (str): The warning message to display.
        """
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def display_results_table(self, statuses: List[GitStatus]) -> None:
        """
        Builds and displays a formatted, color-coded table of Git repository statuses.

        Args:
            statuses (List[GitStatus]): A list of parsed GitStatus objects to render in the table.
        """
        if not statuses:
            self.console.print("[bold yellow]No Git repositories found in the specified path.[/bold yellow]")
            return

        # Initialize the table
        table = Table(
            title="📦 Git Repositories Status",
            show_header=True,
            header_style="bold magenta",
            title_style="bold cyan",
            title_justify="left"
        )

        # Add columns
        table.add_column("Repository", style="cyan", no_wrap=True)
        table.add_column("Branch", style="blue")
        table.add_column("Local Status", justify="center")
        table.add_column("Remote", justify="center")

        # Sort statuses alphabetically by repo name before displaying
        sorted_statuses = sorted(statuses, key=lambda s: s.repo_name.lower())

        # Populate rows
        for status in sorted_statuses:
            if status.error:
                # Handle repos that failed to be analyzed
                table.add_row(
                    status.repo_name, 
                    "N/A", 
                    f"[red]Error[/red]", 
                    f"[dim]{status.error}[/dim]"
                )
                continue

            # Color coding logic for Local Status (Dirty/Clean)
            if status.is_dirty:
                local_status_ui = "[red]✗ Dirty[/red]"
            else:
                local_status_ui = "[green]✓ Clean[/green]"

            # Color coding logic for Remote
            if status.has_remote:
                remote_ui = "[green]✓ Synced[/green]"
            else:
                remote_ui = "[yellow]⚠ No Remote[/yellow]"

            table.add_row(
                status.repo_name,
                status.branch,
                local_status_ui,
                remote_ui
            )

        # Print the final table to the terminal
        self.console.print(table)
