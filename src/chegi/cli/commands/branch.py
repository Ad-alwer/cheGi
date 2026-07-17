"""CLI command for chegi branch — branch manager with interactive and direct modes."""

from pathlib import Path
from typing import List, Optional

import questionary
import typer
from rich.table import Table
from rich.text import Text
from typing_extensions import Annotated

from chegi.services.branch import BranchError, BranchService, ProtectedBranchError
from chegi.services.branch.constants import PROTECTED_BRANCHES
from chegi.ui import TerminalUI, console

app = typer.Typer(
    help="Manage Git branches — create, list, switch, merge, rename, delete, sync, and more.",
)


@app.callback(invoke_without_command=True)
def branch(
    ctx: typer.Context,
) -> None:
    """Interactive branch manager or direct subcommand."""
    if ctx.invoked_subcommand is not None:
        return

    _interactive_menu()


@app.command(name="list")
def list_branches(
    remote: Annotated[
        bool,
        typer.Option("--remote", "-r", help="Show remote-tracking branches"),
    ] = False,
) -> None:
    """List all local branches with metadata."""
    service = _get_service()

    try:
        branches = service.list_branches(remote=remote)
    except BranchError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    if not branches:
        label = "remote" if remote else "local"
        console.print(f"[dim]No {label} branches found.[/dim]")
        return

    table = Table(
        title=f"{'Remote' if remote else 'Local'} Branches",
        title_style="bold gold1",
        border_style="gold1",
    )
    table.add_column("Name", style="bold")
    table.add_column("Last Commit", style="dim")
    table.add_column("Author", style="cyan")
    table.add_column("Upstream", style="blue")

    for b in branches:
        name = b.name
        if b.is_current:
            name = f"* {name}"
        upstream = b.upstream or ""
        table.add_row(
            name,
            b.last_commit_message or "",
            b.last_commit_author or "",
            upstream,
        )

    console.print()
    console.print(table)
    console.print()


@app.command(name="create")
def create_branch(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Branch name to create"),
    ] = None,
) -> None:
    """Create a new branch. Prompts interactively if no name is given."""
    service = _get_service()

    if not name:
        name = questionary.text(
            "Branch name:",
            validate=lambda val: len(val.strip()) > 0 or "Branch name cannot be empty.",
        ).ask()

        if not name:
            raise typer.Exit()

    base = None
    base_choice = questionary.select(
        "Create from:",
        choices=[
            questionary.Choice(
                title="Current branch",
                value=None,
                description=f"({service.get_current_branch()})",
            ),
            questionary.Choice(
                title="Another branch",
                value="other",
            ),
        ],
    ).ask()

    if base_choice == "other":
        branches = service.get_local_branch_names()
        base = questionary.select(
            "Select base branch:",
            choices=branches,
        ).ask()

        if not base:
            raise typer.Exit()

    try:
        service.create_branch(name, base=base)
    except BranchError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    TerminalUI.print_success(f"Created branch '{name}'")

    switch_now = questionary.confirm(
        "Switch to it now?",
        default=True,
    ).ask()

    if switch_now:
        try:
            service.switch_branch(name)
            TerminalUI.print_success(f"Switched to '{name}'")
        except BranchError as e:
            TerminalUI.print_error(str(e))
            raise typer.Exit(code=1)

    push_now = questionary.confirm(
        "Push to origin?",
        default=False,
    ).ask()

    if push_now:
        try:
            service.push_branch(name)
            TerminalUI.print_success(f"Pushed '{name}' to origin")
        except BranchError as e:
            TerminalUI.print_error(str(e))
            raise typer.Exit(code=1)


@app.command(name="switch")
def switch_branch(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Branch to switch to"),
    ] = None,
) -> None:
    """Switch to an existing branch. Prompts interactively if no name is given."""
    service = _get_service()

    if not name:
        branches = service.get_local_branch_names()
        current = service.get_current_branch()
        choices = []
        for b in branches:
            if b == current:
                choices.append(
                    questionary.Choice(
                        title=f"{b} (current)",
                        value=b,
                        disabled=True,
                    )
                )
            else:
                choices.append(questionary.Choice(title=b, value=b))

        if not choices:
            TerminalUI.print_error("No branches available to switch to.")
            raise typer.Exit(code=1)

        name = questionary.select(
            "Switch to branch:",
            choices=choices,
        ).ask()

        if not name:
            raise typer.Exit()

    try:
        service.switch_branch(name)
    except BranchError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    TerminalUI.print_success(f"Switched to branch '{name}'")


@app.command(name="merge")
def merge_branch(
    source: Annotated[
        Optional[str],
        typer.Argument(help="Source branch to merge from"),
    ] = None,
    target: Annotated[
        Optional[str],
        typer.Argument(help="Target branch to merge into (defaults to current)"),
    ] = None,
) -> None:
    """Merge a source branch into target (or current). Shows preview first."""
    service = _get_service()

    if not source:
        branches = [b for b in service.get_local_branch_names()
                    if b != service.get_current_branch()]
        if not branches:
            TerminalUI.print_error("No other branches to merge from.")
            raise typer.Exit(code=1)

        source = questionary.select(
            "Which branch do you want to merge from?",
            choices=branches,
        ).ask()

        if not source:
            raise typer.Exit()

    if not target:
        target = service.get_current_branch()

    console.print(
        f"\n[bold]Preview:[/] commits that will merge into [cyan]{target}[/] "
        f"from [cyan]{source}[/]:"
    )

    try:
        commits = service.get_merge_preview(source, target)
    except BranchError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    if commits:
        for commit in commits:
            console.print(f"  [dim]{commit}[/]")
    else:
        console.print("  [dim]Already up to date.[/]")

    if not questionary.confirm("Proceed with merge?", default=True).ask():
        console.print("[dim]Merge cancelled.[/]")
        raise typer.Exit()

    try:
        output = service.merge_branch(source, target)
    except BranchError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    TerminalUI.print_success(f"Merged '{source}' into '{target}'")

    push_now = questionary.confirm("Push now?", default=False).ask()

    if push_now:
        try:
            service.push_branch(target)
            TerminalUI.print_success(f"Pushed '{target}' to origin")
        except BranchError as e:
            TerminalUI.print_error(str(e))
            raise typer.Exit(code=1)

    delete_source = questionary.confirm(
        f"Delete source branch '{source}'?",
        default=False,
    ).ask()

    if delete_source:
        try:
            service.delete_branch(source)
            TerminalUI.print_success(f"Deleted '{source}'")
        except BranchError as e:
            TerminalUI.print_error(str(e))


@app.command(name="rename")
def rename_branch(
    old_name: Annotated[
        Optional[str],
        typer.Argument(help="Current branch name"),
    ] = None,
    new_name: Annotated[
        Optional[str],
        typer.Argument(help="New branch name"),
    ] = None,
) -> None:
    """Rename a branch. Prompts interactively if names are missing."""
    service = _get_service()

    if not old_name:
        branches = service.get_local_branch_names()
        old_name = questionary.select(
            "Which branch to rename?",
            choices=branches,
        ).ask()

        if not old_name:
            raise typer.Exit()

    if not new_name:
        new_name = questionary.text(
            "New name:",
            validate=lambda val: len(val.strip()) > 0 or "Name cannot be empty.",
        ).ask()

        if not new_name:
            raise typer.Exit()

    try:
        service.rename_branch(old_name, new_name)
    except BranchError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    TerminalUI.print_success(f"Renamed '{old_name}' to '{new_name}'")


@app.command(name="delete")
def delete_branch(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Branch to delete"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force delete even if unmerged"),
    ] = False,
) -> None:
    """Delete a branch. Protected branches (main, master, develop) cannot be deleted."""
    service = _get_service()

    if not name:
        branches = [
            b for b in service.get_local_branch_names()
            if b not in PROTECTED_BRANCHES
        ]
        if not branches:
            TerminalUI.print_error("No deletable branches (all are protected).")
            raise typer.Exit(code=1)

        name = questionary.select(
            "Which branch to delete?",
            choices=branches,
        ).ask()

        if not name:
            raise typer.Exit()

    try:
        service.delete_branch(name, force=force)
    except ProtectedBranchError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)
    except BranchError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    TerminalUI.print_success(f"Deleted branch '{name}'")


@app.command(name="push-delete")
def push_delete_branch(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Branch to push and delete"),
    ] = None,
) -> None:
    """Push a branch to origin, then delete it locally."""
    service = _get_service()

    if not name:
        branches = [
            b for b in service.get_local_branch_names()
            if b not in PROTECTED_BRANCHES
        ]
        if not branches:
            TerminalUI.print_error("No branches available to push-delete.")
            raise typer.Exit(code=1)

        name = questionary.select(
            "Which branch to push and delete?",
            choices=branches,
        ).ask()

        if not name:
            raise typer.Exit()

    try:
        service.push_and_delete(name)
    except (BranchError, ProtectedBranchError) as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    TerminalUI.print_success(f"Pushed '{name}' to origin and deleted locally")


@app.command(name="sync")
def sync_branches(
    remote: Annotated[
        str,
        typer.Argument(help="Remote name"),
    ] = "origin",
) -> None:
    """Prune remote-tracking branches that no longer exist on the remote."""
    service = _get_service()

    try:
        pruned = service.sync_branches(remote=remote)
    except BranchError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    if pruned:
        for name in pruned:
            console.print(f"  [dim]Pruned: {name}[/]")
        TerminalUI.print_success(f"Pruned {len(pruned)} branch(es)")
    else:
        TerminalUI.print_success("No stale branches to prune")


@app.command(name="info")
def branch_info(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Branch name"),
    ] = None,
) -> None:
    """Show detailed information about a branch."""
    service = _get_service()

    if not name:
        name = service.get_current_branch()

    try:
        info = service.get_branch_info(name)
    except BranchError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1)

    table = Table(title=f"Branch: {info.name}", title_style="bold gold1", border_style="gold1")
    table.add_column("Property", style="bold")
    table.add_column("Value")

    table.add_row("Name", info.name)
    table.add_row("Current", "Yes" if info.is_current else "No")
    table.add_row("Upstream", info.upstream or "(none)")
    table.add_row("Ahead", str(info.ahead))
    table.add_row("Behind", str(info.behind))
    if info.last_commit_hash:
        table.add_row("Last Commit", info.last_commit_hash)
    if info.last_commit_message:
        table.add_row("Message", info.last_commit_message)
    if info.last_commit_author:
        table.add_row("Author", info.last_commit_author)
    if info.last_commit_date:
        table.add_row("Date", info.last_commit_date)

    console.print()
    console.print(table)
    console.print()


def _get_service() -> BranchService:
    """Creates a BranchService for the current directory.

    Returns:
        A BranchService instance.
    """
    return BranchService(repo_path=Path.cwd())


def _interactive_menu() -> None:
    """Renders the main interactive branch manager menu."""
    service = _get_service()

    try:
        current = service.get_current_branch()
    except BranchError:
        current = "?"

    console.print(
        Text.assemble(
            ("\U0001f426 ", "bold gold1"),
            ("cheGi Branch Manager", "bold gold1"),
        )
    )
    console.print(
        Text.assemble(
            ("\U0001f331 ", "bold cyan"),
            (f"Current: {current}", "bold cyan"),
        )
    )
    console.print()

    choices = [
        questionary.Choice(
            title="List branches",
            value="list",
            description="Show all local branches",
        ),
        questionary.Choice(
            title="Create",
            value="create",
            description="Create a new branch",
        ),
        questionary.Choice(
            title="Switch",
            value="switch",
            description="Checkout an existing branch",
        ),
        questionary.Choice(
            title="Merge",
            value="merge",
            description="Merge one branch into another",
        ),
        questionary.Choice(
            title="Rename",
            value="rename",
            description="Rename a branch",
        ),
        questionary.Choice(
            title="Delete",
            value="delete",
            description="Delete a branch",
        ),
        questionary.Choice(
            title="Push & Delete",
            value="push-delete",
            description="Push to origin then delete locally",
        ),
        questionary.Choice(
            title="Sync",
            value="sync",
            description="Prune stale remote-tracking branches",
        ),
        questionary.Choice(
            title="Info",
            value="info",
            description="Show branch details",
        ),
        questionary.Choice(
            title="Cancel",
            value="cancel",
        ),
    ]

    action = questionary.select(
        "What would you like to do?",
        choices=choices,
    ).ask()

    if action is None or action == "cancel":
        console.print("[dim]OK, see you later![/dim]")
        raise typer.Exit()

    subcommand_map = {
        "list": list_branches,
        "create": create_branch,
        "switch": switch_branch,
        "merge": merge_branch,
        "rename": rename_branch,
        "delete": delete_branch,
        "push-delete": push_delete_branch,
        "sync": sync_branches,
        "info": branch_info,
    }

    cmd_func = subcommand_map.get(action)
    if cmd_func:
        cmd_func()
