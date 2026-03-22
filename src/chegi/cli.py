import typer
from pathlib import Path
from typing import Optional, Annotated

from chegi.config import ChegiConfig
from chegi.scanner import find_git_repos
from chegi.git_utils import GitAnalyzer, check_git_environment
from chegi.ui import TerminalUI
from chegi.installer import SystemInstaller
from chegi.security import SecurityGuard

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
) -> None:
    """Scans a directory recursively for Git repositories and reports their status.

    Args:
        path (str): The root directory where the scanning process begins.
        max_depth (Optional[int]): Overrides the configuration's maximum folder depth.
        workers (int): Number of concurrent threads for analyzing repositories.
        security (bool): If True, performs a security scan on staged files for each repository.

    Raises:
        typer.Exit: If the specified path is not a valid directory or if no 
            repositories are found.
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

    ui.console.print(f"[dim]⚡ Analyzing {len(repo_paths)} repositories...[/dim]")
    
    analyzer = GitAnalyzer(max_workers=workers)

    scanner_func = SecurityGuard.scan_repo if security else None
    
    statuses = analyzer.analyze_concurrently(repo_paths, security_scanner=scanner_func)
    
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


def main() -> None:
    """Main entry point for the cheGi Typer CLI application."""
    app()
