from typing import Any, List
from rich.table import Table

from .console import console
from .models import TableTheme
from .exceptions import TableRenderingError


def display_results_table(results: List[Any], theme: TableTheme = None) -> None:
    """Renders and displays a formatted table for repository statuses.

    Args:
        results (List[Any]): A list of objects containing table data.
        theme (TableTheme, optional): The theme configuration for styling 
            the table. Defaults to None (uses default TableTheme).

    Raises:
        TableRenderingError: If the results argument is not a list or if 
            there is an error parsing row data.
    """
    if theme is None:
        theme = TableTheme()

    if not isinstance(results, list):
        raise TableRenderingError("Expected 'results' to be a list.")

    if not results:
        console.print("[yellow]No results to display.[/yellow]")
        return

    table = Table(
        show_header=True,
        header_style=theme.header_style,
        border_style=theme.border_style,
        show_lines=theme.show_lines
    )

    table.add_column("Repository", justify="left")
    table.add_column("Branch", justify="center")
    table.add_column("Status", justify="center")

    try:
        for item in results:
            table.add_row(
                str(getattr(item, 'path', 'N/A')),
                str(getattr(item, 'branch', 'N/A')),
                str(getattr(item, 'status', 'N/A'))
            )
    except Exception as e:
        # Wrap arbitrary object parsing errors into a domain-specific UI error
        raise TableRenderingError(f"Failed to extract data for table row: {str(e)}")

    console.print(table)
