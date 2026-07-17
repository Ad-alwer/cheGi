"""CLI command for chegi upgrade — self-upgrade command."""

import typer
from typing_extensions import Annotated

from chegi.services.upgrade import UpgradeError, UpgradeService
from chegi.ui import TerminalUI, console

app = typer.Typer(
    help="Check for and install the latest version of cheGi.",
)


@app.callback(invoke_without_command=True)
def upgrade(
    check: Annotated[
        bool,
        typer.Option("--check", "-c", help="Only check for updates, don't upgrade"),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Check for updates and upgrade cheGi to the latest version."""
    service = UpgradeService()

    current = service.get_current_version()
    console.print(f"[dim]Current version: [bold]{current}[/][/dim]")
    console.print()

    info = service.check_version()

    if info.error:
        TerminalUI.print_error(info.error)
        raise typer.Exit(code=1)

    console.print(f"[bold]Latest version:[/] [bold cyan]{info.latest_version}[/]")

    if not info.is_outdated:
        TerminalUI.print_success("You're already on the latest version!")
        raise typer.Exit()

    console.print()
    if info.changelog_diff:
        console.print("[bold]What's new:[/]")
        console.print(info.changelog_diff)
        console.print()

    TerminalUI.print_warning(
        f"A new version [bold]{info.latest_version}[/] is available!"
    )

    if check:
        console.print(
            f"[dim]Run [bold]chegi upgrade[/] to upgrade to {info.latest_version}.[/dim]"
        )
        raise typer.Exit()

    if not yes and not typer.confirm("Upgrade now?", default=True):
        console.print(
            "[dim]Run [bold]chegi upgrade[/] anytime to upgrade to the latest version.[/dim]"
        )
        raise typer.Exit()

    try:
        service.upgrade(yes=True)
    except UpgradeError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    TerminalUI.print_success(f"Successfully upgraded to v{info.latest_version}!")
