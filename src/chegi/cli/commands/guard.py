import typer
from typing import Annotated
from pathlib import Path

from chegi.ui import TerminalUI
from chegi.services.guard import SecurityGuard
from chegi.services.git.client import GitClient

app = typer.Typer(help="Checks staged files for sensitive data to prevent accidental commits.")


@app.callback(invoke_without_command=True)
def guard(
    ctx: typer.Context,
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            "-f",
            help="Automatically unstage sensitive files without prompting",
        ),
    ] = False,
) -> None:
    """Checks staged files for sensitive data to prevent accidental commits.

    Scans currently staged files against known sensitive patterns (e.g., .env, keys).
    If sensitive files are detected, it can automatically unstage them or prompt
    the user for action.

    Args:
        ctx (typer.Context): The Typer context.
        fix (bool, optional): Automatically unstage detected files without prompting. Defaults to False.

    Raises:
        typer.Exit: Exits with code 1 if sensitive files are found (for pre-commit hooks).
    """
    if ctx.invoked_subcommand is not None:
        return

    ui = TerminalUI()
    
    # Check if we are inside a valid git repository
    git_client = GitClient(Path.cwd())
    if not git_client.is_valid_repo():
        ui.print_error("fatal: not a git repository (or any of the parent directories): .git")
        raise typer.Exit(code=1)

    ui.console.print("[dim]🔒 Running Security Guard...[/dim]")

    staged_files = SecurityGuard.get_staged_files()
    if not staged_files:
        ui.console.print(
            "[bold blue]No staged files found. Nothing to check.[/bold blue]"
        )
        raise typer.Exit()

    sensitive_files = SecurityGuard.find_sensitive_files(staged_files)

    if sensitive_files:
        ui.console.print(
            "\n[bold red]⚠️  WARNING: Sensitive files detected in staging area![/bold red]"
        )
        for f in sensitive_files:
            ui.console.print(f"  [red]- {f}[/red]")

        files_str = " ".join(sensitive_files)
        exact_command = f"git rm --cached {files_str}"
        ui.console.print(
            f"\n[bold yellow]To fix this manually, run:[/bold yellow] [cyan]{exact_command}[/cyan]\n"
        )

        if fix:
            success = SecurityGuard.unstage_files(sensitive_files)
            if success:
                ui.console.print(
                    "\n[bold green]✅ Files successfully unstaged automatically (via --fix). You can now commit safely.[/bold green]"
                )
            else:
                ui.print_error(
                    "\nFailed to unstage files automatically. Please run the command manually."
                )
        else:
            should_unstage = typer.confirm(
                "Do you want cheGi to automatically unstage these files for you?"
            )

            if should_unstage:
                success = SecurityGuard.unstage_files(sensitive_files)
                if success:
                    ui.console.print(
                        "\n[bold green]✅ Files successfully unstaged. You can now commit safely.[/bold green]"
                    )
                else:
                    ui.print_error(
                        "\nFailed to unstage files automatically. Please run the command manually."
                    )

        # Exit with code 1 for CI/CD or pre-commit hooks
        raise typer.Exit(code=1)
    else:
        ui.console.print(
            "[bold green]✅ Security check passed. No sensitive files found in staging.[/bold green]"
        )
