import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterator, List, Optional

import typer
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from chegi.config import ChegiConfig
from chegi.services.git.client import GitClient
from chegi.services.git.exceptions import GitCommandError
from chegi.services.git.models import GitStatus
from chegi.services.guard import SecurityGuard
from chegi.services.guard.models import GuardScanResult
from chegi.services.scanner.exceptions import InvalidDirectoryError
from chegi.services.scanner.models import ScanOptions
from chegi.ui import TerminalUI, console, display_results_table


class ScanService:
    """Service responsible for executing the repository scanning logic.

    Attributes:
        options (ScanOptions): The configuration options for the scan.
        base_path (Path): The resolved absolute path to start scanning from.
        config (ChegiConfig): Loaded configuration for the scanner.
    """

    def __init__(self, options: ScanOptions):
        """Initializes the ScanService with the provided scan options.

        Args:
            options (ScanOptions): Configuration and filter options for scanning.
        """
        self.options = options
        self.base_path = Path(self.options.path).resolve()
        
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
        if self.options.max_depth is not None:
            config.max_depth = self.options.max_depth
        return config

    def execute(self) -> None:
        """Main entry point to execute the scan operation.

        This method orchestrates the scanning process: finding repositories,
        analyzing them concurrently, applying user filters, and displaying
        the final results in the terminal.
        """
        console.print(
            f"[dim]🔍 Scanning '{self.base_path}' (max depth: {self.config.max_depth})...[/dim]"
        )

        # 1. Find Repositories
        repo_paths = self._get_repositories()
        if not repo_paths:
            display_results_table([])
            return

        # 2. Analyze Repositories
        statuses = self._analyze_repositories(repo_paths)

        # 3. Filter Results
        statuses = self._filter_results(statuses)

        # 4. Display Results
        if not statuses:
            console.print(
                "\n[bold yellow]No repositories matched your filters.[/bold yellow]"
            )
            return

        display_results_table(statuses)

    def _find_git_repos(self, start_path: str) -> Iterator[Path]:
        """Core logic to traverse directories and find .git folders.

        Args:
            start_path (str): The directory path to start the search from.

        Yields:
            Iterator[Path]: Paths to discovered Git repositories.

        Raises:
            InvalidDirectoryError: If the start_path is not a valid directory.
        """
        start_path_obj = Path(start_path)
        if not start_path_obj.is_dir():
            raise InvalidDirectoryError(f"The directory '{start_path}' does not exist.")

        start_level = len(start_path_obj.parts)

        for root, dirs, _ in os.walk(start_path_obj):
            root_path = Path(root)

            # Check max depth
            if self.config.max_depth is not None:
                current_level = len(root_path.parts)
                if current_level - start_level >= self.config.max_depth:
                    dirs[:] = []  # Stop traversing deeper
                    continue

            # Remove ignored directories
            dirs[:] = [d for d in dirs if d not in self.config.exclude_dirs]

            # Yield if it's a git repo
            if (root_path / ".git").is_dir():
                yield root_path
                dirs[:] = []  # Stop traversing inside the repository (ignores submodules)

    def _get_repositories(self) -> List[Path]:
        """Finds all git repositories in the base path.

        Returns:
            List[Path]: A list of Path objects pointing to git repositories.

        Raises:
            typer.Exit: If the target path is not a valid directory.
        """
        try:
            return list(self._find_git_repos(str(self.base_path)))
        except InvalidDirectoryError as e:
            TerminalUI.print_error(str(e))
            raise typer.Exit(code=1)

    def _analyze_single_repo(self, repo_path: Path, security_scanner: Optional[Callable[[Path], GuardScanResult]] = None) -> GitStatus:
        """Extracts the git status for a single repository.

        Args:
            repo_path (Path): The path to the git repository to analyze.
            security_scanner (Optional[Callable[[Path], GuardScanResult]]): A function to perform security scans.

        Returns:
            GitStatus: An object containing the extracted status of the repository.
        """
        repo_name = repo_path.name
        git_client = GitClient(repo_path)
        try:
            # 1. Branch Name
            branch = git_client.run_command(["git", "branch", "--show-current"]) or "No Commits"

            # 2. Local Status (Dirty / Staged / Clean)
            status_output = git_client.run_command(["git", "status", "--porcelain"])
            is_dirty = len(status_output) > 0

            has_staged_files = False
            if is_dirty:
                for line in status_output.splitlines():
                    if line and line[0] not in (" ", "?"):
                        has_staged_files = True
                        break

            local_status = "Staged" if has_staged_files else ("Dirty" if is_dirty else "Clean")

            # 3. Remote Status
            remote_output = git_client.run_command(["git", "remote"])
            has_remote = len(remote_output) > 0

            remote_status = "No Remote"
            if has_remote and branch != "No Commits":
                # Check if there is an upstream branch configured
                try:
                    git_client.run_command(["git", "rev-parse", "--abbrev-ref", "@{u}"])
                except GitCommandError:
                    remote_status = "Local Only"

                if remote_status != "Local Only":
                    # Check ahead and behind counts
                    try:
                        rev_list = git_client.run_command(
                            ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"]
                        )
                        counts = rev_list.split()
                        if len(counts) == 2:
                            ahead, behind = int(counts[0]), int(counts[1])
                            if ahead > 0 and behind > 0:
                                remote_status = f"Diverged ({ahead}A/{behind}B)"
                            elif ahead > 0:
                                remote_status = f"Ahead ({ahead})"
                            elif behind > 0:
                                remote_status = f"Behind ({behind})"
                            else:
                                remote_status = "Synced"
                        else:
                            remote_status = "Unknown"
                    except GitCommandError:
                        remote_status = "Unknown"

            # Combine local and remote statuses
            final_status = f"{local_status} | {remote_status}"

            # 4. Security Status
            sec_status = None
            if security_scanner:
                try:
                    scan_result = security_scanner(repo_path)
                    if not scan_result.is_safe:
                        sensitive = ", ".join(scan_result.sensitive_files)
                        sec_status = f"Sensitive: {sensitive}"
                    else:
                        sec_status = "Safe"
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
                status=final_status,
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
                status="Error",
            )

    def _analyze_repositories(self, repo_paths: List[Path]) -> List[GitStatus]:
        """Runs concurrent analysis on the found repositories.

        Args:
            repo_paths (List[Path]): List of repository paths to analyze.

        Returns:
            List[GitStatus]: A list of GitStatus objects containing analysis results.
        """
        scanner_func = SecurityGuard.scan_repo if self.options.security else None
        statuses: List[GitStatus] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]⚡ Analyzing repositories...", total=len(repo_paths))

            with ThreadPoolExecutor(max_workers=self.options.workers) as executor:
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
        if self.options.dirty:
            filtered_statuses = [s for s in filtered_statuses if s.is_dirty]
        if self.options.staged:
            filtered_statuses = [s for s in filtered_statuses if s.has_staged_files]
        return filtered_statuses
