import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed

@dataclass
class GitStatus:
    """Represents the extracted status of a single Git repository."""
    path: Path
    repo_name: str
    branch: str
    is_dirty: bool      # True if there are uncommitted changes
    has_remote: bool    # True if the repository has a configured remote
    error: str = ""    


class GitAnalyzer:
    """
    Handles executing Git commands and analyzing repository statuses concurrently.
    """
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers

    def _run_git_command(self, cwd: Path, *args: str) -> str:
        """
        Executes a git command in the specified directory.
        Private method used internally by the class.
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
        Extracts the git status for a single repository path.
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
        Yields results as soon as they are completed (Lazy Evaluation).
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
