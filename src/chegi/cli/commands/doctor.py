"""CLI command for chegi doctor — comprehensive project health check."""

from pathlib import Path
from typing import Optional

import typer
from rich.text import Text
from typing_extensions import Annotated

from chegi.services.doctor import CheckCategory, DoctorService
from chegi.ui import TerminalUI, console

app = typer.Typer(
    help="Check your project health, security posture, and Git statistics.",
)


@app.callback(invoke_without_command=True)
def doctor(
    ctx: typer.Context,
    path: Annotated[
        Optional[str],
        typer.Option(
            "--path",
            "-p",
            help="Path to the project directory to check",
        ),
    ] = None,
) -> None:
    """Run a comprehensive health check on your project.

    Checks Git installation, identity, .gitignore, .chegi/ config,
    staged sensitive files, .env tracking, pre-commit hooks,
    commit history, branches, and remote status.
    """
    if ctx.invoked_subcommand is not None:
        return

    target = Path(path).resolve() if path else Path.cwd()

    if not target.is_dir():
        TerminalUI.print_error(f"Directory does not exist: {target}")
        raise typer.Exit(code=1)

    console.print("\n[bold gold1]🐆 cheGi Doctor[/bold gold1]")
    console.print(f"[dim]Checking: {target}[/dim]\n")

    service = DoctorService(target)
    report = service.run()

    _display_report(report)

    if report.fail_count > 0 or report.warn_count > 0:
        raise typer.Exit(code=1)


def _display_report(report) -> None:
    """Displays the doctor report in a Rich table.

    Args:
        report: DoctorReport to display.
    """
    current_category = None

    for result in report.results:
        if result.category != current_category:
            current_category = result.category
            _display_category_header(current_category)

        _display_check_row(result)

    _display_summary(report)


def _display_category_header(category: CheckCategory) -> None:
    """Displays a category header.

    Args:
        category: The check category.
    """
    icon = {
        CheckCategory.HEALTH: "🩺",
        CheckCategory.SECURITY: "🔒",
        CheckCategory.STATS: "📊",
    }.get(category, "")

    console.print(f"\n  [bold]{icon} {category.value}[/bold]")


def _display_check_row(result) -> None:
    """Displays a single check result row.

    Args:
        result: CheckResult to display.
    """
    status_tag = Text(result.status.emoji, style=result.status.rich_style)
    name = Text(f"  {result.name}", style="bold")
    message = Text(f"  {result.message}", style="dim")

    console.print(f"    {status_tag} {name}{message}")

    if result.suggestion:
        console.print(f"       [dim italic]→ {result.suggestion}[/dim italic]")


def _display_summary(report) -> None:
    """Displays the check summary.

    Args:
        report: DoctorReport with aggregated counts.
    """
    console.print()

    if report.fail_count > 0:
        summary_style = "bold red"
        prefix = "✗"
    elif report.warn_count > 0:
        summary_style = "bold yellow"
        prefix = "⚠"
    else:
        summary_style = "bold green"
        prefix = "✓"

    parts = []
    if report.pass_count > 0:
        parts.append(f"[green]{report.pass_count} passed[/green]")
    if report.warn_count > 0:
        parts.append(f"[yellow]{report.warn_count} warnings[/yellow]")
    if report.fail_count > 0:
        parts.append(f"[red]{report.fail_count} failed[/red]")
    if report.skip_count > 0:
        parts.append(f"[dim]{report.skip_count} skipped[/dim]")

    summary_text = f"  {prefix} [bold]{report.total}[/bold] checks: {', '.join(parts)}"
    console.print(summary_text, style=summary_style)
    console.print()
