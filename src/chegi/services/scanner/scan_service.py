from pathlib import Path
from typing import Any, List, Optional

import typer
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from chegi.config import ChegiConfig
from chegi.git_utils import GitAnalyzer
from chegi.security import SecurityGuard
from chegi.ui import TerminalUI
from chegi.utils.finder import find_git_repos


class ScanService:
    """Service responsible for executing the repository scanning logic.

    Attributes:
        base_path (Path): The resolved absolute path to start scanning from.
        max_depth (Optional[int]): Maximum directory depth to traverse.
        workers (int): Number of concurrent threads for analyzing repositories.
        security (bool): Flag to enable security scanning.
        dirty (bool): Flag to filter and show only repositories with uncommitted changes.
        staged (bool): Flag to filter and show only repositories with staged files.
        ui (TerminalUI): Instance of the terminal UI manager.
        config (ChegiConfig): Loaded configuration for the scanner.
    """

    def __init__(
        self,
        path: str,
        max_depth: Optional[int],
        workers: int,
        security: bool,
        dirty: bool,
        staged: bool,
    ):
        """Initializes the ScanService with the provided CLI arguments.

        Args:
            path (str): Base directory to scan.
            max_depth (Optional[int]): Override max depth from config.
            workers (int): Number of concurrent workers.
            security (bool): Perform security scan on repositories.
            dirty (bool): Only show repositories with uncommitted changes.
            staged (bool): Only show repositories with staged files.
        """
        self.base_path = Path(path).resolve()
        self.max_depth = max_depth
        self.workers = workers
        self.security = security
        self.dirty = dirty
        self.staged = staged
        
        self.ui = TerminalUI()
        self.config = self._init_config()

    def _init_config(self) -> ChegiConfig:
        """Initializes and loads the configuration for the scanner.

        Loads the default configuration and overrides the max_depth if it was
        explicitly provided by the user.

        Returns:
            ChegiConfig: The initialized and loaded configuration object.
        """
        config = ChegiConfig(base_path=str(self.base_path))
        config.load()
        if self.max_depth is not None:
            config.max_depth = self.max_depth
        return config

    def execute(self) -> None:
        """Main entry point to execute the scan operation.

        This method orchestrates the scanning process: finding repositories,
        analyzing them concurrently, applying user filters, and displaying
        the final results in the terminal.
        """
        self.ui.console.print(
            f"[dim]🔍 Scanning '{self.base_path}' (max depth: {self.config.max_depth})...[/dim]"
        )

        # 1. Find Repositories
        repo_paths = self._get_repositories()
        if not repo_paths:
            self.ui.display_results_table([])
            return

        # 2. Analyze Repositories
        statuses = self._analyze_repositories(repo_paths)

        # 3. Filter Results
        statuses = self._filter_results(statuses)

        # 4. Display Results
        if not statuses:
            self.ui.console.print(
                "\n[bold yellow]No repositories matched your filters.[/bold yellow]"
            )
            return

        self.ui.display_results_table(statuses)

    def _get_repositories(self) -> List[str]:
        """Finds all git repositories in the base path.

        Returns:
            List[str]: A list of string paths pointing to git repositories.

        Raises:
            typer.Exit: If the target path is not a valid directory.
        """
        try:
            # Convert Path objects yielded by find_git_repos to strings
            return [str(p) for p in find_git_repos(str(self.base_path), self.config)]
        except NotADirectoryError as e:
            self.ui.print_error(str(e))
            raise typer.Exit(code=1)

    def _analyze_repositories(self, repo_paths: List[str]) -> List[Any]:
        """Runs concurrent analysis on the found repositories.

        Args:
            repo_paths (List[str]): List of repository paths to analyze.

        Returns:
            List[Any]: A list of repository status objects containing analysis results.
        """
        analyzer = GitAnalyzer(max_workers=self.workers)
        scanner_func = SecurityGuard.scan_repo if self.security else None
        statuses = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.ui.console,
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

        return statuses

    def _filter_results(self, statuses: List[Any]) -> List[Any]:
        """Filters the analysis results based on CLI flags.

        Args:
            statuses (List[Any]): The raw list of repository statuses.

        Returns:
            List[Any]: The filtered list of repository statuses matching the conditions
                (e.g., dirty or staged).
        """
        filtered_statuses = statuses
        
        if self.dirty:
            filtered_statuses = [s for s in filtered_statuses if s.is_dirty]

        if self.staged:
            filtered_statuses = [s for s in filtered_statuses if s.has_staged_files]

        return filtered_statuses
