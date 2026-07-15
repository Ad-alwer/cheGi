"""CLI command for syncing the Git repository."""

from pathlib import Path

import typer

from chegi.services.git.client import GitClient
from chegi.services.git.exceptions import GitCoreError
from chegi.services.sync.sync_service import SyncService
from chegi.ui import TerminalUI, console

app = typer.Typer(help="Sync the current Git repository.")

_AUTH_ERROR_KEYWORDS = [
    "authentication failed",
    "invalid username or password",
    "could not read username",
    "could not read password",
    "403",
    "401",
    "access denied",
    "access token",
]


def _is_auth_error(error_message: str) -> bool:
    """Checks if an error message indicates an authentication failure."""
    msg_lower = error_message.lower()
    return any(kw in msg_lower for kw in _AUTH_ERROR_KEYWORDS)


def _suggest_auth_setup() -> None:
    """Suggests the user set up Git authentication."""
    console.print()
    TerminalUI.print_warning("This looks like an authentication issue.")
    console.print(
        "  Run [bold]chegi auth login[/bold] to set up token-based authentication."
    )
    console.print(
        "  Or set up a Git credential helper with "
        "[bold]chegi auth login[/bold] to avoid future issues."
    )
    console.print()


@app.callback(invoke_without_command=True)
def sync() -> None:
    """Syncs the current branch with the remote repository.

    Performs a safe sync by checking workspace cleanliness, stashing
    uncommitted changes if necessary, pulling with rebase, pushing
    local commits, and restoring the stash if it was created.

    Raises:
        typer.Exit: If a Git operation fails (code 1) or an unexpected error occurs.
    """
    repo_path = Path.cwd()

    try:
        git_client = GitClient(repo_path)
        git_client.check_git_installation()

        sync_service = SyncService(git_client)

        is_clean = git_client.is_workspace_clean()
        if not is_clean:
            console.print(
                "[yellow]Workspace is not clean. Stashing changes...[/yellow]"
            )
            sync_service.stash_changes()

        try:
            console.print("[cyan]Pulling changes from remote (rebase)...[/cyan]")
            sync_service.pull_rebase()

            console.print("[cyan]Pushing local commits to remote...[/cyan]")
            sync_service.push_changes()

            console.print(
                "[bold green]Repository synced successfully! \u2728[/bold green]"
            )

        finally:
            if not is_clean:
                console.print("[yellow]Popping stashed changes...[/yellow]")
                try:
                    sync_service.pop_stash()
                except Exception as stash_err:
                    console.print(
                        f"[bold red]Warning: Could not automatically pop stash."
                        f" Details: {stash_err}[/bold red]"
                    )

    except GitCoreError as e:
        error_msg = str(e)
        console.print(f"[bold red]Sync Failed:[/bold red]\n{error_msg}")
        if _is_auth_error(error_msg):
            _suggest_auth_setup()
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred:[/bold red]\n{e}")
        raise typer.Exit(code=1)
