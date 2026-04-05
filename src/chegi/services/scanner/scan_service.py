import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, List, Optional

import typer
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from chegi.config import ChegiConfig
from chegi.security import SecurityGuard
from chegi.ui import TerminalUI
from chegi.utils.finder import find_git_repos
from chegi.services.git.models import GitStatus


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
            workers (int): Number of concurrent workers for analysis.
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

    def _get_repositories(self) -> List[Path]:
        """Finds all git repositories in the base path.

        Returns:
            List[Path]: A list of Path objects pointing to git repositories.

        Raises:
            typer.Exit: If the target path is not a valid directory.
        """
        try:
            return list(find_git_repos(str(self.base_path), self.config))
        except NotADirectoryError as e:
            self.ui.print_error(str(e))
            raise typer.Exit(code=1)

    def _analyze_single_repo(self, repo_path: Path, security_scanner: Optional[Callable[[Path], str]] = None) -> GitStatus:
        """Extracts the git status for a single repository.

        Args:
            repo_path (Path): The path to the git repository to analyze.
            security_scanner (Optional[Callable[[Path], str]]): A function to perform security scans.

        Returns:
            GitStatus: An object containing the extracted status of the repository.
        """
        repo_name = repo_path.name
        try:
            branch_result = subprocess.run(["git", "branch", "--show-current"], cwd=repo_path, capture_output=True, text=True)
            branch = branch_result.stdout.strip() or "No Commits"

            status_result = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True)
            status_output = status_result.stdout.strip()
            is_dirty = len(status_output) > 0

            has_staged_files = False
            if is_dirty:
                for line in status_output.splitlines():
                    if line and line[0] not in (" ", "?"):
                        has_staged_files = True
                        break

            remote_result = subprocess.run(["git", "remote"], cwd=repo_path, capture_output=True, text=True)
            has_remote = len(remote_result.stdout.strip()) > 0

            sec_status = None
            if security_scanner:
                try:
                    sec_status = security_scanner(repo_path)
                except Exception:
                    sec_status = "Scan Failed"

            return GitStatus(
                path=repo_path,
                repo_name=repo_name,
                branch=branch,
                is_dirty=is_dirty,
                has_staged_files=has_staged_files,
                has_remote=has_remote,
                security_status=sec_status,
            )
        except Exception as e:
            return GitStatus(
                path=repo_path,
                repo_name=repo_name,
                branch="Unknown",
                is_dirty=False,
                has_staged_files=False,
                has_remote=False,
                error=str(e),
            )

    def _analyze_repositories(self, repo_paths: List[Path]) -> List[GitStatus]:
        """Runs concurrent analysis on the found repositories.

        Args:
            repo_paths (List[Path]): List of repository paths to analyze.

        Returns:
            List[GitStatus]: A list of GitStatus objects containing analysis results.
        """
        scanner_func = SecurityGuard.scan_repo if self.security else None
        statuses: List[GitStatus] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.ui.console,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]⚡ Analyzing repositories...", total=len(repo_paths))

            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                future_to_path = {
                    executor.submit(self._analyze_single_repo, path, scanner_func): path
                    for path in repo_paths
                }

                for future in as_completed(future_to_path):
                    statuses.append(future.result())
                    progress.advance(task)

        return statuses

    def _filter_results(self, statuses: List[GitStatus]) -> List[GitStatus]:
        """Filters the analysis results based on CLI flags.

        Args:
            statuses (List[GitStatus]): The raw list of repository statuses.

        Returns:
            List[GitStatus]: The filtered list of repository statuses matching the conditions
                (e.g., dirty or staged).
        """
        filtered_statuses = statuses
        if self.dirty:
            filtered_statuses = [s for s in filtered_statuses if s.is_dirty]
        if self.staged:
            filtered_statuses = [s for s in filtered_statuses if s.has_staged_files]
        return filtered_statuses
