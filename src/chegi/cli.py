import json
import subprocess
from pathlib import Path
from typing import Annotated, Optional

import questionary
import typer
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.prompt import Confirm
from rich.table import Table

from chegi.config import SUPPORTED_PMS, ChegiConfig
from chegi.env_manager import EnvManager
from chegi.git_utils import (
    GitAnalyzer,
    check_git_environment,
    is_workspace_clean,
    perform_automated_rebase,
    pop_stash,
    pull_rebase,
    push_changes,
    stash_changes,
)
from chegi.installer import SystemInstaller
from chegi.scanner import find_git_repos
from chegi.security import SecurityGuard
from chegi.ui import TerminalUI

app = typer.Typer(help="cheGi - The ultimate Git companion. Type less, do more.")
config_app = typer.Typer(help="Manage cheGi configuration")
app.add_typer(config_app, name="config")


@app.callback()
def global_setup() -> None:
    """Global setup executed before any command.

    Validates the Git environment. If Git is missing or outdated, it prompts
    the user to automatically install or update it using the SystemInstaller.

    Raises:
        typer.Exit: If the user aborts the installation, if the installation
            fails, or upon successful installation requiring a terminal restart.
    """
    is_valid, message = check_git_environment()

    if not is_valid:
        ui = TerminalUI()
        ui.print_error(f"Environment Check Failed: {message}")

        install_now = typer.confirm(
            "Git is missing or outdated. Do you want cheGi to automatically install/update Git for you?"
        )

        if not install_now:
            ui.print_error(
                "Installation aborted. cheGi requires Git to function properly."
            )
            raise typer.Exit(code=1)

        ui.console.print("\n[bold cyan]Starting installation process...[/bold cyan]")
        success = SystemInstaller.install_package("git")

        if success:
            ui.console.print(
                "\n[bold green]Success! Git has been installed/updated.[/bold green]"
            )
            ui.console.print(
                "[bold magenta]IMPORTANT: Please restart your terminal (close and open it again) "
                "so the system can recognize the 'git' command.[/bold magenta]"
            )
            raise typer.Exit(code=0)
        else:
            ui.print_error(
                "Failed to install Git automatically. Please install it manually from https://git-scm.com/"
            )
            raise typer.Exit(code=1)


@app.command("scan")
def scan(
    path: str = typer.Argument(".", help="Base directory to scan"),
    max_depth: Optional[int] = typer.Option(
        None, "--max-depth", "-d", help="Override max depth from config"
    ),
    workers: int = typer.Option(
        5, "--workers", "-w", help="Number of concurrent workers"
    ),
    security: Annotated[
        bool,
        typer.Option("--security", "-s", help="Perform security scan on repositories"),
    ] = False,
    dirty: Annotated[
        bool,
        typer.Option("--dirty", help="Only show repositories with uncommitted changes"),
    ] = False,
    staged: Annotated[
        bool, typer.Option("--staged", help="Only show repositories with staged files")
    ] = False,
) -> None:
    """Scans a directory recursively for Git repositories and reports their status."""
    ui = TerminalUI()
    base_path = Path(path).resolve()

    config = ChegiConfig(base_path=str(base_path))
    config.load()

    if max_depth is not None:
        config.max_depth = max_depth

    ui.console.print(
        f"[dim]🔍 Scanning '{base_path}' (max depth: {config.max_depth})...[/dim]"
    )

    try:
        repo_paths = list(find_git_repos(str(base_path), config))
    except NotADirectoryError as e:
        ui.print_error(str(e))
        raise typer.Exit(code=1)

    if not repo_paths:
        ui.display_results_table([])
        raise typer.Exit()

    analyzer = GitAnalyzer(max_workers=workers)
    scanner_func = SecurityGuard.scan_repo if security else None
    statuses = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=ui.console,
        transient=True,
    ) as progress:
        task = progress.add_task(
            "[cyan]⚡ Analyzing repositories...", total=len(repo_paths)
        )

        for status in analyzer.analyze_concurrently(
            repo_paths, security_scanner=scanner_func
        ):
            statuses.append(status)
            progress.advance(task)

    if dirty:
        statuses = [s for s in statuses if s.is_dirty]

    if staged:
        statuses = [s for s in statuses if s.has_staged_files]

    if not statuses:
        ui.console.print(
            "\n[bold yellow]No repositories matched your filters.[/bold yellow]"
        )
        raise typer.Exit()

    ui.display_results_table(statuses)


@app.command("guard")
def guard(
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            "-f",
            help="Automatically unstage sensitive files without prompting",
        ),
    ] = False,
) -> None:
    """Checks staged files for sensitive data to prevent accidental commits."""
    ui = TerminalUI()
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

        raise typer.Exit(code=1)
    else:
        ui.console.print(
            "[bold green]✅ Security check passed. No sensitive files found in staging.[/bold green]"
        )


@app.command("gitignore")
def gitignore(
    path: str = typer.Option(
        ".", "--path", "-p", help="Directory to save the .gitignore file."
    ),
    auto_commit: bool = typer.Option(
        None, "--commit", "-c", help="Automatically commit the generated file."
    ),
) -> None:
    """Creates a .gitignore file interactively by combining environment templates.

    Prompts the user to select one or more environments, generates a deduplicated
    .gitignore file, and optionally commits it to the local git repository.
    """
    ui = TerminalUI()
    env_manager = EnvManager()

    ui.console.print("\n[bold blue] 🐆 Chegi .gitignore Generator[/bold blue]\n")

    envs_with_gitignore = env_manager.get_envs_with_gitignore()
    if not envs_with_gitignore:
        ui.print_error("No gitignore templates found in the environments database.")
        raise typer.Exit(1)

    choices = [env.capitalize() for env in sorted(envs_with_gitignore)]
    selected_langs_caps = questionary.checkbox(
        "Select technologies for the .gitignore file (Space to select, Enter to confirm):",
        choices=choices,
    ).ask()

    if not selected_langs_caps:
        ui.console.print(
            "[bold red]Operation cancelled or no technologies selected.[/bold red]"
        )
        raise typer.Exit(1)

    selected_langs = [lang.lower() for lang in selected_langs_caps]

    if env_manager.has_existing_gitignore(path):
        if not Confirm.ask(
            f"⚠️  [yellow].gitignore already exists in '{path}'. Overwrite?[/yellow]",
            default=False,
        ):
            ui.console.print("[bold red]Aborted.[/bold red]")
            raise typer.Exit()

    try:
        created_path = env_manager.generate_gitignore(selected_langs, path)
        ui.console.print(f"\n[bold green]✅ Created:[/bold green] {created_path}")
    except Exception as e:
        ui.print_error(f"Error generating file: {e}")
        raise typer.Exit(1)

    if env_manager.is_git_repo(path):
        should_commit = (
            auto_commit
            if auto_commit is not None
            else typer.confirm(
                "🚀 Do you want to commit this new .gitignore file?", default=True
            )
        )

        if should_commit:
            try:
                ui.console.print("[dim]Adding and committing .gitignore...[/dim]")
                commit_msg = env_manager.commit_gitignore(path)
                ui.console.print(
                    f"[bold green]✨ Committed with message:[/bold green] [cyan]{commit_msg}[/cyan]"
                )

            except Exception as e:
                ui.print_error(f"Failed to execute git commit: {e}")
        else:
            ui.console.print("[dim]Skipping commit.[/dim]")
    else:
        ui.console.print(
            "[bold yellow]⚠️  Skipped commit: Not a git repository.[/bold yellow]"
        )


@app.command("reword")
def reword(
    message: Optional[str] = typer.Argument(None, help="The new commit message"),
    last: Optional[int] = typer.Option(
        None, "--last", "-l", help="Number of recent commits to choose from", min=1
    ),
    start: Optional[int] = typer.Option(
        None, "--start", "-s", help="Start index for commit list (e.g., 15)", min=0
    ),
    end: Optional[int] = typer.Option(
        None, "--end", "-e", help="End index for commit list (e.g., 25)", min=1
    ),
) -> None:
    """Changes a commit message interactively or directly."""
    ui = TerminalUI()

    if last is not None and last > 20:
        ui.print_error("❌ Maximum limit for --last is 20.")
        ui.print_error(
            "💡 Please use --start/-s and --end/-e flags to navigate older commits."
        )
        raise typer.Exit(1)

    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        ui.print_error("❌ Not a git repository.")
        raise typer.Exit(1)

    target_hash = "HEAD"
    is_head = True

    show_menu = last is not None or start is not None or end is not None

    if show_menu:
        if start is not None and end is not None:
            if start >= end:
                ui.print_error("❌ Error: --start must be less than --end.")
                raise typer.Exit(1)
            skip = start
            limit = end - start
        elif start is not None:
            skip = start
            limit = 10
        elif end is not None:
            skip = max(0, end - 10)
            limit = end - skip
        else:
            skip = 0
            limit = last if last else 10

        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"--max-count={limit}",
                    f"--skip={skip}",
                    "--format=%h %s",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            commits = [line for line in result.stdout.strip().split("\n") if line]

            if not commits:
                ui.print_error("❌ No commits found in the specified range.")
                raise typer.Exit(1)

            choice = questionary.select(
                "Select the commit to reword:", choices=commits
            ).ask()

            if not choice:
                raise typer.Exit(0)

            target_hash = choice.split(" ")[0]

            head_hash = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
            ).stdout.strip()

            is_head = target_hash == head_hash

        except subprocess.CalledProcessError:
            ui.print_error("❌ Failed to fetch git history.")
            raise typer.Exit(1)

    try:
        old_msg_result = subprocess.run(
            ["git", "log", "--format=%B", "-n", "1", target_hash],
            check=True,
            capture_output=True,
            text=True,
        )
        old_message = old_msg_result.stdout.strip()
    except subprocess.CalledProcessError:
        ui.print_error("❌ Failed to fetch the commit message.")
        raise typer.Exit(1)

    if not message:
        message = questionary.text(
            "Enter new commit message:", default=old_message
        ).ask()

        if not message:
            ui.print_error("❌ Commit message cannot be empty.")
            raise typer.Exit(1)

    if message == old_message:
        ui.print_success("✅ Message is unchanged. Exiting without modifying history.")
        return

    if is_head:
        try:
            subprocess.run(["git", "commit", "--amend", "-m", message], check=True)
            ui.print_success("✅ Last commit message updated successfully!")
        except subprocess.CalledProcessError:
            ui.print_error("❌ Failed to amend the commit.")
            raise typer.Exit(1)
    else:
        try:
            perform_automated_rebase(target_hash, message)
            ui.print_success(f"✅ Commit {target_hash} updated successfully!")
        except Exception as e:
            ui.print_error(f"❌ Failed to rebase: {e}")
            raise typer.Exit(1)


@app.command()
def sync():
    """Synchronizes the local repository with the remote safely."""
    ui = TerminalUI()
    ui.print_info("Starting synchronization process...")

    needs_stash = False

    if not is_workspace_clean():
        ui.print_warning("You have uncommitted changes in your workspace.")

        confirm_stash = typer.confirm(
            "Do you want to automatically stash changes, sync, and restore them?",
            default=False,
        )
        if not confirm_stash:
            ui.print_error(
                "Sync aborted. Please commit or stash your changes manually."
            )
            raise typer.Exit(1)

        ui.print_warning(
            "Restoring changes (stash pop) after sync might result in merge conflicts."
        )
        confirm_again = typer.confirm(
            "Are you absolutely sure you want to proceed?", default=False
        )
        if not confirm_again:
            ui.print_error(
                "Sync aborted. Please commit or stash your changes manually."
            )
            raise typer.Exit(1)

        needs_stash = True

    if needs_stash:
        ui.print_info("Stashing uncommitted changes...")
        try:
            stash_changes()
        except RuntimeError as e:
            ui.print_error(str(e))
            raise typer.Exit(1)

    ui.print_info("Pulling latest changes from remote (rebase)...")
    try:
        pull_rebase()
    except RuntimeError as e:
        ui.print_error("❌ Conflict or error during pull --rebase.")
        ui.print_error(str(e))
        ui.print_warning(
            "💡 Please resolve conflicts manually, then run 'git rebase --continue'."
        )
        if needs_stash:
            ui.print_info("ℹ️ Your uncommitted changes are safely stored in git stash.")
        raise typer.Exit(1)

    ui.print_info("Pushing local commits to remote...")
    try:
        push_changes()
    except RuntimeError as e:
        ui.print_error("❌ Error during push.")
        ui.print_error(str(e))
        if needs_stash:
            ui.print_info("ℹ️ Your uncommitted changes are safely stored in git stash.")
        raise typer.Exit(1)

    if needs_stash:
        ui.print_info("Restoring stashed changes...")
        try:
            pop_stash()
        except RuntimeError as e:
            ui.print_warning(
                "⚠️ Conflict or error occurred while restoring stashed changes."
            )
            ui.print_error(str(e))
            ui.print_warning(
                "💡 Please resolve the conflicts manually in your code editor."
            )

    ui.print_success("Synchronization completed successfully! 🚀")


@config_app.command("list")
def config_list(
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Lists the current configuration settings, including saved mirrors.

    Args:
        path: Base directory for the configuration file.
    """
    config = ChegiConfig(base_path=path)
    config.load()
    ui = TerminalUI()

    ui.console.print("[bold]Current Configuration:[/bold]")
    ui.console.print(f"  Max Depth: {config.max_depth}")
    ui.console.print(f"  MCTS: {getattr(config, 'mcts', 10)}")
    ui.console.print(f"  Exclude Dirs: {', '.join(config.exclude_dirs)}")

    if hasattr(config, "mirrors") and config.mirrors:
        ui.console.print("  [bold]Saved Mirrors:[/bold]")
        for pm, urls in config.mirrors.items():
            if not urls:
                continue

            # Format nicely depending on the number of URLs
            if len(urls) == 1:
                ui.console.print(f"    - {pm}: [cyan]{urls[0]}[/cyan]")
            else:
                ui.console.print(f"    - {pm}:")
                for url in urls:
                    ui.console.print(f"      • [cyan]{url}[/cyan]")
    else:
        ui.console.print("  [bold]Saved Mirrors:[/bold] None")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key (e.g., max_depth, mcts)"),
    value: int = typer.Argument(..., help="New integer value"),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Updates a specific configuration setting."""
    config = ChegiConfig(base_path=path)
    config.load()
    ui = TerminalUI()

    try:
        config.update_setting(key, value)
        config.save()
        ui.console.print(f"[green]Successfully updated '{key}' to {value}.[/green]")
    except ValueError as e:
        ui.print_error(str(e))
        raise typer.Exit(code=1)


@config_app.command("exclude-add")
def config_exclude_add(
    folder: str = typer.Argument(..., help="Folder name to ignore"),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Adds a directory name to the scanning exclusion list."""
    config = ChegiConfig(base_path=path)
    config.load()
    config.add_exclude(folder)
    config.save()

    ui = TerminalUI()
    ui.console.print(f"[green]Added '{folder}' to the exclude list.[/green]")


@config_app.command("exclude-remove")
def config_exclude_remove(
    folder: str = typer.Argument(..., help="Folder name to stop ignoring"),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Removes a directory name from the scanning exclusion list."""
    config = ChegiConfig(base_path=path)
    config.load()
    ui = TerminalUI()

    try:
        config.remove_exclude(folder)
        config.save()
        ui.console.print(f"[green]Removed '{folder}' from the exclude list.[/green]")
    except ValueError as e:
        ui.print_error(str(e))
        raise typer.Exit(code=1)


@config_app.command("mirror-add")
def config_mirror_add(
    pm_name: str = typer.Argument(..., help="Package manager name (e.g., pip, npm)"),
    url: str = typer.Argument(..., help="The mirror URL to use"),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Adds or updates a single mirror URL for a package manager.

    Args:
        pm_name: The target package manager (e.g., 'pip', 'npm').
        url: The custom registry or mirror URL.
        path: Path to look for or create the configuration file.
    """
    config = ChegiConfig(base_path=path)
    config.load()
    ui = TerminalUI()

    try:
        config.set_mirror(pm_name, url)
        config.save()
        ui.console.print(
            f"[green]✔ Successfully added/updated mirror for '{pm_name.lower()}' -> '{url}'.[/green]"
        )
    except ValueError as e:
        ui.print_error(str(e))
        raise typer.Exit(code=1)


@config_app.command(name="mirror-remove")
def config_mirror_remove(
    pm_name: str = typer.Argument(
        ..., help="The package manager name (e.g., pip, npm)."
    ),
    url: Optional[str] = typer.Argument(
        None,
        help="The specific mirror URL to remove. If omitted, all mirrors for this PM are removed.",
    ),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Removes a mirror configuration.

    If a URL is provided, only that URL is removed.
    If omitted, all saved mirrors for the package manager are deleted.
    """
    ui = TerminalUI()
    config = ChegiConfig(base_path=path)
    config.load()

    pm_name = pm_name.lower()

    if not hasattr(config, "mirrors") or pm_name not in config.mirrors:
        ui.print_error(f"No mirror configuration found for '{pm_name}'.")
        raise typer.Exit(code=1)

    success = config.remove_mirror(pm_name, url)

    if success:
        config.save()
        if url:
            ui.print_success(f"Removed mirror URL '{url}' for '{pm_name}'.")
        else:
            ui.print_success(f"Removed all mirror configurations for '{pm_name}'.")
    else:
        if url:
            ui.print_error(f"URL '{url}' not found in saved mirrors for '{pm_name}'.")
        else:
            ui.print_error(f"Failed to remove mirror configuration for '{pm_name}'.")
        raise typer.Exit(code=1)


@config_app.command("mirror-set-all")
def config_mirror_set_all(
    json_data: str = typer.Argument(
        ...,
        help='JSON string representing the full mirror dictionary (e.g., \'{"npm": "url", "pip": "url"}\')',
    ),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Overwrites the entire mirrors configuration with the provided JSON data.

    You can pass an empty JSON object '{}' to clear all, or a dictionary
    with multiple key-value pairs to set everything at once.

    Args:
        json_data: A JSON formatted string containing package managers and URLs.
        path: Path to look for the configuration file.
    """
    config = ChegiConfig(base_path=path)
    config.load()
    ui = TerminalUI()

    try:
        new_mirrors = json.loads(json_data)

        if not isinstance(new_mirrors, dict):
            raise ValueError(
                "Data must be a valid JSON dictionary format (e.g., {...})."
            )

        for k, v in new_mirrors.items():
            if not isinstance(k, str) or not isinstance(v, (str, list)):
                raise ValueError(
                    f"All keys must be strings and values must be strings or lists. Invalid pair: '{k}': {v}"
                )

    except json.JSONDecodeError:
        ui.print_error(
            'Invalid JSON format! Please wrap the string properly (e.g. \'{"pip": "url"}\').'
        )
        raise typer.Exit(code=1)
    except ValueError as e:
        ui.print_error(f"Validation Error: {e}")
        raise typer.Exit(code=1)

    if not hasattr(config, "mirrors") or config.mirrors is None:
        config.mirrors = {}

    config.mirrors.clear()
    try:
        config.update_setting("mirrors", new_mirrors)
        config.save()
    except ValueError as e:
        ui.print_error(f"Validation Error: {e}")
        raise typer.Exit(code=1)

    ui.console.print(
        f"[green]✔ Mirrors configuration has been completely overwritten with {len(new_mirrors)} items.[/green]"
    )


@config_app.command("mirror-clear")
def config_mirror_clear(
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config"),
) -> None:
    """Completely removes all stored mirror configurations permanently.

    Args:
        path: Path to look for the configuration file.
    """
    config = ChegiConfig(base_path=path)
    config.load()
    ui = TerminalUI()

    if hasattr(config, "mirrors") and config.mirrors:
        config.mirrors = {}
        config.save()
        ui.console.print("[green]✔ All mirrors have been completely cleared.[/green]")
    else:
        ui.console.print("[yellow]⚠ No mirrors were configured to clear.[/yellow]")


@app.command(name="setup")
def setup_environment(
    environment: str = typer.Argument(
        ...,
        help="The programming language or toolset to setup (e.g., python, ruby, postman).",
    ),
    auto_yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Automatically answer yes to all installation prompts.",
    ),
) -> None:
    """Sets up the development environment or installs a standalone tool.

    Args:
        environment: Name of the environment or tool to install.
        auto_yes: Skip prompts and answer yes to all.
    """
    ui = TerminalUI()
    env_manager = EnvManager()

    # 1. Target Resolution: Find the target tool/env
    env_data = env_manager.find_setup_target(environment.lower())

    if not env_data:
        available_envs = env_manager.get_available_envs()
        ui.print_error(f"Target '{environment}' is not supported.")
        ui.print_info(f"Available environments: {', '.join(available_envs)}")
        raise typer.Exit(code=1)

    display_name = env_data.get("name", environment.capitalize())
    ui.print_info(
        f"Analyzing environment for: [bold yellow]{display_name}[/bold yellow]"
    )

    pkg_manager = SystemInstaller.get_os_package_manager()
    ui.console.print(
        f"Detected Package Manager: [bold cyan]{pkg_manager}[/bold cyan]\n"
    )

    # Setup status table
    table = Table(
        title=f"{display_name} Status", show_header=True, header_style="bold magenta"
    )
    table.add_column("Tool", style="cyan", no_wrap=True)
    table.add_column("Requires", style="dim")
    table.add_column("Level", style="blue")
    table.add_column("Status", justify="center")
    table.add_column("Version/Info", style="dim")

    # 2. Data Normalization: Make standalone tools compatible with the main loop
    tool_name = environment.lower()

    levels = env_data.get("levels", {})
    levels_info = env_data.get("levels_info", {})
    tools_data = env_data.get("tools", {})

    if not levels or not tools_data:
        levels = {"standalone": [tool_name]}
        levels_info = {"standalone": "Standalone App"}

        if (
            "tools" in env_data
            and isinstance(env_data["tools"], dict)
            and tool_name in env_data["tools"]
        ):
            tools_data = {tool_name: env_data["tools"][tool_name]}
        else:
            tools_data = {tool_name: env_data}

    tools_to_install = []
    installed_tools = set()

    # 3. Check installed tools
    with ui.console.status(
        "[bold green]Checking installed tools...[/bold green]", spinner="dots"
    ):
        for level_id, tool_names in levels.items():
            level_name = levels_info.get(level_id, f"Level {level_id}")

            for t_name in tool_names:
                tool_info = tools_data.get(t_name)
                if not tool_info:
                    continue

                check_cmd = (
                    tool_info.get("check_command")
                    or tool_info.get("check_cmd")
                    or f"{t_name} --version"
                )
                requires_list = tool_info.get("requires", [])
                requires_str = ", ".join(requires_list) if requires_list else "-"

                is_gui_app = bool(tool_info.get("is_gui", False))
                is_installed, info = SystemInstaller.is_tool_installed(
                    check_cmd, is_gui=is_gui_app
                )

                if is_installed:
                    installed_tools.add(t_name)
                    status_str = "[bold green]✔ Installed[/bold green]"
                    if is_gui_app and not info:
                        info = "GUI Tool"
                else:
                    status_str = "[bold red]✖ Missing[/bold red]"

                    cmd_to_run = SystemInstaller.get_install_command(
                        tool_info, pkg_manager
                    )

                    if cmd_to_run:
                        tools_to_install.append(
                            {
                                "name": t_name,
                                "level": level_name,
                                "cmd": cmd_to_run,
                                "requires": requires_list,
                            }
                        )
                    else:
                        status_str = "[bold yellow]⚠ Manual[/bold yellow]"

                table.add_row(t_name, requires_str, level_name, status_str, info)

    ui.console.print(table)
    ui.console.print("\n")

    if not tools_to_install:
        ui.print_success(
            f"All critical tools for {display_name} are already installed! 🎉"
        )
        raise typer.Exit()

    # 4. Dependency Sorting: Install required tools first
    sorted_tools_to_install = []
    remaining_tools = tools_to_install.copy()

    while remaining_tools:
        progress = False
        for tool in remaining_tools:
            pending_deps = [
                dep
                for dep in tool.get("requires", [])
                if any(t["name"] == dep for t in remaining_tools)
            ]

            if not pending_deps:
                sorted_tools_to_install.append(tool)
                remaining_tools.remove(tool)
                progress = True
                break

        if not progress:  # Break on circular dependency
            sorted_tools_to_install.extend(remaining_tools)
            break

    tools_to_install = sorted_tools_to_install

    ui.print_info(
        f"Found {len(tools_to_install)} missing tools that can be installed automatically."
    )

    # Check if we are dealing with exactly one standalone tool
    is_single_standalone_tool = (
        len(tools_to_install) == 1 and tools_to_install[0]["level"] == "Standalone App"
    )

    # 5. User Prompts
    if not auto_yes:
        if is_single_standalone_tool:
            single_tool_name = tools_to_install[0]["name"]
            if not typer.confirm(f"Do you want to install '{single_tool_name}'?"):
                ui.print_info("Setup aborted by user. No changes were made.")
                raise typer.Exit()
        else:
            choices = [
                questionary.Choice(
                    title=f"{t['name']} ({t['level']})"
                    + (
                        f" [Requires: {', '.join(t['requires'])}]"
                        if t["requires"]
                        else ""
                    ),
                    value=t,
                    checked=True,
                )
                for t in tools_to_install
            ]

            selected_tools = questionary.checkbox(
                "Select the tools you want to install (Space to toggle, Enter to confirm):",
                choices=choices,
            ).ask()

            if not selected_tools:
                ui.print_info("Setup aborted by user or no tools selected.")
                raise typer.Exit()

            tools_to_install = selected_tools

    # 6. Mirror Configuration: Setup proxy/mirror if needed
    session_mirrors = {}
    config = ChegiConfig()
    config.load()

    active_pms_in_tools = {tool["cmd"].split()[0].lower() for tool in tools_to_install}

    if environment.lower() in env_manager.get_available_envs():
        required_pms = env_manager.get_required_package_managers([environment.lower()])
    else:
        required_pms = active_pms_in_tools.copy()

    pms_to_ask = required_pms.intersection(SUPPORTED_PMS).intersection(
        active_pms_in_tools
    )

    if pms_to_ask:
        ui.console.print(
            "\n[bold cyan]🪞 Mirror / Registry Configuration (Optional)[/bold cyan]"
        )
        ui.console.print("[dim]Useful if you are behind a restricted network.[/dim]")

        for pm in list(pms_to_ask):
            saved_mirrors = (
                config.get_mirror(pm) if hasattr(config, "get_mirror") else None
            )

            if saved_mirrors:
                mirror_list = (
                    saved_mirrors
                    if isinstance(saved_mirrors, list)
                    else [saved_mirrors]
                )

                if auto_yes:
                    primary_mirror = mirror_list[0]
                    session_mirrors[pm] = primary_mirror
                    ui.console.print(
                        f"[dim]Auto-using primary mirror for {pm}: {primary_mirror}[/dim]"
                    )
                else:
                    choices = [
                        questionary.Choice(f"✅ Use: {url}", value=url)
                        for url in mirror_list
                    ]
                    choices.extend(
                        [
                            questionary.Choice(
                                "✏️  Use a different mirror", value="new"
                            ),
                            questionary.Choice("❌ Do NOT use a mirror", value="none"),
                        ]
                    )

                    choice = questionary.select(
                        f"Found configured mirror(s) for '{pm}'. Please select one:",
                        choices=choices,
                    ).ask()

                    if choice is None:
                        ui.console.print("\n[bold red]❌ Cancelled by user.[/bold red]")
                        raise typer.Exit(code=1)
                    elif choice == "none":
                        ui.console.print(
                            f"[yellow]ℹ Skipping mirror for {pm}.[/yellow]"
                        )
                    elif choice == "new":
                        new_url = questionary.text(
                            f"Enter the new mirror URL for {pm}:",
                            default=mirror_list[0],
                        ).ask()

                        if new_url is None:
                            ui.console.print(
                                "\n[bold red]❌ Cancelled by user.[/bold red]"
                            )
                            raise typer.Exit(code=1)

                        if new_url and new_url.strip():
                            new_url = new_url.strip()
                            session_mirrors[pm] = new_url

                            if new_url not in mirror_list:
                                if typer.confirm(
                                    f"Add this URL to the permanent config for {pm}?",
                                    default=False,
                                ):
                                    config.set_mirror(pm, new_url)
                                    config.save()
                                    ui.console.print(
                                        f"[green]✔ Added mirror permanently for {pm}[/green]"
                                    )
                    else:
                        session_mirrors[pm] = choice

            else:
                if not auto_yes:
                    use_mirror = typer.confirm(
                        f"Do you want to use a mirror/custom registry for '{pm}'?",
                        default=False,
                    )
                    if use_mirror:
                        mirror_url = questionary.text(
                            f"Enter mirror URL for {pm}:"
                        ).ask()

                        if mirror_url is None:
                            ui.console.print(
                                "\n[bold red]❌ Cancelled by user.[/bold red]"
                            )
                            raise typer.Exit(code=1)

                        if mirror_url and mirror_url.strip():
                            session_mirrors[pm] = mirror_url.strip()

                            if typer.confirm(
                                "Save this mirror permanently in config?", default=True
                            ):
                                config.set_mirror(pm, session_mirrors[pm])
                                config.save()
                                ui.console.print(
                                    f"[green]✔ Saved mirror permanently for {pm}[/green]"
                                )

    # 7. Execution Loop: Run install commands
    success_count = 0
    skipped_count = 0

    try:
        for tool in tools_to_install:
            missing_deps = [
                dep for dep in tool.get("requires", []) if dep not in installed_tools
            ]

            if missing_deps:
                ui.print_warning(
                    f"⏭️  Skipping {tool['name']}: Missing prerequisites ({', '.join(missing_deps)})"
                )
                skipped_count += 1
                continue

            ui.console.print(
                f"\n[bold blue]▶ Installing {tool['name']} ({tool['level']})...[/bold blue]"
            )

            pm_name = tool["cmd"].split()[0].lower()
            mirror_url = session_mirrors.get(pm_name)

            success = SystemInstaller.run_custom_command(
                tool["cmd"],
                pm_name=pm_name if mirror_url else None,
                mirror_url=mirror_url,
            )

            if success:
                # Print individual success message only for multi-tool setups
                if len(tools_to_install) > 1:
                    ui.console.print(
                        f"[bold green]✅ {tool['name']} installed successfully.[/bold green]"
                    )
                installed_tools.add(tool["name"])
                success_count += 1
            else:
                ui.print_error(
                    f"❌ Failed to install {tool['name']}. Check permissions or install manually."
                )

    except KeyboardInterrupt:
        ui.console.print(
            "\n[bold red]❌ Installation interrupted by user (Ctrl+C).[/bold red]"
        )
        raise typer.Exit(code=1)

    # Final Output
    ui.console.print("\n")
    if success_count == len(tools_to_install) and success_count > 0:
        if len(tools_to_install) == 1:
            # Single tool installation success message
            single_installed_tool = tools_to_install[0]["name"]
            ui.print_success(f"✨ {single_installed_tool} installed successfully! ✨")
        else:
            # Multi-tool environment success message
            ui.print_success(f"✨ Setup for {display_name} completed successfully! ✨")
    else:
        ui.print_info(
            f"Setup finished. Installed: {success_count}, Skipped: {skipped_count}, Failed/Canceled: {len(tools_to_install) - success_count - skipped_count}."
        )


def main() -> None:
    """Main entry point for the cheGi Typer CLI application."""
    app()
