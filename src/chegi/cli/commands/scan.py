from typing import Annotated, Optional

import typer

from chegi.services.scanner.models import ScanOptions
from chegi.services.scanner.scan_service import ScanService

app = typer.Typer()


@app.callback(invoke_without_command=True)
def scan_command(
    path: str = typer.Argument(".", help="Base directory to scan"),
    max_depth: Optional[int] = typer.Option(
        None, "--max-depth", "-d", help="Override max depth from config"
    ),
    workers: int = typer.Option(
        5, "--workers", "-w", help="Number of concurrent workers"
    ),
    security: Annotated[
        bool,
        typer.Option("--security", "-s", help="Perform security scan on repositories"),
    ] = False,
    dirty: Annotated[
        bool,
        typer.Option("--dirty", help="Only show repositories with uncommitted changes"),
    ] = False,
    staged: Annotated[
        bool, typer.Option("--staged", help="Only show repositories with staged files")
    ] = False,
) -> None:
    """Scans a directory recursively for Git repositories and reports their status.

    Args:
        path (str): Base directory to start the scan.
        max_depth (Optional[int]): Depth limit for directory traversal.
        workers (int): Thread count for concurrent repository analysis.
        security (bool): Enables vulnerability/security checks.
        dirty (bool): Filters output to show only repositories with uncommitted changes.
        staged (bool): Filters output to show only repositories with staged files.
    """
    options = ScanOptions(
        path=path,
        max_depth=max_depth,
        workers=workers,
        security=security,
        dirty=dirty,
        staged=staged,
    )

    service = ScanService(options=options)
    service.execute()
