import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Tuple, Callable, Optional

MIN_GIT_VERSION = (2, 25, 0)


def check_git_environment() -> Tuple[bool, str]:
    """Checks if Git is installed and meets the minimum version requirement.

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
    """Represents the extracted status of a single Git repository.
    
    Attributes:
        path (Path): Absolute path to the repository.
        repo_name (str): The name of the repository folder.
        branch (str): Current active branch name.
        is_dirty (bool): True if there are uncommitted changes.
        has_staged_files (bool): True if there are files in the staging area.
        has_remote (bool): True if the repository has a configured remote URL.
        error (str): Error message if the repository analysis fails.
        security_status (Optional[str]): Security scan result if requested.
    """
    path: Path
    repo_name: str
    branch: str
    is_dirty: bool
    has_remote: bool
    error: str = ""
    has_staged_files: bool =False
    security_status: Optional[str] = None


class GitAnalyzer:
    """Handles executing Git commands and analyzing repository statuses concurrently."""
    
    def __init__(self, max_workers: int = 10):
        """Initializes the GitAnalyzer with a specific concurrency limit.

        Args:
            max_workers (int): Maximum number of threads to use for concurrent analysis.
        """
        self.max_workers = max_workers

    def _run_git_command(self, cwd: Path, *args: str) -> str:
        """Executes a git command in the specified directory.

        Args:
            cwd (Path): The current working directory where the command should be run.
            *args (str): The git arguments.

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

    def analyze_single_repo(self, repo_path: Path, security_scanner: Optional[Callable[[Path], str]] = None) -> GitStatus:
        """Extracts the git status for a single repository.

        Args:
            repo_path (Path): The path to the git repository.
            security_scanner (Callable, optional): A function that takes a Path and returns a security status string.

        Returns:
            GitStatus: An object containing the analyzed status of the repository.
        """
        repo_name = repo_path.name
        
        try:
            branch = self._run_git_command(repo_path, "branch", "--show-current")
            if not branch:
                branch = "No Commits"
                
            status_output = self._run_git_command(repo_path, "status", "--porcelain")
            is_dirty = len(status_output) > 0
            
            has_staged_files = False
            if is_dirty:
                for line in status_output.splitlines():
                    if line and line[0] not in (' ', '?'):
                        has_staged_files = True
                        break
            
            remote_output = self._run_git_command(repo_path, "remote")
            has_remote = len(remote_output) > 0
            
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
                security_status=sec_status
            )
            
        except Exception as e:
            return GitStatus(
                path=repo_path,
                repo_name=repo_name,
                branch="Unknown",
                is_dirty=False,
                has_staged_files=False,
                has_remote=False,
                error=str(e)
            )

    def analyze_concurrently(self, repo_paths: Iterable[Path], security_scanner: Optional[Callable[[Path], str]] = None) -> Iterator[GitStatus]:
        """Processes an iterable of repository paths concurrently using a thread pool.

        Args:
            repo_paths (Iterable[Path]): A collection of repository paths to analyze.
            security_scanner (Callable, optional): A function to scan security for each repo.

        Yields:
            GitStatus: The status object for each repository as soon as its analysis is completed.
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(self.analyze_single_repo, path, security_scanner): path 
                for path in repo_paths
            }
            
            for future in as_completed(future_to_path):
                yield future.result()

def perform_automated_rebase(target_hash: str, new_message: str) -> None:
    """Performs an automated interactive rebase to reword a specific commit.

    This function automates the interactive rebase process by injecting temporary
    Python scripts as Git's sequence and message editors. It automatically marks
    the target commit for rewording and supplies the new message.

    Args:
        target_hash (str): The exact commit hash to be modified.
        new_message (str): The new commit message to apply.

    Raises:
        subprocess.CalledProcessError: If the git rebase operation fails.
    """
    seq_editor_path = ""
    msg_editor_path = ""
    
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as seq_editor:
            seq_editor.write(f"""#!{sys.executable}
import sys
with open(sys.argv[1], 'r') as f:
    lines = f.readlines()
with open(sys.argv[1], 'w') as f:
    for line in lines:
        if line.startswith('pick ') and '{target_hash}' in line:
            f.write(line.replace('pick ', 'reword ', 1))
        else:
            f.write(line)
""")
            seq_editor_path = seq_editor.name

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as msg_editor:
            msg_editor.write(f"""#!{sys.executable}
import sys
with open(sys.argv[1], 'w') as f:
    f.write('''{new_message}''')
""")
            msg_editor_path = msg_editor.name

        os.chmod(seq_editor_path, 0o755)
        os.chmod(msg_editor_path, 0o755)

        env = os.environ.copy()
        env["GIT_SEQUENCE_EDITOR"] = seq_editor_path
        env["GIT_EDITOR"] = msg_editor_path

        subprocess.run(
            ["git", "rebase", "-i", f"{target_hash}^"],
            env=env,
            check=True,
            capture_output=True
        )

    except subprocess.CalledProcessError as e:
        subprocess.run(["git", "rebase", "--abort"], capture_output=True, check=False)
        raise RuntimeError(f"Automated rebase failed: {e.stderr.decode('utf-8') if e.stderr else str(e)}") from e

    finally:
        if seq_editor_path and os.path.exists(seq_editor_path):
            os.remove(seq_editor_path)
        if msg_editor_path and os.path.exists(msg_editor_path):
            os.remove(msg_editor_path)

def is_workspace_clean() -> bool:
    """Checks if the Git workspace is clean (no uncommitted changes).

    Uses `git status --porcelain` to check for any modified, staged, 
    or untracked files in a stable, machine-readable format.

    Returns:
        bool: True if the workspace is clean, False otherwise.

    Raises:
        RuntimeError: If the Git command fails to execute properly.
    """
    try:
        # --porcelain guarantees a stable output format across git versions
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        return len(result.stdout.strip()) == 0
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to check git status: {e.stderr}")

def stash_changes() -> None:
    """Stashes uncommitted changes securely with a descriptive message.

    Raises:
        RuntimeError: If the stash operation fails.
    """
    try:
        # Explicitly use 'push' with a message to identify our stash entry
        subprocess.run(
            ["git", "stash", "push", "-m", "chegi auto stash before sync"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to stash changes: {e.stderr}")

def pop_stash() -> None:
    """Pops the most recently stashed changes back into the workspace.

    Raises:
        RuntimeError: If the pop operation fails, typically due to conflicts.
    """
    try:
        subprocess.run(
            ["git", "stash", "pop"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        # git stash pop returns non-zero if a merge conflict occurs
        raise RuntimeError(f"Conflict or error popping stash:\n{e.stdout}\n{e.stderr}")

def pull_rebase() -> None:
    """Executes a git pull using rebase to maintain a linear history.

    Fetches from the remote and rebases current local commits on top of 
    the remote tracking branch.

    Raises:
        RuntimeError: If the pull/rebase fails due to network issues or conflicts.
    """
    try:
        subprocess.run(
            ["git", "pull", "--rebase"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        # Rebase stops and exits with non-zero on conflicts
        raise RuntimeError(f"Failed to pull changes (Conflict or network error):\n{e.stdout}\n{e.stderr}")

def push_changes() -> None:
    """Pushes local commits to the remote repository.

    Raises:
        RuntimeError: If the push operation is rejected or fails.
    """
    try:
        subprocess.run(
            ["git", "push"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to push changes: {e.stderr}")
