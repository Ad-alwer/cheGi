"""Core Git client for executing Git commands securely."""

import os
import subprocess
from pathlib import Path
from typing import List, Optional

from chegi.services.git.exceptions import GitCommandError, GitNotInstalledError


class GitClient:
    """Client for running Git commands in a specified repository.

    Attributes:
        repo_path (Path): The path to the Git repository.
    """

    def __init__(self, repo_path: Path):
        """Initializes the GitClient.

        Args:
            repo_path (Path): The local directory path of the git repository.
        """
        self.repo_path = repo_path

    def is_valid_repo(self) -> bool:
        """Checks if the repository path is a valid Git repository.

        Returns:
            bool: True if it is a valid Git repo, False otherwise.
        """
        try:
            self.run_command(["git", "rev-parse", "--is-inside-work-tree"])
            return True
        except (GitCommandError, GitNotInstalledError):
            return False

    def run_command(
        self,
        command: List[str],
        check: bool = True,
        env: Optional[dict] = None,
        cwd: Optional[Path] = None,
    ) -> str:
        """Executes a git command securely using subprocess.

        Args:
            command (List[str]): The git command and its arguments as a list.
            check (bool, optional): Whether to raise an exception on command failure. Defaults to True.
            env (dict, optional): Environment variables to pass to the subprocess. Defaults to None.
            cwd (Path, optional): Working directory. Defaults to self.repo_path.

        Returns:
            str: The stripped standard output of the command.

        Raises:
            GitCommandError: If the command returns a non-zero exit code and `check` is True.
            GitNotInstalledError: If the git executable is not found.
        """
        try:
            result = subprocess.run(
                command,
                cwd=str(cwd) if cwd is not None else self.repo_path,
                capture_output=True,
                text=True,
                check=check,
                env={**os.environ.copy(), **(env or {})},
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise GitCommandError(
                f"Command '{' '.join(command)}' failed with exit code {e.returncode}.\n"
                f"Error: {e.stderr.strip()}"
            ) from e
        except FileNotFoundError:
            raise GitNotInstalledError("Git executable not found. Is Git installed?")

    def clone(
        self,
        url: str,
        target_dir: Path,
        branch: Optional[str] = None,
        depth: Optional[int] = None,
    ) -> str:
        """Clones a remote repository into a local directory.

        Args:
            url: The repository URL.
            target_dir: The target directory to clone into.
            branch: Optional branch to clone.
            depth: Optional shallow clone depth.

        Returns:
            The git clone output.

        Raises:
            GitCommandError: If the clone fails.
            GitNotInstalledError: If git is not installed.
        """
        cmd: List[str] = ["git", "clone"]
        if branch:
            cmd.extend(["-b", branch])
        if depth:
            cmd.extend(["--depth", str(depth)])
        cmd.append(url)
        cmd.append(str(target_dir))

        target_dir.parent.mkdir(parents=True, exist_ok=True)
        return self.run_command(cmd, cwd=str(target_dir.parent))

    def check_git_installation(self) -> bool:
        """Ensures Git is installed on the system.

        Returns:
            bool: True if Git is installed.

        Raises:
            GitNotInstalledError: If Git is not accessible.
        """
        try:
            self.run_command(["git", "--version"])
            return True
        except GitNotInstalledError:
            raise

    def is_workspace_clean(self) -> bool:
        """Checks if the Git working directory is clean.

        Returns:
            bool: True if there are no uncommitted changes, False otherwise.
        """
        output = self.run_command(["git", "status", "--porcelain"])
        return len(output) == 0

    def submodule_update(self, recursive: bool = True) -> str:
        """Initializes and updates submodules.

        Args:
            recursive: Whether to init submodules recursively.

        Returns:
            The git submodule command output.

        Raises:
            GitCommandError: If the submodule update fails.
            GitNotInstalledError: If git is not installed.
        """
        cmd = ["git", "submodule", "update", "--init"]
        if recursive:
            cmd.append("--recursive")
        return self.run_command(cmd)

    def commit_file(self, file_path: str, commit_msg: str) -> str:
        """Adds and commits a specific file to the repository.

        Args:
            file_path (str): The name or relative path of the file to add.
            commit_msg (str): The commit message.

        Returns:
            str: The commit message used.

        Raises:
            GitCommandError: If the git add or commit commands fail.
            ValueError: If the file_path or commit_msg contain dangerous patterns.
        """
        if file_path.startswith("-"):
            raise ValueError(f"File path must not start with '-': {file_path}")
        if "\n" in commit_msg:
            raise ValueError("Commit message must not contain newlines")
        self.run_command(["git", "add", file_path])
        self.run_command(["git", "commit", "-m", commit_msg])
        return commit_msg
