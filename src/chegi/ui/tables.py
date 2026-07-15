"""Table rendering for cheGi with theme support."""

from typing import Any, List, Optional

from rich.table import Table

from .console import TerminalUI, console
from .exceptions import TableRenderingError
from .models import TableTheme


def _get_table_theme() -> TableTheme:
    """Loads the table theme from the active cheGi theme.

    Returns:
        The active TableTheme.
    """
    return TerminalUI.get_active_theme().table


def display_results_table(
    results: List[Any], theme: Optional[TableTheme] = None
) -> None:
    """Renders and displays a formatted table for repository statuses.

    Args:
        results: A list of objects containing table data.
        theme: Optional override TableTheme. Uses active cheGi theme if None.

    Raises:
        TableRenderingError: If the results argument is not a list or if
            there is an error parsing row data.
    """
    if theme is None:
        theme = _get_table_theme()

    if not isinstance(results, list):
        raise TableRenderingError("Expected 'results' to be a list.")

    if not results:
        console.print("[yellow]No results to display.[/yellow]")
        return

    table = Table(
        show_header=True,
        header_style=theme.header_style,
        border_style=theme.border_style,
        show_lines=theme.show_lines,
    )

    table.add_column("Repository", justify="left")
    table.add_column("Branch", justify="center")
    table.add_column("Status", justify="center")

    try:
        for item in results:
            table.add_row(
                str(getattr(item, "path", "N/A")),
                str(getattr(item, "branch", "N/A")),
                str(getattr(item, "status", "N/A")),
            )
    except Exception as e:
        raise TableRenderingError(f"Failed to extract data for table row: {str(e)}")

    console.print(table)
