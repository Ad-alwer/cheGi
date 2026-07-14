"""CLI command for chegi hooks — manage Git hooks with guard integration."""

from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from chegi.services.hooks import HooksService
from chegi.ui import TerminalUI, console

app = typer.Typer(help="Manage Git hooks with automatic guard scanning.")


@app.callback(invoke_without_command=True)
def hooks(
    ctx: typer.Context,
) -> None:
    """Manage Git hooks with automatic guard scanning.

    Install a pre-commit hook that runs [bold]chegi guard --fix[/bold]
    before every commit, automatically unstaging sensitive files and
    aborting the commit when threats are detected.
    """
    if ctx.invoked_subcommand is not None:
        return

    console.print(
        "[dim]Use [bold]chegi hooks install[/bold] to install the guard hook."
    )
    console.print(
        "[dim]Use [bold]chegi hooks status[/bold] to check installation status.[/dim]"
    )
    console.print("[dim]Use [bold]chegi hooks remove[/bold] to remove it.[/dim]")


@app.command()
def install(
    path: Annotated[
        Optional[Path],
        typer.Option(
            "--path",
            "-p",
            help="Path to the Git repository",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Overwrite existing pre-commit hook if present",
        ),
    ] = False,
) -> None:
    """Install a pre-commit hook that auto-runs [bold]chegi guard --fix[/bold].

    The hook runs before every [bold]git commit[/bold]. If sensitive
    files are staged, they are automatically unstaged and the commit
    is aborted with a clear message.
    """
    repo_path = path or Path.cwd()
    service = HooksService(repo_path)

    try:
        hook_path = service.install(force=force)
    except Exception as exc:
        TerminalUI.print_error(str(exc))
        raise typer.Exit(code=1)

    console.print(
        f"[bold green]✅ Pre-commit hook installed at:[/bold green] {hook_path}"
    )
    console.print(
        "[dim]The hook will run [bold]chegi guard --fix[/bold] before every commit.[/dim]"
    )


@app.command()
def remove(
    path: Annotated[
        Optional[Path],
        typer.Option(
            "--path",
            "-p",
            help="Path to the Git repository",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
        ),
    ] = None,
) -> None:
    """Remove the cheGi pre-commit hook.

    Only removes hooks previously installed by [bold]chegi hooks install[/bold].
    Custom pre-commit hooks are left untouched.
    """
    repo_path = path or Path.cwd()
    service = HooksService(repo_path)

    try:
        removed = service.remove()
    except Exception as exc:
        TerminalUI.print_error(str(exc))
        raise typer.Exit(code=1)

    if removed:
        console.print("[bold green]✅ cheGi pre-commit hook removed.[/bold green]")
    else:
        console.print(
            "[bold yellow]⚠️  No cheGi pre-commit hook found. Nothing to remove.[/bold yellow]"
        )


@app.command()
def status(
    path: Annotated[
        Optional[Path],
        typer.Option(
            "--path",
            "-p",
            help="Path to the Git repository",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
        ),
    ] = None,
) -> None:
    """Check whether the cheGi pre-commit hook is installed.

    Reports the installation status and hook file path.
    """
    repo_path = path or Path.cwd()
    service = HooksService(repo_path)
    info = service.is_installed()

    if info.installed:
        console.print("[bold green]✅ cheGi pre-commit hook is installed[/bold green]")
        console.print(f"[dim]   Path: {info.path}[/dim]")
    else:
        console.print(
            "[bold yellow]⚠️  cheGi pre-commit hook is not installed[/bold yellow]"
        )
