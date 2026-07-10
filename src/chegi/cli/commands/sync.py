"""CLI command for syncing the Git repository."""

from pathlib import Path

import typer

from chegi.services.git.client import GitClient
from chegi.services.git.exceptions import GitCoreError
from chegi.services.sync.sync_service import SyncService
from chegi.ui.console import console

app = typer.Typer(help="Sync the current Git repository.")


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

            console.print("[bold green]Repository synced successfully! ✨[/bold green]")

        finally:
            # Ensure stash is restored even if pull or push fails
            if not is_clean:
                console.print("[yellow]Popping stashed changes...[/yellow]")
                try:
                    sync_service.pop_stash()
                except Exception as stash_err:
                    console.print(
                        f"[bold red]Warning: Could not automatically pop stash. Details: {stash_err}[/bold red]"
                    )

    except GitCoreError as e:
        console.print(f"[bold red]Sync Failed:[/bold red]\n{e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred:[/bold red]\n{e}")
        raise typer.Exit(code=1)
