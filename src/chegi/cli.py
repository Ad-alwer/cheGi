import typer
from pathlib import Path

from chegi.config import load_config
from chegi.scanner import find_git_repos
from chegi.git_utils import GitAnalyzer
from chegi.ui import TerminalUI

app = typer.Typer(help="cheGi - Fast & Concurrent Git Repository Manager")

@app.command()
def scan(
    path: str = typer.Argument(".", help="Base directory to scan"),
    max_depth: int = typer.Option(3, "--max-depth", "-d", help="Max depth to search"),
    workers: int = typer.Option(5, "--workers", "-w", help="Number of concurrent workers"),
):
    """Scan directory for Git repositories and report their status."""
    ui = TerminalUI()
    base_path = Path(path).resolve()
    
    if not base_path.exists() or not base_path.is_dir():
        ui.print_error(f"Invalid path: {base_path}")
        raise typer.Exit(code=1)

    # Load excluded directories (e.g., node_modules) to prevent getting stuck in junk folders
    exclude_dirs = load_config(str(base_path))
    
    ui.console.print(f"[dim]🔍 Scanning '{base_path}' (max depth: {max_depth})...[/dim]")
    repo_paths = list(find_git_repos(str(base_path), max_depth, exclude_dirs))
    
    if not repo_paths:
        ui.display_results_table([])
        raise typer.Exit()

    ui.console.print(f"[dim]⚡ Analyzing {len(repo_paths)} repositories...[/dim]")
    
    # Concurrently analyze all found repositories to maximize performance
    analyzer = GitAnalyzer(max_workers=workers)
    statuses = analyzer.analyze_concurrently(repo_paths)
    
    ui.display_results_table(statuses)

def main():
    app()
