from pathlib import Path
from typing import Optional

import questionary
import typer

from chegi.services.git.client import GitClient
from chegi.services.git.exceptions import GitCoreError
from chegi.services.reword.reword_service import RewordService
from chegi.ui.console import console

app = typer.Typer(help="Reword a specific commit message.")


@app.callback(invoke_without_command=True)
def reword(
    message: Optional[str] = typer.Argument(None, help="The new commit message"),
    last: Optional[int] = typer.Option(
        None, "--last", "-l", help="Number of recent commits to choose from", min=1
    ),
    start: Optional[int] = typer.Option(
        None, "--start", "-s", help="Start index for commit list", min=0
    ),
    end: Optional[int] = typer.Option(
        None, "--end", "-e", help="End index for commit list", min=1
    ),
) -> None:
    git_client = GitClient(repo_path=Path.cwd())
    reword_service = RewordService(git_client=git_client)

    try:
        git_client.check_git_installation()
    except GitCoreError as e:
        console.print(f"[bold red]❌ {e}[/bold red]")
        raise typer.Exit(1)

    if last is not None and last > 20:
        console.print("[bold red]❌ Maximum limit for --last is 20.[/bold red]")
        raise typer.Exit(1)

    target_hash = "HEAD"
    show_menu = any([last, start, end])

    try:
        if show_menu:
            skip, limit = reword_service.calculate_pagination(last, start, end)
            commits = reword_service.get_commits(skip, limit)

            if not commits:
                console.print(
                    "[bold red]❌ No commits found in the specified range.[/bold red]"
                )
                raise typer.Exit(1)

            choice = questionary.select(
                "Select the commit to reword:", choices=commits
            ).ask()
            if not choice:
                raise typer.Exit(0)

            target_hash = choice.split(" ")[0]

        is_head = reword_service.is_head(target_hash)
        old_message = reword_service.get_commit_message(target_hash)

        if not message:
            message = questionary.text(
                "Enter new commit message:", default=old_message
            ).ask()
            if not message:
                console.print("[bold red]❌ Commit message cannot be empty.[/bold red]")
                raise typer.Exit(1)

        if message == old_message:
            console.print("[bold green]✅ Message is unchanged. Exiting.[/bold green]")
            return

        if is_head:
            reword_service.amend_head(message)
        else:
            console.print(
                f"[cyan]Rewording commit [bold]{target_hash}[/bold]...[/cyan]"
            )
            reword_service.perform_automated_rebase(target_hash, message)

        console.print(
            "[bold green]✅ Commit message updated successfully! ✨[/bold green]"
        )

    except ValueError as ve:
        console.print(f"[bold red]❌ {ve}[/bold red]")
        raise typer.Exit(1)
    except GitCoreError as e:
        console.print(f"[bold red]❌ Failed to update commit:[/bold red]\n{e}")
        raise typer.Exit(1)
