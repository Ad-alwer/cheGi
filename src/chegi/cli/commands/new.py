"""CLI command for scaffolding new Git projects."""

import subprocess
from pathlib import Path
from typing import Optional

import questionary
import typer
from rich.table import Table
from typing_extensions import Annotated

from chegi.services.auth import AuthService
from chegi.services.environment import EnvManager
from chegi.services.github import (
    GhService,
    GitHubRepo,
    GitHubRepoService,
)
from chegi.services.new_project import (
    NewProjectConfig,
    NewProjectResult,
    NewProjectService,
)
from chegi.services.new_project.constants import (
    AVAILABLE_LICENSES,
    TEMPLATE_TECH_MAP,
)
from chegi.services.new_project.exceptions import (
    NewProjectError,
    ProjectAlreadyExistsError,
)
from chegi.ui import TerminalUI, console


def new_cmd(
    project_name: Annotated[
        Optional[str],
        typer.Argument(
            help="Name of the project (creates a new directory with this name)",
        ),
    ] = None,
    path: Annotated[
        str,
        typer.Option(
            "--path",
            "-p",
            help="Parent directory to create the project in",
        ),
    ] = ".",
    template: Annotated[
        Optional[str],
        typer.Option(
            "--template",
            "-t",
            help="Predefined project template (python, node, go, rust, ...)",
        ),
    ] = None,
    license: Annotated[
        Optional[str],
        typer.Option(
            "--license",
            "-l",
            help="License type (mit, apache, gpl3)",
        ),
    ] = None,
    no_readme: Annotated[
        bool,
        typer.Option(
            "--no-readme",
            help="Skip README.md generation",
        ),
    ] = False,
    no_gitignore: Annotated[
        bool,
        typer.Option(
            "--no-gitignore",
            help="Skip .gitignore generation",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Non-interactive mode — use defaults for all prompts",
        ),
    ] = False,
    github: Annotated[
        bool,
        typer.Option(
            "--github",
            "-g",
            help="Create and push to a GitHub repository",
        ),
    ] = False,
    private: Annotated[
        bool,
        typer.Option(
            "--private",
            help="Make the GitHub repository private",
        ),
    ] = False,
) -> None:
    """Create a new Git project from scratch.

    Scaffolds a complete project with Git initialization, .gitignore,
    .chegi/ directory, README.md, optional LICENSE, and an initial commit.

    Use [bold]chegi new <project-name>[/bold] to get started interactively.
    Use [bold]chegi new <project-name> --github[/bold] to also create a GitHub repo.
    """
    target_path = Path(path).resolve()
    yes_mode = yes or template is not None

    if project_name is None:
        project_name = questionary.text(
            "What is your project name?",
            validate=lambda val: (
                len(val.strip()) > 0 or "Project name cannot be empty."
            ),
        ).ask()

        if project_name is None:
            TerminalUI.print_error("Operation cancelled.")
            raise typer.Exit(1)

    config = NewProjectConfig(
        name=project_name,
        path=target_path,
        template=template,
        license_type=license,
        skip_readme=no_readme,
        skip_gitignore=no_gitignore,
        yes=yes_mode,
        github=github,
        private=private,
    )

    if not yes_mode:
        _run_interactive(config)
    else:
        _run_non_interactive(config)


def _run_interactive(config: NewProjectConfig) -> None:
    """Runs the interactive guided flow for project creation.

    Args:
        config: The base configuration to fill in interactively.
    """
    console.print("\n[bold gold1]🐆 Create a new cheGi project[/bold gold1]\n")
    console.print(
        f"[dim]Scaffolding: [bold]{config.name}[/bold] "
        f"at {config.path / config.name}[/dim]\n"
    )

    env_manager = EnvManager()
    available_envs = env_manager.get_envs_with_gitignore()
    if available_envs and not config.skip_gitignore:
        choices = [env.capitalize() for env in sorted(available_envs)]
        selected_caps = questionary.checkbox(
            "Select technologies for .gitignore (Space to select, Enter to confirm):",
            choices=choices,
        ).ask()

        if selected_caps is None:
            TerminalUI.print_error("Operation cancelled.")
            raise typer.Exit(1)

        config.technologies = [lang.lower() for lang in selected_caps]

    if not config.license_type:
        license_choices = list(AVAILABLE_LICENSES.values())
        license_choice = questionary.select(
            "Select a license (or skip with Esc):",
            choices=["None (skip)"] + license_choices,
        ).ask()

        if license_choice is None or license_choice == "None (skip)":
            config.license_type = None
        else:
            reverse_map = {v: k for k, v in AVAILABLE_LICENSES.items()}
            config.license_type = reverse_map.get(license_choice)

    tech_str = ", ".join(config.technologies) if config.technologies else "None"
    lic_str = (
        AVAILABLE_LICENSES.get(config.license_type, "None")
        if config.license_type
        else "None"
    )

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"  [gold1]•[/gold1] Project:  [bold]{config.name}[/bold]")
    console.print(
        f"  [gold1]•[/gold1] Location: [dim]{config.path / config.name}[/dim]"
    )
    console.print(f"  [gold1]•[/gold1] .gitignore: [cyan]{tech_str}[/cyan]")
    console.print(f"  [gold1]•[/gold1] License:   [cyan]{lic_str}[/cyan]")

    if config.github:
        console.print(
            f"  [gold1]•[/gold1] GitHub:    [cyan]Yes{' (private)' if config.private else ''}[/cyan]"
        )

    if not typer.confirm("\nCreate this project?", default=True):
        TerminalUI.print_error("Aborted.")
        raise typer.Exit(1)

    result = _create_project(config)

    if config.github and result:
        _handle_github_flow(config, result)


def _run_non_interactive(config: NewProjectConfig) -> None:
    """Runs project creation in non-interactive mode.

    Args:
        config: The project configuration (uses defaults for unset values).
    """
    if config.template and config.template.lower() in TEMPLATE_TECH_MAP:
        config.technologies = TEMPLATE_TECH_MAP[config.template.lower()]

    result = _create_project(config)

    if config.github and result:
        _handle_github_noninteractive(config, result)


def _create_project(config: NewProjectConfig) -> Optional[NewProjectResult]:
    """Creates the project with the given configuration.

    Args:
        config: The final project configuration.

    Returns:
        The NewProjectResult, or None on failure.
    """
    service = NewProjectService(config)

    try:
        result = service.create()
    except ProjectAlreadyExistsError as e:
        TerminalUI.print_error(str(e))
        raise typer.Exit(code=1) from e
    except NewProjectError as e:
        TerminalUI.print_error(f"Failed to create project: {e}")
        raise typer.Exit(code=1) from e

    console.print()
    TerminalUI.print_success(
        f"Project [bold cyan]{config.name}[/bold cyan] created at "
        f"[bold]{result.project_path}[/bold]"
    )
    console.print()

    for f in result.files_created:
        console.print(f"  [gold1]✓[/gold1] [bold]{f}[/bold]")

    if result.commit_hash:
        console.print(
            f"\n  [dim]Initial commit:[/dim] [cyan]{result.commit_hash}[/cyan]"
        )
        msg = config.commit_message or "Initial commit"
        console.print(f"  [dim]Message:[/dim] {msg}")

    return result


# ── GitHub flow ────────────────────────────────────────────


def _ensure_gh_and_token() -> Optional[str]:
    """Ensures gh CLI is installed and authenticated, and a cheGi auth token exists.

    Returns:
        GitHub token string, or None if setup fails.
    """
    if not GhService.check_installed():
        console.print()
        console.print("[yellow]⚠ GitHub CLI (gh) is not installed.[/yellow]")
        console.print("[dim]Install it from [bold]https://cli.github.com[/bold][/dim]")
        console.print()
        if not typer.confirm("Continue without gh?", default=False):
            return None

    if not GhService.ensure_authenticated():
        console.print("[yellow]⚠ GitHub CLI authentication failed.[/yellow]")
        return None

    creds = AuthService.get_credential_for_host("github.com")
    if not creds:
        console.print()
        console.print("[yellow]⚠ No cheGi GitHub token found.[/yellow]")
        console.print("[dim]Run [bold]chegi auth login[/bold] to set one up.[/dim]")
        console.print()
        if not typer.confirm("Continue without push?", default=False):
            return None
        return None

    return creds.token


def _pick_or_create_repo(token: str, config: NewProjectConfig) -> Optional[str]:
    """Interactive: user picks an existing repo or creates a new one.

    Args:
        token: GitHub API token.
        config: Project config (uses name/private).

    Returns:
        The remote URL, or None if cancelled.
    """
    console.print()
    has_repo = questionary.select(
        "Do you already have a GitHub repo for this project?",
        choices=["Yes, connect an existing one", "No, create a new one"],
    ).ask()

    if has_repo is None:
        return None

    has_existing = has_repo.startswith("Yes")

    if has_existing:
        return _pick_existing_repo(token)
    else:
        return _create_new_repo(token, config)


def _pick_existing_repo(token: str) -> Optional[str]:
    """Shows user's repos and lets them pick one.

    Args:
        token: GitHub API token.

    Returns:
        The remote URL, or None if cancelled.
    """
    console.print()
    console.print("[bold]Fetching your repositories...[/bold]")
    console.print()

    try:
        repos = GitHubRepoService.list_repos(token)
    except Exception:
        TerminalUI.print_error("Failed to fetch repositories.")
        return None

    if not repos:
        console.print("[yellow]No repositories found.[/yellow]")
        return None

    choices = [f"{r.full_name}  ({r.default_branch})" for r in repos]
    selected = questionary.select(
        "Select your repository:",
        choices=choices,
    ).ask()

    if selected is None:
        return None

    idx = choices.index(selected)
    repo = repos[idx]
    return _ssh_url(repo)


def _create_new_repo(token: str, config: NewProjectConfig) -> Optional[str]:
    """Creates a new repo on GitHub and returns its remote URL.

    Args:
        token: GitHub API token.
        config: Project config.

    Returns:
        The remote URL, or None if creation fails.
    """
    repo_name = config.repo_name or config.name
    description = questionary.text(
        "Repository description (optional):",
        default="",
    ).ask()

    if description is None:
        return None

    console.print()
    console.print(f"[dim]Creating repository [bold]{repo_name}[/bold]...[/dim]")

    try:
        repo = GitHubRepoService.create_repo(
            name=repo_name,
            token=token,
            private=config.private,
            description=description or f"Project {config.name}",
        )
    except Exception as e:
        TerminalUI.print_error(f"Failed to create repository: {e}")
        return None

    TerminalUI.print_success(f"Repository created: [cyan]{repo.html_url}[/cyan]")
    return _ssh_url(repo)


def _ssh_url(repo: GitHubRepo) -> str:
    """Converts a GitHubRepo to an SSH remote URL.

    Args:
        repo: The GitHub repo.

    Returns:
        SSH URL (git@github.com:user/repo.git).
    """
    return f"git@github.com:{repo.full_name}.git"


def _handle_github_flow(config: NewProjectConfig, result) -> None:
    """Runs the interactive GitHub flow after project creation.

    Args:
        config: Project config.
        result: The NewProjectResult from project creation.
    """
    console.print()

    # Step: prerequisites
    token = _ensure_gh_and_token()
    if not token:
        console.print("[dim]Skipping GitHub setup.[/dim]")
        console.print()
        return

    # Step: pick or create repo
    remote_url = _pick_or_create_repo(token, config)
    if not remote_url:
        console.print("[dim]Skipping GitHub setup.[/dim]")
        console.print()
        return

    # Step: brand in commit message
    console.print()
    want_brand = typer.confirm(
        "🐆 Mind if cheGi signs this commit with you?", default=True
    )

    if want_brand:
        commit_msg = "Initial commit 🐆"
    else:
        commit_msg = "Initial commit"

    # Step: commit with chosen message
    project_path = result.project_path
    try:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(project_path),
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", commit_msg],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        # If commit fails, it might be because there's nothing new to commit
        # (service already committed). Try amending instead.
        try:
            subprocess.run(
                ["git", "commit", "--amend", "-m", commit_msg],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            TerminalUI.print_warning("Could not update commit message.")

    # Step: detect default branch
    branch = _detect_branch(project_path)

    # Step: push
    console.print()
    console.print(f"[dim]Pushing to [bold]{remote_url}[/bold]...[/dim]")

    try:
        GitHubRepoService.push_project(
            project_path=project_path,
            remote_url=remote_url,
            branch=branch,
        )
    except Exception as e:
        TerminalUI.print_error(f"Failed to push: {e}")
        console.print()
        console.print(f"[dim]Remote URL: {remote_url}[/dim]")
        console.print(
            f"[dim]Push manually: [bold]git push -u origin {branch}[/bold][/dim]"
        )
        return

    # Update README with the repo URL if it exists
    _update_readme_with_repo_url(project_path, remote_url)

    # Step: report
    _print_github_report(config, remote_url, branch)


def _handle_github_noninteractive(config: NewProjectConfig, result) -> None:
    """Runs the GitHub flow in non-interactive mode.

    Args:
        config: Project config.
        result: The NewProjectResult from project creation.
    """
    creds = AuthService.get_credential_for_host("github.com")
    if not creds:
        TerminalUI.print_warning("GitHub setup skipped — no token found.")
        console.print("[dim]Run [bold]chegi auth login[/bold] first.[/dim]")
        return

    repo_name = config.repo_name or config.name
    try:
        repo = GitHubRepoService.create_repo(
            name=repo_name,
            token=creds.token,
            private=config.private,
            description=f"Project {config.name}",
        )
    except Exception as e:
        TerminalUI.print_error(f"Failed to create repository: {e}")
        return

    remote_url = _ssh_url(repo)
    project_path = result.project_path
    branch = _detect_branch(project_path)

    try:
        GitHubRepoService.push_project(
            project_path=project_path,
            remote_url=remote_url,
            branch=branch,
        )
    except Exception as e:
        TerminalUI.print_error(f"Failed to push: {e}")
        return

    _update_readme_with_repo_url(project_path, remote_url)
    _print_github_report(config, remote_url, branch)


def _detect_branch(project_path: Path) -> str:
    """Detects the default branch name of a git repo.

    Args:
        project_path: Path to the git repository.

    Returns:
        The branch name (defaults to main).
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        return branch if branch else "main"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "main"


def _update_readme_with_repo_url(project_path: Path, remote_url: str) -> None:
    """Updates README.md with the actual repo URL if a placeholder exists.

    Args:
        project_path: Path to the project.
        remote_url: The SSH remote URL.
    """
    readme_path = project_path / "README.md"
    if not readme_path.exists():
        return

    content = readme_path.read_text()
    placeholder = "git clone <your-repo-url>"
    if placeholder in content:
        content = content.replace(placeholder, f"git clone {remote_url}")
        readme_path.write_text(content)


def _print_github_report(
    config: NewProjectConfig, remote_url: str, branch: str
) -> None:
    """Prints the final summary report with GitHub details.

    Args:
        config: Project config.
        remote_url: The remote URL.
        branch: The branch name.
    """
    table = Table(
        title="🐆 Mission Complete!",
        title_style="bold gold1",
        border_style="gold1",
        header_style="bold",
    )
    table.add_column("Item", style="cyan")
    table.add_column("Detail", style="green")

    location = config.path / config.name
    github_https = remote_url.replace("git@github.com:", "https://github.com/").replace(
        ".git", ""
    )

    table.add_row("📍 Path", str(location))
    table.add_row("🔗 Remote", remote_url)
    table.add_row("🌐 Repo", github_https)
    table.add_row("🌿 Branch", branch)

    console.print()
    console.print(table)
    console.print()
    console.print("[dim]🐆 Type less, do more. — cheGi[/dim]")
    console.print()
