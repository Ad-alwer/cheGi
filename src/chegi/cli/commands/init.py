"""CLI command for initializing a cheGi project."""

import os
import shutil
from pathlib import Path

import typer
from typing_extensions import Annotated

from chegi.services.git_config import GitConfigService
from chegi.services.init import InitService
from chegi.ui import TerminalUI, console

app = typer.Typer(help="Initialize a cheGi project with .chegi/ directory.")


@app.callback(invoke_without_command=True)
def init(
    ctx: typer.Context,
    path: Annotated[
        str,
        typer.Option(
            "--path",
            "-p",
            help="Project root directory where .chegi/ will be created",
        ),
    ] = ".",
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Overwrite existing .chegi/ directory",
        ),
    ] = False,
) -> None:
    """Initialize a cheGi project by creating a .chegi/ directory.

    This sets up project-specific configuration, guard rules, and ignore
    patterns so that cheGi can operate with per-project settings.
    """
    if ctx.invoked_subcommand is not None:
        return

    target_path = Path(path).resolve()

    if not target_path.is_dir():
        TerminalUI.print_error(f"Directory does not exist: {target_path}")
        raise typer.Exit(code=1)

    chegi_dir = target_path / ".chegi"
    if chegi_dir.exists() and not force:
        TerminalUI.print_warning(
            f"A .chegi/ directory already exists at {target_path}.\n"
            f"  Use 'chegi init --force' to overwrite."
        )
        raise typer.Exit(code=1)

    if force and chegi_dir.exists():
        shutil.rmtree(chegi_dir)

    InitService.create_project_directory(target_path)

    # ── Offer to set Git identity if missing ──
    name, email = GitConfigService.get_identity()
    if not name or not email:
        console.print()
        console.print("[bold]👤 Git Identity[/bold]")
        console.print("[dim]Configure your Git user name and email for commits.[/dim]")
        should_set = typer.confirm(
            "  Would you like to set Git identity?", default=True
        )
        if should_set:
            new_name = name or os.environ.get("USER", "")
            if not name:
                new_name = typer.prompt("  Enter your name", default=new_name)
            new_email = email or ""
            if not email:
                new_email = typer.prompt("  Enter your email", default=new_email)
            if new_name and new_email:
                GitConfigService.set_identity(new_name, new_email)
                TerminalUI.print_success(
                    f"Git identity set to: [cyan]{new_name}[/cyan] <[cyan]{new_email}[/cyan]>"
                )

    console.print()
    TerminalUI.print_success(
        f"cheGi project initialized at [bold cyan]{target_path}[/bold cyan]"
    )
    console.print()
    console.print("  [gold1]📂[/gold1] [bold].chegi/[/bold] directory created")
    console.print(
        "  [gold1]  ├──[/gold1] [dim]config.json[/dim]    [dim]Project configuration[/dim]"
    )
    console.print(
        "  [gold1]  ├──[/gold1] [dim]guard-rules.json[/dim] [dim]Sensitive file patterns[/dim]"
    )
    console.print(
        "  [gold1]  └──[/gold1] [dim].chegiignore[/dim]     [dim]Scan exclusion patterns[/dim]"
    )
    console.print()
    console.print("  [dim]Run [bold]chegi guard[/bold] to scan staged files.[/dim]")
