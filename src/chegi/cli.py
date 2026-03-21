import typer
from pathlib import Path
from typing import Optional

from chegi.config import ChegiConfig
from chegi.scanner import find_git_repos
from chegi.git_utils import GitAnalyzer, check_git_environment
from chegi.ui import TerminalUI

app = typer.Typer(help="cheGi - Fast & Concurrent Git Repository Manager")
config_app = typer.Typer(help="Manage cheGi configuration")
app.add_typer(config_app, name="config")

@app.callback()
def global_setup():
    """
    Global setup executed before any command.
    Ensures that Git is installed and meets the minimum version requirement.
    """
    is_ok, message = check_git_environment()
    if not is_ok:
        ui = TerminalUI()
        ui.print_error(message)
        raise typer.Exit(code=1)

@app.command("scan")
def scan(
    path: str = typer.Argument(".", help="Base directory to scan"),
    max_depth: Optional[int] = typer.Option(None, "--max-depth", "-d", help="Override max depth from config"),
    workers: int = typer.Option(5, "--workers", "-w", help="Number of concurrent workers"),
) -> None:
    """Scan directory for Git repositories and report their status.

    Args:
        path (str): The root directory where scanning begins.
        max_depth (Optional[int]): Overrides config's max folder depth if provided.
        workers (int): Number of threads for analyzing repositories.
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
    statuses = analyzer.analyze_concurrently(repo_paths)
    
    ui.display_results_table(statuses)

@config_app.command("list")
def config_list(path: str = typer.Option(".", "--path", "-p", help="Base directory for config")):
    """List current configuration settings.

    Args:
        path (str): The base directory where the .chegi.json config resides.
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
):
    """Set a configuration value.

    Args:
        key (str): The setting name to update.
        value (int): The new value for the setting.
        path (str): The base directory where the .chegi.json config resides.
    """
    config = ChegiConfig(base_path=path)
    config.load()
    try:
        config.update_setting(key, value)
        config.save()
        TerminalUI().console.print(f"[green]Successfully updated {key} to {value}.[/green]")
    except ValueError as e:
        TerminalUI().print_error(str(e))
        raise typer.Exit(code=1)

@config_app.command("exclude-add")
def config_exclude_add(
    folder: str = typer.Argument(..., help="Folder name to ignore"),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config")
):
    """Add a folder to the exclude list.

    Args:
        folder (str): The name of the directory to add to the blacklist.
        path (str): The base directory where the config resides.
    """
    config = ChegiConfig(base_path=path)
    config.load()
    config.add_exclude(folder)
    config.save()
    TerminalUI().console.print(f"[green]Added '{folder}' to exclude list.[/green]")

@config_app.command("exclude-remove")
def config_exclude_remove(
    folder: str = typer.Argument(..., help="Folder name to stop ignoring"),
    path: str = typer.Option(".", "--path", "-p", help="Base directory for config")
):
    """Remove a folder from the exclude list.

    Args:
        folder (str): The name of the directory to remove from the blacklist.
        path (str): The base directory where the config resides.
    """
    config = ChegiConfig(base_path=path)
    config.load()
    try:
        config.remove_exclude(folder)
        config.save()
        TerminalUI().console.print(f"[green]Removed '{folder}' from exclude list.[/green]")
    except ValueError as e:
        TerminalUI().print_error(str(e))
        raise typer.Exit(code=1)

def main() -> None:
    """Main entry point for the Typer CLI application."""
    app()
