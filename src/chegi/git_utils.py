import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Tuple

MIN_GIT_VERSION = (2, 25, 0)

def check_git_environment() -> Tuple[bool, str]:
    """
    Checks if Git is installed and meets the minimum version requirement.

    Returns:
        Tuple[bool, str]: A tuple containing:
            - bool: True if Git is installed and the version is valid, False otherwise.
            - str: A message describing the status, error, or current Git version.
    """
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        version_str = result.stdout.strip()
        
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_str)
        if match:
            current_version = tuple(map(int, match.groups()))
            
            if current_version < MIN_GIT_VERSION:
                min_v_str = '.'.join(map(str, MIN_GIT_VERSION))
                return False, f"Git version is too old: {version_str}. Minimum required: {min_v_str}"
            
            return True, version_str
        
        return False, "Could not determine Git version."

    except FileNotFoundError:
        return False, "Git is not installed or not found in system PATH."
    except Exception as e:
        return False, f"An unexpected error occurred while checking Git: {str(e)}"


@dataclass
class GitStatus:
    """
    Represents the extracted status of a single Git repository.
    
    Attributes:
        path (Path): Absolute path to the repository.
        repo_name (str): The name of the repository folder.
        branch (str): Current active branch name.
        is_dirty (bool): True if there are uncommitted changes.
        has_remote (bool): True if the repository has a configured remote URL.
        error (str): Error message if the repository analysis fails.
    """
    path: Path
    repo_name: str
    branch: str
    is_dirty: bool
    has_remote: bool
    error: str = ""    


class GitAnalyzer:
    """
    Handles executing Git commands and analyzing repository statuses concurrently.
    """
    
    def __init__(self, max_workers: int = 10):
        """
        Initializes the GitAnalyzer with a specific concurrency limit.

        Args:
            max_workers (int): Maximum number of threads to use for concurrent analysis.
        """
        self.max_workers = max_workers

    def _run_git_command(self, cwd: Path, *args: str) -> str:
        """
        Executes a git command in the specified directory.

        Args:
            cwd (Path): The current working directory where the command should be run.
            *args (str): The git arguments (e.g., "status", "--porcelain").

        Returns:
            str: The standard output of the git command, stripped of leading/trailing whitespace.
            
        Raises:
            RuntimeError: If the git command execution fails.
        """
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() or "Git command execution failed"
            raise RuntimeError(error_msg)

    def analyze_single_repo(self, repo_path: Path) -> GitStatus:
        """
        Extracts the git status (branch, dirty state, remote state) for a single repository.

        Args:
            repo_path (Path): The path to the git repository.

        Returns:
            GitStatus: An object containing the analyzed status of the repository.
        """
        repo_name = repo_path.name
        
        try:
            # 1. Get current branch
            branch = self._run_git_command(repo_path, "branch", "--show-current")
            if not branch:
                branch = "No Commits"
                
            # 2. Check for uncommitted changes (dirty state)
            status_output = self._run_git_command(repo_path, "status", "--porcelain")
            is_dirty = len(status_output) > 0
            
            # 3. Check for remote configuration
            remote_output = self._run_git_command(repo_path, "remote")
            has_remote = len(remote_output) > 0
            
            return GitStatus(
                path=repo_path,
                repo_name=repo_name,
                branch=branch,
                is_dirty=is_dirty,
                has_remote=has_remote
            )
            
        except Exception as e:
            # Return a fallback GitStatus object if the directory is corrupted or lacks permissions
            return GitStatus(
                path=repo_path,
                repo_name=repo_name,
                branch="Unknown",
                is_dirty=False,
                has_remote=False,
                error=str(e)
            )

    def analyze_concurrently(self, repo_paths: Iterable[Path]) -> Iterator[GitStatus]:
        """
        Processes an iterable of repository paths concurrently using a thread pool.

        Args:
            repo_paths (Iterable[Path]): A collection of repository paths to analyze.

        Yields:
            GitStatus: The status object for each repository as soon as its analysis is completed.
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Map the execution of analyze_single_repo to the thread pool
            future_to_path = {
                executor.submit(self.analyze_single_repo, path): path 
                for path in repo_paths
            }
            
            # Yield completed futures as soon as they finish
            for future in as_completed(future_to_path):
                yield future.result()
