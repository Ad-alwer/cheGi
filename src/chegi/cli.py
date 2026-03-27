import typer
import subprocess
import questionary
from pathlib import Path
from typing import Optional, Annotated
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm
from rich.table import Table


from chegi.config import ChegiConfig
from chegi.scanner import find_git_repos
from chegi.git_utils import GitAnalyzer, check_git_environment,perform_automated_rebase,is_workspace_clean, stash_changes,pop_stash,pull_rebase,push_changes
from chegi.ui import TerminalUI
from chegi.installer import SystemInstaller
from chegi.security import SecurityGuard
from chegi.gitignore_templates import TEMPLATES
from chegi.env_manager import EnvManager

app = typer.Typer(help="cheGi - Fast & Concurrent Git Repository Manager")
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
            ui.print_error("Installation aborted. cheGi requires Git to function properly.")
            raise typer.Exit(code=1)
            
        ui.console.print("\n[bold cyan]Starting installation process...[/bold cyan]")
        success = SystemInstaller.install_package("git")
        
        if success:
            ui.console.print("\n[bold green]Success! Git has been installed/updated.[/bold green]")
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
    max_depth: Optional[int] = typer.Option(None, "--max-depth", "-d", help="Override max depth from config"),
    workers: int = typer.Option(5, "--workers", "-w", help="Number of concurrent workers"),
    security: Annotated[bool, typer.Option("--security", "-s", help="Perform security scan on repositories")] = False,
    dirty: Annotated[bool, typer.Option("--dirty", help="Only show repositories with uncommitted changes")] = False,
    staged: Annotated[bool, typer.Option("--staged", help="Only show repositories with staged files")] = False,
) -> None:
    """Scans a directory recursively for Git repositories and reports their status.

    Args:
        path (str): The root directory where the scanning process begins.
        max_depth (Optional[int]): Overrides the configuration's maximum folder depth.
        workers (int): Number of concurrent threads for analyzing repositories.
        security (bool): If True, performs a security scan on staged files for each repository.
        dirty (bool): If True, filters the output to only show repositories with uncommitted changes.
        staged (bool): If True, filters the output to only show repositories with staged files.

    Raises:
        typer.Exit: If the specified path is not a valid directory, if no 
            repositories are found, or if no repositories match the applied filters.
    """
    ui = TerminalUI()
    base_path = Path(path).resolve()
    
    config = ChegiConfig(base_path=str(base_path))
    config.load()
    
    if max_depth is not None:
        config.max_depth = max_depth
        
    ui.console.print(f"[dim]🔍 Scanning '{base_path}' (max depth: {config.max_depth})...[/dim]")
    
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
        transient=True
    ) as progress:
        task = progress.add_task("[cyan]⚡ Analyzing repositories...", total=len(repo_paths))
        
        for status in analyzer.analyze_concurrently(repo_paths, security_scanner=scanner_func):
            statuses.append(status)
            progress.advance(task)
    
    if dirty:
        statuses = [s for s in statuses if s.is_dirty]
    
    if staged:
        statuses = [s for s in statuses if s.has_staged_files]

    if not statuses:
        ui.console.print("\n[bold yellow]No repositories matched your filters.[/bold yellow]")
        raise typer.Exit()

    ui.display_results_table(statuses)


@app.command("guard")
def guard(
    fix: Annotated[bool, typer.Option("--fix", "-f", help="Automatically unstage sensitive files without prompting")] = False
) -> None:
    """Checks staged files for sensitive data to prevent accidental commits.

    This command runs a standalone security check. It fetches staged files
    and checks them against predefined sensitive patterns (like .env or private keys).
    If sensitive files are found, it displays a warning, offers to unstage them,
    and exits with a non-zero status code.

    Raises:
        typer.Exit: Exits with code 1 if sensitive files are detected.
    """
    ui = TerminalUI()
    ui.console.print("[dim]🔒 Running Security Guard...[/dim]")
    
    staged_files = SecurityGuard.get_staged_files()
    if not staged_files:
        ui.console.print("[bold blue]No staged files found. Nothing to check.[/bold blue]")
        raise typer.Exit()
        
    sensitive_files = SecurityGuard.find_sensitive_files(staged_files)
    
    if sensitive_files:
        ui.console.print("\n[bold red]⚠️  WARNING: Sensitive files detected in staging area![/bold red]")
        for f in sensitive_files:
            ui.console.print(f"  [red]- {f}[/red]")
            
        files_str = " ".join(sensitive_files)
        exact_command = f"git rm --cached {files_str}"
        ui.console.print(f"\n[bold yellow]To fix this manually, run:[/bold yellow] [cyan]{exact_command}[/cyan]\n")
        
        if fix:
            success = SecurityGuard.unstage_files(sensitive_files)
            if success:
                ui.console.print("\n[bold green]✅ Files successfully unstaged automatically (via --fix). You can now commit safely.[/bold green]")
            else:
                ui.print_error("\nFailed to unstage files automatically. Please run the command manually.")
        else:
            should_unstage = typer.confirm("Do you want cheGi to automatically unstage these files for you?")
            
            if should_unstage:
                success = SecurityGuard.unstage_files(sensitive_files)
                if success:
                    ui.console.print("\n[bold green]✅ Files successfully unstaged. You can now commit safely.[/bold green]")
                else:
                    ui.print_error("\nFailed to unstage files automatically. Please run the command manually.")
        
        raise typer.Exit(code=1)
    else:
        ui.console.print("[bold green]✅ Security check passed. No sensitive files found in staging.[/bold green]")


@app.command("gitignore")
def gitignore(
    path: str = typer.Option(".", "--path", "-p", help="Directory to save .gitignore"),
    auto_commit: bool = typer.Option(None, "--commit", "-c", help="Automatically commit the file")
) -> None:
    """Creates a .gitignore file interactively by combining multiple templates.

    Prompts the user to select one or multiple technologies using an interactive 
    checkbox menu. It combines the selected templates, removes duplicate rules 
    (while preserving comments), appends global OS/IDE rules, and generates 
    a .gitignore file. Optionally commits it automatically to the repository.

    Args:
        path (str): Directory where the .gitignore file will be saved. Defaults to ".".
        auto_commit (bool, optional): If True, automatically commits the file without prompting.

    Raises:
        typer.Exit: If the user cancels the operation, declines to overwrite 
            an existing file, or if file writing fails.
    """
    ui = TerminalUI()
    ui.console.print("\n[bold blue] 🐆 Chegi .gitignore Generator[/bold blue]\n")
    
    # 1. Interactive multi-selection logic using questionary checkbox
    options = list(TEMPLATES.keys())
    languages = [opt for opt in options if opt != "Global (OS/IDE)"]
    
    selected_langs = questionary.checkbox(
        "Select technologies for the .gitignore file (Space to select, Enter to confirm):",
        choices=languages
    ).ask()
    
    # Handle user cancellation or empty selection
    if not selected_langs:
        ui.console.print("[bold red]Operation cancelled or no technologies selected.[/bold red]")
        raise typer.Exit(1)
    
    # 2. Combine templates and deduplicate rules
    combined_content = []
    seen_rules = set()
    
    # Add header
    combined_content.append(f"# .gitignore generated by Chegi for: {', '.join(selected_langs)}\n")

    # Add selected languages templates
    for lang in selected_langs:
        combined_content.append(f"\n# =========================\n# {lang}\n# =========================")
        template_lines = TEMPLATES[lang].splitlines()
        
        for line in template_lines:
            stripped_line = line.strip()
            # Keep empty lines and comments intact
            if not stripped_line or stripped_line.startswith('#'):
                combined_content.append(line)
            else:
                # Deduplicate actual gitignore rules (e.g., node_modules/)
                if stripped_line not in seen_rules:
                    seen_rules.add(stripped_line)
                    combined_content.append(line)

    # Append Global OS/IDE Rules
    combined_content.append("\n# =========================\n# Global (OS/IDE)\n# =========================")
    global_lines = TEMPLATES["Global (OS/IDE)"].splitlines()
    
    for line in global_lines:
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith('#'):
            combined_content.append(line)
        else:
            if stripped_line not in seen_rules:
                seen_rules.add(stripped_line)
                combined_content.append(line)

    final_content = "\n".join(combined_content).strip() + "\n"

    # 3. Path & Writing
    target_path = Path(path).expanduser().resolve() / ".gitignore"
    
    if target_path.exists():
       if not Confirm.ask(f"⚠️  [yellow].gitignore already exists in {target_path}. Overwrite?[/yellow]", default=False):
            ui.console.print("[bold red]Aborted.[/bold red]")
            raise typer.Exit()

    try:
        target_path.write_text(final_content)
        ui.console.print(f"\n[bold green]✅ Created:[/bold green] {target_path}")
    except Exception as e:
        ui.print_error(f"❌ Error writing file: {e}")
        raise typer.Exit(1)

    # 4. Scoped Commit Logic
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"], 
            check=True, capture_output=True, cwd=path
        )
        is_git_repo = True
    except subprocess.CalledProcessError:
        is_git_repo = False

    if is_git_repo:
        should_commit = auto_commit
        if should_commit is None:
            should_commit = typer.confirm("🚀 Do you want to commit this new .gitignore file?", default=True)

        if should_commit:
            try:
                ui.console.print("[dim]Adding and committing .gitignore...[/dim]")
                subprocess.run(["git", "add", ".gitignore"], check=True, cwd=path)
                
                commit_msg = "chore(gitignore): add .gitignore via chegi 🐆"
                # Include '.gitignore' in the commit command to prevent committing other staged files
                subprocess.run(["git", "commit", ".gitignore", "-m", commit_msg], check=True, cwd=path)
                
                ui.console.print(f"[bold green]✨ Committed with message:[/bold green] {commit_msg}")
            except subprocess.CalledProcessError as e:
                ui.print_error(f"Failed to execute git commit: {e}")
        else:
            ui.console.print("[dim]Skipping commit.[/dim]")
    else:
        ui.console.print("[bold yellow]⚠️  Skipped commit: Not a git repository.[/bold yellow]")

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
    )
) -> None:
    """Changes a commit message interactively or directly.

    If no flags are provided, it modifies the last commit (HEAD).
    Use --last/-l to select from recent commits, or --start/-s and --end/-e 
    to paginate through older commits in the repository history.

    Args:
        message (Optional[str]): The new commit message. Prompts if not provided.
        last (Optional[int]): Number of recent commits to display for selection.
        start (Optional[int]): The starting index to skip before listing commits.
        end (Optional[int]): The ending index for listing commits.

    Raises:
        typer.Exit: If the directory is not a Git repository, if no commits are found,
            or if the git operations fail.
    """
    ui = TerminalUI()

    # --- Validation for --last ---
    if last is not None and last > 20:
        ui.print_error("❌ Maximum limit for --last is 20.")
        ui.print_error("💡 Please use --start/-s and --end/-e flags to navigate older commits.")
        raise typer.Exit(1)
    # -----------------------------

    try:
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        ui.print_error("❌ Not a git repository.")
        raise typer.Exit(1)

    target_hash = "HEAD"
    is_head = True

    # Determine if we need to show the interactive commit selection menu
    show_menu = last is not None or start is not None or end is not None

    if show_menu:
        # Pagination Logic: Calculate how many commits to skip and how many to fetch
        if start is not None and end is not None:
            if start >= end:
                ui.print_error("❌ Error: --start must be less than --end.")
                raise typer.Exit(1)
            skip = start
            limit = end - start
        elif start is not None:
            # Only start provided: fetch the next 10 commits starting from 'start'
            skip = start
            limit = 10
        elif end is not None:
            # Only end provided: fetch up to 10 commits preceding the 'end' index
            # The formula is: $$skip = max(0, end - 10)$$
            skip = max(0, end - 10)
            limit = end - skip
        else:
            # Default to --last if start/end are not provided
            skip = 0
            limit = last if last else 10

        try:
            # Use --skip and --max-count to fetch the exact window of commits
            result = subprocess.run(
                ["git", "log", f"--max-count={limit}", f"--skip={skip}", "--format=%h %s"],
                check=True, capture_output=True, text=True
            )
            commits = [line for line in result.stdout.strip().split("\n") if line]
            
            if not commits:
                ui.print_error("❌ No commits found in the specified range.")
                raise typer.Exit(1)
                
            choice = questionary.select(
                "Select the commit to reword:",
                choices=commits
            ).ask()
            
            if not choice:
                # User cancelled the selection menu (e.g., pressed Ctrl+C)
                raise typer.Exit(0)
                
            target_hash = choice.split(" ")[0]
            
            # Check if the selected hash is actually the current HEAD
            head_hash = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"], 
                capture_output=True, text=True
            ).stdout.strip()
            
            is_head = (target_hash == head_hash)

        except subprocess.CalledProcessError:
            ui.print_error("❌ Failed to fetch git history.")
            raise typer.Exit(1)

    # Fetch the old message of the target commit to use as default input
    try:
        old_msg_result = subprocess.run(
            ["git", "log", "--format=%B", "-n", "1", target_hash],
            check=True, capture_output=True, text=True
        )
        old_message = old_msg_result.stdout.strip()
    except subprocess.CalledProcessError:
        ui.print_error("❌ Failed to fetch the commit message.")
        raise typer.Exit(1)

    if not message:
        message = questionary.text(
            "Enter new commit message:",
            default=old_message
        ).ask()

        if not message:
            ui.print_error("❌ Commit message cannot be empty.")
            raise typer.Exit(1)

    # Graceful exit if the user leaves the message unchanged
    if message == old_message:
        ui.print_success("✅ Message is unchanged. Exiting without modifying history.")
        return

    # Apply the change
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
    """Synchronizes the local repository with the remote safely.

    Performs a `git pull --rebase` to fetch and apply upstream changes,
    followed by a `git push` to publish local commits. If the workspace
    contains uncommitted changes, it prompts the user with a double
    confirmation to safely stash and restore them.

    Raises:
        typer.Exit: If the user aborts the operation or if a Git command fails.
    """
    ui = TerminalUI()
    ui.print_info("Starting synchronization process...")

    needs_stash = False

    # 1. Workspace Validation & Double Confirmation
    if not is_workspace_clean():
        ui.print_warning("You have uncommitted changes in your workspace.")
        
        # First confirmation: Ask if user wants to auto-stash (Default: No)
        confirm_stash = typer.confirm(
            "Do you want to automatically stash changes, sync, and restore them?",
            default=False
        )
        if not confirm_stash:
            ui.print_error("Sync aborted. Please commit or stash your changes manually.")
            raise typer.Exit(1)
        
        # Second confirmation: Emphasize the risk of merge conflicts (Default: No)
        ui.print_warning("Restoring changes (stash pop) after sync might result in merge conflicts.")
        confirm_again = typer.confirm(
            "Are you absolutely sure you want to proceed?",
            default=False
        )
        if not confirm_again:
            ui.print_error("Sync aborted. Please commit or stash your changes manually.")
            raise typer.Exit(1)
        
        needs_stash = True

    # 2. Stash uncommitted changes securely
    if needs_stash:
        ui.print_info("Stashing uncommitted changes...")
        try:
            stash_changes()
        except RuntimeError as e:
            ui.print_error(str(e))
            raise typer.Exit(1)

    # 3. Pull latest changes using rebase to maintain a linear history
    ui.print_info("Pulling latest changes from remote (rebase)...")
    try:
        pull_rebase()
    except RuntimeError as e:
        ui.print_error("❌ Conflict or error during pull --rebase.")
        ui.print_error(str(e))
        ui.print_warning("💡 Please resolve conflicts manually, then run 'git rebase --continue'.")
        if needs_stash:
            ui.print_info("ℹ️ Your uncommitted changes are safely stored in git stash.")
        raise typer.Exit(1)

    # 4. Push local commits to the remote repository
    ui.print_info("Pushing local commits to remote...")
    try:
        push_changes()
    except RuntimeError as e:
        ui.print_error("❌ Error during push.")
        ui.print_error(str(e))
        if needs_stash:
            ui.print_info("ℹ️ Your uncommitted changes are safely stored in git stash.")
        raise typer.Exit(1)

    # 5. Restore previously stashed changes
    if needs_stash:
        ui.print_info("Restoring stashed changes...")
        try:
            pop_stash()
        except RuntimeError as e:
            # Do not exit with 1 here; the sync was successful, only stash pop had conflicts
            ui.print_warning("⚠️ Conflict or error occurred while restoring stashed changes.")
            ui.print_error(str(e))
            ui.print_warning("💡 Please resolve the conflicts manually in your code editor.")

    ui.print_success("Synchronization completed successfully! 🚀")


@config_app.command("list")
def config_list(
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config")
) -> None:
    """Lists the current configuration settings.

    Args:
        path (str): The base directory where the '.chegi.json' configuration file resides.
    """
    config = ChegiConfig(base_path=path)
    config.load()
    ui = TerminalUI()
    
    ui.console.print("[bold]Current Configuration:[/bold]")
    ui.console.print(f"  Max Depth: {config.max_depth}")
    ui.console.print(f"  MCTS: {getattr(config, 'mcts', 10)}")
    ui.console.print(f"  Exclude Dirs: {', '.join(config.exclude_dirs)}")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key (e.g., max_depth, mcts)"),
    value: int = typer.Argument(..., help="New integer value"),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config")
) -> None:
    """Updates a specific configuration setting.

    Args:
        key (str): The name of the configuration setting to update.
        value (int): The new integer value to assign to the setting.
        path (str): The base directory where the configuration file resides.

    Raises:
        typer.Exit: If the provided key is invalid or the update process fails.
    """
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
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config")
) -> None:
    """Adds a directory name to the scanning exclusion list.

    Args:
        folder (str): The name of the directory to add to the blacklist.
        path (str): The base directory where the configuration file resides.
    """
    config = ChegiConfig(base_path=path)
    config.load()
    config.add_exclude(folder)
    config.save()
    
    ui = TerminalUI()
    ui.console.print(f"[green]Added '{folder}' to the exclude list.[/green]")


@config_app.command("exclude-remove")
def config_exclude_remove(
    folder: str = typer.Argument(..., help="Folder name to stop ignoring"),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config")
) -> None:
    """Removes a directory name from the scanning exclusion list.

    Args:
        folder (str): The name of the directory to remove from the blacklist.
        path (str): The base directory where the configuration file resides.

    Raises:
        typer.Exit: If the specified folder is not found in the exclude list.
    """
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

@app.command(name="setup")
def setup_environment(
    environment: str = typer.Argument(
        ..., 
        help="The programming language or toolset to setup (e.g., python, ruby)."
    ),
    auto_yes: bool = typer.Option(
        False, 
        "--yes", 
        "-y", 
        help="Automatically answer yes to all installation prompts."
    )
) -> None:
    """Sets up the development environment for a specific language.

    This command analyzes the system, checks for installed tools based on Chegi's
    environment database, displays a status report, and provides a guided
    interactive installation for missing dependencies.

    Args:
        environment (str): The name of the environment to configure (e.g., 'python').
        auto_yes (bool): If True, skips the interactive selection prompt and installs 
            all missing tools automatically.

    Raises:
        typer.Exit: If the requested environment is unsupported, if the JSON data 
            fails to load, or if the user aborts the operation.
    """
    ui = TerminalUI()
    env_manager = EnvManager()
    
    available_envs = env_manager.get_available_envs()

    # Validate if the requested environment exists in our JSON database
    if environment.lower() not in available_envs:
        ui.print_error(f"Environment '{environment}' is not supported.")
        ui.print_info(f"Available environments: {', '.join(available_envs)}")
        raise typer.Exit(code=1)

    env_data = env_manager.get_env(environment.lower())
    if not env_data:
        ui.print_error(f"Failed to load configuration data for '{environment}'.")
        raise typer.Exit(code=1)
    
    ui.print_info(f"Analyzing environment for: [bold yellow]{environment.capitalize()}[/bold yellow]")
    
    pkg_manager = SystemInstaller.get_os_package_manager()
    ui.console.print(f"Detected Package Manager: [bold cyan]{pkg_manager}[/bold cyan]\n")
    
    # Initialize the Rich Table for displaying tool statuses
    table = Table(
        title=f"{environment.capitalize()} Environment Status", 
        show_header=True, 
        header_style="bold magenta"
    )
    table.add_column("Tool", style="cyan", no_wrap=True)
    table.add_column("Level", style="blue")
    table.add_column("Status", justify="center")
    table.add_column("Version/Info", style="dim")

    # Extract sections from the loaded JSON data
    levels = env_data.get("levels", {})
    levels_info = env_data.get("levels_info", {})
    tools_data = env_data.get("tools", {})

    tools_to_install = []

    # Show a spinner while executing check commands for all tools
    with ui.console.status("[bold green]Checking installed tools...[/bold green]", spinner="dots"):
        for level_id, tool_names in levels.items():
            level_name = levels_info.get(level_id, f"Level {level_id}")
            
            for tool_name in tool_names:
                tool_info = tools_data.get(tool_name)
                
                # Skip if tool definition is missing in the 'tools' section
                if not tool_info:
                    continue
                    
                check_cmd = tool_info.get("check_cmd", "")
                if not check_cmd:
                    continue
                
                is_installed, info = SystemInstaller.is_tool_installed(check_cmd)
                
                if is_installed:
                    status_str = "[bold green]✔ Installed[/bold green]"
                else:
                    status_str = "[bold red]✖ Missing[/bold red]"
                    
                    install_cmds = tool_info.get("install", {})
                    # Prioritize the OS-specific package manager (e.g., 'apt', 'brew').
                    # Fallback to 'default' (e.g., 'pip', 'npm') if no OS-specific command exists.
                    cmd_to_run = install_cmds.get(pkg_manager) or install_cmds.get("default")
                    
                    if cmd_to_run:
                        tools_to_install.append({
                            "name": tool_name,
                            "level": level_name,
                            "cmd": cmd_to_run
                        })
                    else:
                        # If no install command is found for the OS, mark as manual
                        status_str = "[bold yellow]⚠ Manual[/bold yellow]"
                        
                table.add_row(tool_name, level_name, status_str, info)

    ui.console.print(table)
    ui.console.print("\n")

    # Exit early if everything is already installed
    if not tools_to_install:
        ui.print_success(f"All critical tools for {environment.capitalize()} are already installed! 🎉")
        raise typer.Exit()

    ui.print_info(f"Found {len(tools_to_install)} missing tools that can be installed automatically.")
    
    # Handle interactive tool selection if --yes flag is not provided
    if not auto_yes:
        # Create choices for the interactive checkbox menu. 
        # By passing the entire dictionary as `value`, we keep the command associated with the name.
        choices = [
            questionary.Choice(title=f"{t['name']} ({t['level']})", value=t, checked=True)
            for t in tools_to_install
        ]
        
        selected_tools = questionary.checkbox(
            "Select the tools you want to install (Space to toggle, Enter to confirm):",
            choices=choices
        ).ask()

        # Handle user cancellation (Ctrl+C during prompt) or empty selection
        if not selected_tools:
            ui.print_info("Setup aborted by user or no tools selected. No changes were made.")
            raise typer.Exit()
            
        tools_to_install = selected_tools

    success_count = 0
    
    # Wrap the installation loop in a try-except block to gracefully handle 
    # KeyboardInterrupt (Ctrl+C) without showing a messy Python traceback.
    try:
        for tool in tools_to_install:
            ui.console.print(f"\n[bold blue]▶ Installing {tool['name']} ({tool['level']})...[/bold blue]")
            success = SystemInstaller.run_custom_command(tool["cmd"])
            
            if success:
                ui.print_success(f"✅ {tool['name']} installed successfully.")
                success_count += 1
            else:
                ui.print_error(f"❌ Failed to install {tool['name']}. You may need to run with sudo or install it manually.")
                
    except KeyboardInterrupt:
        # Catch local interruption and exit cleanly
        ui.console.print("\n[bold red]❌ Installation interrupted by user (Ctrl+C).[/bold red]")
        raise typer.Exit(code=1)

    ui.console.print("\n")
    if success_count == len(tools_to_install):
        ui.print_success("✨ Environment setup completed successfully! ✨")
    else:
        ui.print_info(f"Setup finished. Installed {success_count} of {len(tools_to_install)} tools.")


def main() -> None:
    """Main entry point for the cheGi Typer CLI application."""
    app()
