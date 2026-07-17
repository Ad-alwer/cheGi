"""CLI command for cloning repositories with smart defaults."""

from pathlib import Path
from typing import List, Optional

import questionary
import typer
from rich.table import Table
from typing_extensions import Annotated

from chegi.services.clone import CloneService, parse_url
from chegi.services.clone.exceptions import (
    CloneError,
    CloneTargetExistsError,
    CloneUrlError,
)
from chegi.services.clone.models import CloneConfig, CloneSource
from chegi.services.environment import EnvManager
from chegi.ui import TerminalUI, console


def clone_cmd(
    url: Annotated[
        Optional[str],
        typer.Argument(
            help="Repository URL or user/repo shorthand",
        ),
    ] = None,
    path: Annotated[
        Optional[str],
        typer.Option(
            "--path",
            "-p",
            help="Target directory path",
        ),
    ] = None,
    here: Annotated[
        bool,
        typer.Option(
            "--here",
            help="Clone into current directory (no subfolder)",
        ),
    ] = False,
    own: Annotated[
        bool,
        typer.Option(
            "--own",
            help="Browse and clone from your GitHub repositories",
        ),
    ] = False,
    branch: Annotated[
        Optional[str],
        typer.Option(
            "--branch",
            "-b",
            help="Clone a specific branch",
        ),
    ] = None,
    depth: Annotated[
        Optional[int],
        typer.Option(
            "--depth",
            help="Shallow clone depth",
        ),
    ] = None,
    no_submodules: Annotated[
        bool,
        typer.Option(
            "--no-submodules",
            help="Skip submodule initialization",
        ),
    ] = False,
    no_gitignore: Annotated[
        bool,
        typer.Option(
            "--no-gitignore",
            help="Skip .gitignore generation",
        ),
    ] = False,
    no_chegi: Annotated[
        bool,
        typer.Option(
            "--no-chegi",
            help="Skip .chegi/ directory setup",
        ),
    ] = False,
) -> None:
    """Clone a repository with smart defaults.

    Usage:
      chegi clone user/repo
      chegi clone https://github.com/user/repo.git --path ./my-folder
      chegi clone --own
      chegi clone  (interactive)
    """
    # -- direct clone: URL provided --
    if url:
        _run_direct(
            url, path, here, branch, depth, no_submodules, no_gitignore, no_chegi
        )
        return

    # -- interactive --
    _run_interactive(own, branch, depth, no_submodules, no_gitignore, no_chegi)


def _run_direct(
    url: str,
    path: Optional[str],
    here: bool,
    branch: Optional[str],
    depth: Optional[int],
    no_submodules: bool,
    no_gitignore: bool,
    no_chegi: bool,
) -> None:
    """Runs clone with a direct URL argument."""
    try:
        full_url = parse_url(url)
    except CloneUrlError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1) from e

    repo_name = _extract_repo_name(full_url)
    target_dir = _resolve_target_dir(repo_name, path, here)

    config = CloneConfig(
        url=full_url,
        source=CloneSource.EXTERNAL_URL,
        target_dir=target_dir,
        repo_name=repo_name,
        branch=branch,
        depth=depth,
        submodules=not no_submodules,
        gitignore=not no_gitignore,
        chegi=not no_chegi,
    )

    _execute_clone(config)


def _run_interactive(
    own: bool,
    branch: Optional[str],
    depth: Optional[int],
    no_submodules: bool,
    no_gitignore: bool,
    no_chegi: bool,
) -> None:
    """Runs the interactive clone flow with questionary."""
    console.print("\n[bold gold1]🐆 cheGi Clone[/bold gold1]\n")

    if own:
        source = CloneSource.OWN_REPO
        url = _pick_own_repo()
        if not url:
            raise typer.Exit(0)
    else:
        choice = questionary.select(
            "Source:",
            choices=[
                "One of my GitHub repos",
                "External URL",
            ],
        ).ask()

        if choice is None:
            raise typer.Exit(0)

        if choice == "One of my GitHub repos":
            source = CloneSource.OWN_REPO
            url = _pick_own_repo()
            if not url:
                raise typer.Exit(0)
        else:
            source = CloneSource.EXTERNAL_URL
            raw = questionary.text("Repository URL:").ask()
            if not raw:
                raise typer.Exit(0)
            try:
                url = parse_url(raw)
            except CloneUrlError as e:
                TerminalUI.print_error(str(e))
                raise typer.Exit(code=1) from e

    repo_name = _extract_repo_name(url)

    loc_choice = questionary.select(
        "Where to clone?",
        choices=[
            "Here (current directory, no subfolder)",
            f"In a new folder ({repo_name})",
            "Specific path",
        ],
    ).ask()

    if loc_choice is None:
        raise typer.Exit(0)

    if loc_choice.startswith("Here"):
        target_dir = Path.cwd()
    elif loc_choice.startswith("In a new folder"):
        folder = questionary.text("Folder name:", default=repo_name).ask()
        if not folder:
            raise typer.Exit(0)
        target_dir = Path.cwd() / folder
    else:
        p = questionary.text("Full path:").ask()
        if not p:
            raise typer.Exit(0)
        target_dir = Path(p).resolve()

    # Interactive .gitignore technology selection
    if not no_gitignore:
        env_mgr = EnvManager()
        available = env_mgr.get_envs_with_gitignore()
        if available:
            selected = questionary.checkbox(
                "Select technologies for .gitignore:",
                choices=[
                    questionary.Choice(tech, checked=False)
                    for tech in sorted(available)
                ],
            ).ask()
            if selected is None:
                raise typer.Exit(0)
            technologies = selected
        else:
            technologies = []
    else:
        technologies = []

    config = CloneConfig(
        url=url,
        source=source,
        target_dir=target_dir,
        repo_name=repo_name,
        branch=branch,
        depth=depth,
        submodules=not no_submodules,
        gitignore=not no_gitignore,
        chegi=not no_chegi,
        technologies=technologies,
    )

    _execute_clone(config)


def _pick_own_repo() -> Optional[str]:
    """Lets user pick from their GitHub repos. Returns clone URL or None."""
    import questionary

    from chegi.services.auth import AuthService
    from chegi.services.github import GitHubRepoService

    cred = AuthService.get_credential_for_host("github.com")
    if not cred:
        TerminalUI.print_warning("No GitHub token found.")
        if typer.confirm(
            "Would you like to set one up with [bold]chegi auth login[/bold]?"
        ):
            from chegi.cli.commands.auth import login

            login()
            cred = AuthService.get_credential_for_host("github.com")
            if not cred:
                TerminalUI.print_error("Authentication failed.")
                raise typer.Exit(code=1)
        else:
            return None

    console.print("[dim]📡 Fetching your repositories...[/dim]")
    try:
        repos = GitHubRepoService.list_repos(cred.token)
    except Exception as e:
        TerminalUI.print_error(f"Failed to fetch repos: {e}")
        raise typer.Exit(code=1) from e

    if not repos:
        TerminalUI.print_warning("No repositories found.")
        return None

    choices = []
    for r in repos:
        label = f"{r.full_name:50s}  ★ {r.stargazers_count:3d}  {'Private' if r.private else 'Public'}"
        choices.append(questionary.Choice(title=label, value=r.html_url))

    selected = questionary.select(
        "Select a repository to clone:",
        choices=choices,
        use_indicator=True,
        use_shortcuts=True,
        qmark="🔍",
    ).ask()

    if not selected:
        return None

    return f"{selected}.git" if not selected.endswith(".git") else selected


def _extract_repo_name(url: str) -> str:
    """Extracts a friendly directory name from a Git URL.

    Args:
        url: The repository URL.

    Returns:
        The repository name.
    """
    name = url.rstrip("/").rsplit("/", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name


def _resolve_target_dir(repo_name: str, path: Optional[str], here: bool) -> Path:
    """Resolves the target directory from flags.

    Args:
        repo_name: The repository name.
        path: The --path option value.
        here: The --here flag.

    Returns:
        The resolved target Path.
    """
    if path:
        return Path(path).resolve()
    if here:
        return Path.cwd()
    return Path.cwd() / repo_name


def _confirm_overwrite(target_dir: Path) -> bool:
    """Asks user to confirm overwriting a non-empty target directory.

    Args:
        target_dir: The target path that exists and is not empty.

    Returns:
        True if the user confirms, False to abort.
    """
    TerminalUI.print_warning(
        f"Target directory already exists and is not empty: [bold]{target_dir}[/bold]"
    )
    return typer.confirm("Continue cloning into this directory?", default=False)


def _select_technologies(available: List[str]) -> List[str]:
    """Prompts user to select technologies for .gitignore generation.

    Args:
        available: List of available technology names.

    Returns:
        List of selected technology names.
    """
    selected = questionary.checkbox(
        "Select technologies for .gitignore:",
        choices=[questionary.Choice(tech, checked=False) for tech in sorted(available)],
    ).ask()
    return selected or []


def _execute_clone(config: CloneConfig) -> None:
    """Executes the clone and prints the result."""
    console.print()

    try:
        with console.status(
            f"[bold gold1]📡 Cloning [bold]{config.repo_name}[/bold]...[/bold gold1]",
            spinner="dots",
        ):
            service = CloneService(config)
            result = service.execute()
    except CloneTargetExistsError:
        if _confirm_overwrite(config.target_dir):
            try:
                with console.status(
                    f"[bold gold1]📡 Cloning [bold]{config.repo_name}[/bold]...[/bold gold1]",
                    spinner="dots",
                ):
                    service = CloneService(config)
                    result = service.execute()
            except CloneError as e:
                TerminalUI.print_error(str(e))
                raise typer.Exit(code=1) from e
        else:
            raise typer.Exit(0)
    except CloneError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1) from e

    # Build report table
    table = Table(
        title="[bold gold1]🐆 Clone Complete[/bold gold1]",
        title_justify="left",
        show_header=False,
        box=None,
        padding=(0, 1),
    )
    table.add_column("Key", style="dim", no_wrap=True)
    table.add_column("Value", style="bold")

    table.add_row("Path", str(result.target_dir))
    table.add_row("Branch", f"[cyan]{result.default_branch}[/cyan]")
    table.add_row("Origin", f"[cyan]{config.url}[/cyan]")

    if result.had_submodules:
        if result.submodules_inited:
            table.add_row(
                "Submodules",
                f"[dim]{len(result.submodules_inited)} initialized[/dim] "
                f"({', '.join(result.submodules_inited)})",
            )
        else:
            table.add_row("Submodules", "[dim]initialized[/dim]")

    if result.gitignore_created:
        techs = result.detected_techs or config.technologies
        label = ", ".join(t.capitalize() for t in techs) if techs else "Yes"
        table.add_row(".gitignore", label)
    elif result.gitignore_was_missing and not result.gitignore_created:
        table.add_row(".gitignore", "[dim]skipped (no technologies)[/dim]")

    if result.chegi_created:
        table.add_row(".chegi/", "[dim]Guard rules + config[/dim]")

    console.print()
    console.print(table)
    console.print()
    console.print(f"  [dim]🐆 cd {result.target_dir}[/dim]")
