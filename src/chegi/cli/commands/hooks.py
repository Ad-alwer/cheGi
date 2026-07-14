"""CLI command for chegi hooks — manage Git hooks with guard integration."""

from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from chegi.services.hooks import HooksService, HookType
from chegi.ui import TerminalUI, console

app = typer.Typer(help="Manage Git hooks with automatic guard scanning.")


@app.callback(invoke_without_command=True)
def hooks(
    ctx: typer.Context,
) -> None:
    """Manage Git hooks with automatic guard scanning.

    Install hooks that run [bold]chegi guard[/bold] before commits
    or pushes, automatically blocking sensitive data from leaking.
    """
    if ctx.invoked_subcommand is not None:
        return

    console.print("[dim]Use [bold]chegi hooks install[/bold] to install a guard hook.")
    console.print(
        "[dim]Use [bold]chegi hooks status[/bold] to check installation status.[/dim]"
    )
    console.print("[dim]Use [bold]chegi hooks remove[/bold] to remove it.[/dim]")
    console.print("")
    console.print("[dim]By default, hooks target pre-commit.[/dim]")
    console.print("[dim]Use [bold]--pre-push[/bold] for pre-push hooks.[/dim]")


def _get_hook_type(pre_push: bool) -> HookType:
    """Return the hook type based on the --pre-push flag.

    Args:
        pre_push: Whether the pre-push hook type is requested.

    Returns:
        The corresponding HookType enum value.
    """
    return HookType.PRE_PUSH if pre_push else HookType.PRE_COMMIT


def _type_display(hook_type: HookType) -> str:
    """Return human-readable display string for hook type.

    Args:
        hook_type: The hook type.

    Returns:
        Display name like "pre-commit" or "pre-push".
    """
    return hook_type.value


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
            help="Overwrite existing hook if present",
        ),
    ] = False,
    pre_push: Annotated[
        bool,
        typer.Option(
            "--pre-push",
            help="Install a pre-push hook instead of a pre-commit hook",
        ),
    ] = False,
) -> None:
    """Install a Git hook that auto-runs [bold]chegi guard[/bold].

    By default installs a pre-commit hook that runs [bold]chegi guard --fix[/bold]
    before every commit. Use [bold]--pre-push[/bold] to install a pre-push hook
    instead.
    """
    hook_type = _get_hook_type(pre_push)
    type_name = _type_display(hook_type)
    repo_path = path or Path.cwd()
    service = HooksService(repo_path)

    try:
        hook_path = service.install(hook_type=hook_type, force=force)
    except Exception as exc:
        TerminalUI.print_error(str(exc))
        raise typer.Exit(code=1)

    console.print(
        f"[bold green]✅ {type_name.title()} hook installed at:[/bold green] {hook_path}"
    )
    if hook_type == HookType.PRE_COMMIT:
        console.print(
            "[dim]The hook will run [bold]chegi guard --fix[/bold] before every commit.[/dim]"
        )
    else:
        console.print(
            "[dim]The hook will run [bold]chegi guard[/bold] before every push.[/dim]"
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
    pre_push: Annotated[
        bool,
        typer.Option(
            "--pre-push",
            help="Remove a pre-push hook instead of a pre-commit hook",
        ),
    ] = False,
) -> None:
    """Remove the cheGi Git hook.

    Only removes hooks previously installed by [bold]chegi hooks install[/bold].
    Custom hooks are left untouched. By default targets pre-commit;
    use [bold]--pre-push[/bold] for pre-push hooks.
    """
    hook_type = _get_hook_type(pre_push)
    type_name = _type_display(hook_type)
    repo_path = path or Path.cwd()
    service = HooksService(repo_path)

    try:
        removed = service.remove(hook_type=hook_type)
    except Exception as exc:
        TerminalUI.print_error(str(exc))
        raise typer.Exit(code=1)

    if removed:
        console.print(f"[bold green]✅ cheGi {type_name} hook removed.[/bold green]")
    else:
        console.print(
            f"[bold yellow]⚠️  No cheGi {type_name} hook found. Nothing to remove.[/bold yellow]"
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
    pre_push: Annotated[
        bool,
        typer.Option(
            "--pre-push",
            help="Check pre-push hook status instead of pre-commit",
        ),
    ] = False,
) -> None:
    """Check whether the cheGi Git hook is installed.

    By default checks pre-commit; use [bold]--pre-push[/bold] for pre-push.
    Reports the installation status and hook file path.
    """
    hook_type = _get_hook_type(pre_push)
    type_name = _type_display(hook_type)
    repo_path = path or Path.cwd()
    service = HooksService(repo_path)
    info = service.is_installed(hook_type=hook_type)

    if info.installed:
        console.print(
            f"[bold green]✅ cheGi {type_name} hook is installed[/bold green]"
        )
        console.print(f"[dim]   Path: {info.path}[/dim]")
    else:
        console.print(
            f"[bold yellow]⚠️  cheGi {type_name} hook is not installed[/bold yellow]"
        )
