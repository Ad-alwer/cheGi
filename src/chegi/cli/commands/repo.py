"""CLI commands for listing and managing GitHub repositories."""

import webbrowser
from datetime import datetime, timezone
from typing import List, Optional

import questionary
import typer
from rich.table import Table
from rich.text import Text
from typing_extensions import Annotated

from chegi.services.auth import AuthService
from chegi.services.github import GitHubRepoService
from chegi.services.github.cache import RepoCache
from chegi.services.github.constants import DEFAULT_LANG_COLOR, LANG_COLORS
from chegi.services.github.models import GitHubRepo
from chegi.ui import TerminalUI, console

app = typer.Typer(help="List and manage your GitHub repositories.")


def _get_token() -> str:
    """Retrieves the GitHub token from stored credentials.

    Returns:
        The GitHub token.

    Raises:
        typer.Exit: If no GitHub credential is found.
    """
    cred = AuthService.get_credential_for_host("github.com")
    if not cred:
        TerminalUI.print_error(
            "No GitHub token found. Run [bold]chegi auth login[/bold] first."
        )
        raise typer.Exit(code=1)
    return cred.token


def _fetch_repos(token: str, force_refresh: bool = False) -> List[GitHubRepo]:
    """Fetches repos from cache or GitHub API.

    Args:
        token: GitHub API token.
        force_refresh: If True, skip cache and fetch from API.

    Returns:
        List of GitHubRepo objects.
    """
    if not force_refresh and RepoCache.is_fresh():
        cached = RepoCache.read()
        if cached is not None:
            return cached

    console.print()
    console.print("[dim]📡 Fetching your repositories...[/dim]")

    repos = GitHubRepoService.list_repos(token)

    if repos:
        RepoCache.write(repos)

    return repos


def _lang_color(language: Optional[str]) -> str:
    """Returns the Rich color for a programming language.

    Args:
        language: Programming language name.

    Returns:
        Rich color string.
    """
    if not language:
        return DEFAULT_LANG_COLOR
    return LANG_COLORS.get(language, DEFAULT_LANG_COLOR)


def _relative_time(iso_str: str) -> str:
    """Converts an ISO timestamp to a relative time string.

    Args:
        iso_str: ISO 8601 timestamp string.

    Returns:
        Relative time string (e.g. '2h ago', '3d ago').
    """
    if not iso_str:
        return ""
    try:
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(iso_str)
        now = datetime.now(timezone.utc).replace(tzinfo=dt.tzinfo)
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        if seconds < 2592000:
            return f"{seconds // 86400}d ago"
        if seconds < 31536000:
            return f"{seconds // 2592000}mo ago"
        return f"{seconds // 31536000}y ago"
    except (ValueError, TypeError):
        return iso_str


def _visibility_icon(repo: GitHubRepo) -> str:
    """Returns the visibility icon for a repo.

    Args:
        repo: The GitHubRepo.

    Returns:
        Icon string.
    """
    return "🔒" if repo.private else "🔓"


def _build_repos_table(repos: List[GitHubRepo]) -> Table:
    """Builds a Rich table from a list of GitHub repos.

    Args:
        repos: List of GitHubRepo objects.

    Returns:
        A Rich Table.
    """
    table = Table(
        title=f"🐆  Your Repositories ({len(repos)})",
        title_style="bold gold1",
        border_style="gold1",
        header_style="bold",
    )
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Visibility", width=6)
    table.add_column("★", style="yellow", justify="right", width=2)
    table.add_column("Language")
    table.add_column("Updated", style="dim")
    table.add_column("Actions", style="dim")

    for repo in repos[:50]:  # limit display to 50 in table mode
        lang = Text(repo.language or "-", style=_lang_color(repo.language))
        table.add_row(
            repo.name,
            _visibility_icon(repo),
            str(repo.stargazers_count) if repo.stargazers_count else "·",
            lang,
            _relative_time(repo.updated_at),
            "[o]pen [c]opy",
        )

    if len(repos) > 50:
        table.add_row(
            "...",
            "",
            "",
            Text(f"and {len(repos) - 50} more", style="dim"),
            "",
            "",
        )

    return table


def _prompt_repo_selection(repos: List[GitHubRepo]) -> Optional[GitHubRepo]:
    """Prompts the user to select a repo via fuzzy search.

    Args:
        repos: List of GitHubRepo objects.

    Returns:
        The selected GitHubRepo, or None if cancelled.
    """
    choices = []
    for r in repos:
        vis = "Public" if not r.private else "Private"
        label = f"{r.full_name:40s}  ★ {r.stargazers_count:3d}  {vis:8s}  {r.language or '-':10s}  {_relative_time(r.updated_at)}"
        choices.append(questionary.Choice(title=label, value=r))

    selected = questionary.select(
        "Select a repository (type to filter):",
        choices=choices,
        use_indicator=True,
        use_shortcuts=True,
        qmark="🔍",
    ).ask()

    return selected


def _handle_repo_action(repo: GitHubRepo) -> None:
    """Shows actions for a selected repo and handles user choice.

    Args:
        repo: The selected GitHubRepo.
    """
    while True:
        console.print()
        console.print(f"[bold cyan]{repo.full_name}[/bold cyan]")
        console.print(f"  [dim]{repo.html_url}[/dim]")
        console.print()

        action = questionary.select(
            "What now?",
            choices=[
                "🌐  Open in browser",
                "📋  Copy SSH URL",
                "📋  Copy HTTPS URL",
                "◀  Back to list",
                "❌  Exit",
            ],
        ).ask()

        if action is None or action == "❌  Exit":
            raise typer.Exit(0)

        if action == "🌐  Open in browser":
            webbrowser.open(repo.html_url)
            console.print(f"  [dim]Opened: {repo.html_url}[/dim]")
            console.print()

        elif action == "📋  Copy SSH URL":
            ssh_url = f"git@github.com:{repo.full_name}.git"
            _try_copy(ssh_url)
            console.print(f"  [green]✔ Copied:[/green] {ssh_url}")
            console.print()

        elif action == "📋  Copy HTTPS URL":
            https_url = f"https://github.com/{repo.full_name}.git"
            _try_copy(https_url)
            console.print(f"  [green]✔ Copied:[/green] {https_url}")
            console.print()

        elif action == "◀  Back to list":
            return


def _try_copy(text: str) -> None:
    """Attempts to copy text to clipboard.

    Falls back to printing the text if clipboard is not available.

    Args:
        text: The text to copy.
    """
    try:
        import pyperclip

        pyperclip.copy(text)
        return
    except (ImportError, Exception):
        console.print("  [dim]Clipboard not available. Text below:[/dim]")
        console.print(f"  {text}")


# ── Filter helpers ─────────────────────────────────────────


def _apply_filters(
    repos: List[GitHubRepo],
    public_only: bool = False,
    private_only: bool = False,
    owner_only: bool = False,
    limit: Optional[int] = None,
    sort_by: str = "updated",
) -> List[GitHubRepo]:
    """Applies filters to a list of repos.

    Args:
        repos: Full list of repos.
        public_only: Only show public repos.
        private_only: Only show private repos.
        owner_only: Only show non-fork repos.
        limit: Max number of repos to return.
        sort_by: Sort key (stars, updated).

    Returns:
        Filtered and sorted list.
    """
    result = repos

    if public_only:
        result = [r for r in result if not r.private]
    if private_only:
        result = [r for r in result if r.private]
    if owner_only:
        result = [r for r in result if not r.fork]

    if sort_by == "stars":
        result = sorted(result, key=lambda r: r.stargazers_count, reverse=True)
    else:
        result = sorted(result, key=lambda r: r.updated_at or "", reverse=True)

    if limit and limit < len(result):
        result = result[:limit]

    return result


# ── list command ───────────────────────────────────────────


@app.command(name="list")
def list_repos(
    public_only: Annotated[
        bool,
        typer.Option("--public", help="Show only public repositories"),
    ] = False,
    private_only: Annotated[
        bool,
        typer.Option("--private", help="Show only private repositories"),
    ] = False,
    owner_only: Annotated[
        bool,
        typer.Option("--owner", help="Show only non-fork repositories"),
    ] = False,
    limit: Annotated[
        Optional[int],
        typer.Option("--limit", "-n", help="Limit number of repositories"),
    ] = None,
    sort_by: Annotated[
        str,
        typer.Option(
            "--sort",
            help="Sort by (stars, updated)",
        ),
    ] = "updated",
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format (table, json, interactive)",
        ),
    ] = "interactive",
    refresh: Annotated[
        bool,
        typer.Option(
            "--refresh",
            help="Force refresh from GitHub API (skip cache)",
        ),
    ] = False,
) -> None:
    """List your GitHub repositories.

    By default runs in interactive mode with fuzzy search selection.
    Use --format table or --format json for non-interactive output.
    """
    token = _get_token()
    repos = _fetch_repos(token, force_refresh=refresh)

    if not repos:
        console.print("[yellow]No repositories found.[/yellow]")
        return

    repos = _apply_filters(
        repos,
        public_only=public_only,
        private_only=private_only,
        owner_only=owner_only,
        limit=limit,
        sort_by=sort_by,
    )

    if not repos:
        console.print("[yellow]No repositories match the filter.[/yellow]")
        return

    if output_format == "json":
        import json as json_mod

        data = [
            {
                "name": r.name,
                "full_name": r.full_name,
                "html_url": r.html_url,
                "private": r.private,
                "language": r.language,
                "stars": r.stargazers_count,
                "forks": r.forks_count,
                "description": r.description,
                "updated_at": r.updated_at,
                "default_branch": r.default_branch,
            }
            for r in repos
        ]
        console.print(json_mod.dumps(data, indent=2))
        return

    if output_format == "table":
        table = _build_repos_table(repos)
        console.print(table)
        return

    # Interactive mode
    console.print()
    console.print(
        f"[bold gold1]🐆  Your Repositories[/bold gold1]  "
        f"[dim]({len(repos)} repos)[/dim]"
    )
    console.print("[dim]Type to filter, Enter to select, Esc to exit[/dim]")

    while True:
        selected = _prompt_repo_selection(repos)
        if selected is None:
            console.print()
            TerminalUI.print_info("See you next time! 🐆")
            raise typer.Exit(0)

        _handle_repo_action(selected)
