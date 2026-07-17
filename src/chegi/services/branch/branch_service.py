"""Service for managing Git branches."""

from pathlib import Path
from typing import List, Optional

from chegi.services.branch.constants import PROTECTED_BRANCHES
from chegi.services.branch.exceptions import BranchError, ProtectedBranchError
from chegi.services.branch.models import BranchInfo
from chegi.services.git.client import GitClient
from chegi.services.git.exceptions import GitCommandError, GitNotInstalledError


class BranchService:
    """Service for common Git branch operations.

    Provides create, list, switch, rename, delete, merge, push,
    and sync operations using GitClient.
    """

    def __init__(self, repo_path: Optional[Path] = None):
        """Initializes the BranchService.

        Args:
            repo_path: Path to the Git repository. Defaults to current directory.
        """
        self.repo_path = repo_path or Path.cwd()
        self._git = GitClient(self.repo_path)

    def get_current_branch(self) -> str:
        """Returns the name of the currently checked-out branch.

        Returns:
            The current branch name.

        Raises:
            BranchError: If the branch name cannot be determined.
        """
        try:
            return self._git.run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        except (GitCommandError, GitNotInstalledError) as e:
            raise BranchError(f"Failed to get current branch: {e}") from e

    def list_branches(self, remote: bool = False) -> List[BranchInfo]:
        """Lists all local (or remote) branches with metadata.

        Args:
            remote: If True, list remote-tracking branches instead of local.

        Returns:
            A list of BranchInfo objects.
        """
        current = self.get_current_branch()

        if remote:
            fmt = (
                "%(refname:short)%09%(objectname:short)%09"
                "%(subject)%09%(authorname)%09%(upstream:track)"
            )
            cmd = ["git", "branch", "--remote", "--format", fmt]
        else:
            fmt = (
                "%(refname:short)%09%(objectname:short)%09"
                "%(subject)%09%(authorname)%09%(upstream:track)"
            )
            cmd = ["git", "branch", "--format", fmt]

        try:
            output = self._git.run_command(cmd)
        except (GitCommandError, GitNotInstalledError) as e:
            raise BranchError(f"Failed to list branches: {e}") from e

        if not output:
            return []

        branches: List[BranchInfo] = []
        for line in output.splitlines():
            parts = line.split("\t")
            name = parts[0]
            if remote and not name.startswith("origin/"):
                continue
            if remote:
                name = name[len("origin/") :]
            commit_hash = parts[1] if len(parts) > 1 else None
            message = parts[2] if len(parts) > 2 else None
            author = parts[3] if len(parts) > 3 else None
            upstream = parts[4] if len(parts) > 4 else None

            branches.append(
                BranchInfo(
                    name=name,
                    is_current=(name == current),
                    is_remote=remote,
                    last_commit_hash=commit_hash,
                    last_commit_message=message,
                    last_commit_author=author,
                    upstream=upstream,
                )
            )

        return branches

    def create_branch(self, name: str, base: Optional[str] = None) -> None:
        """Creates a new branch from an optional base.

        Args:
            name: The new branch name.
            base: The branch or commit to create from. Defaults to HEAD.

        Raises:
            BranchError: If the branch cannot be created.
        """
        if not name or not name.strip():
            raise BranchError("Branch name cannot be empty.")

        cmd = ["git", "branch", name]
        if base:
            cmd.append(base)

        try:
            self._git.run_command(cmd)
        except (GitCommandError, GitNotInstalledError) as e:
            raise BranchError(f"Failed to create branch '{name}': {e}") from e

    def switch_branch(self, name: str) -> None:
        """Switches to an existing branch.

        Args:
            name: The branch to switch to.

        Raises:
            BranchError: If the switch fails.
        """
        try:
            self._git.run_command(["git", "checkout", name])
        except (GitCommandError, GitNotInstalledError) as e:
            raise BranchError(f"Failed to switch to '{name}': {e}") from e

    def delete_branch(self, name: str, force: bool = False) -> None:
        """Deletes a branch, respecting protected branches.

        Args:
            name: The branch to delete.
            force: If True, force-delete even if unmerged.

        Raises:
            ProtectedBranchError: If the branch is protected.
            BranchError: If the deletion fails.
        """
        if name in PROTECTED_BRANCHES:
            raise ProtectedBranchError(f"Cannot delete protected branch: '{name}'")

        cmd = ["git", "branch", "--delete"]
        if force:
            cmd.append("--force")
        cmd.append(name)

        try:
            self._git.run_command(cmd)
        except (GitCommandError, GitNotInstalledError) as e:
            raise BranchError(f"Failed to delete branch '{name}': {e}") from e

    def rename_branch(self, old: str, new: str) -> None:
        """Renames a branch.

        Args:
            old: The current branch name.
            new: The new branch name.

        Raises:
            BranchError: If the rename fails.
        """
        if not new or not new.strip():
            raise BranchError("New branch name cannot be empty.")

        try:
            self._git.run_command(["git", "branch", "--move", old, new])
        except (GitCommandError, GitNotInstalledError) as e:
            raise BranchError(f"Failed to rename '{old}' to '{new}': {e}") from e

    def merge_branch(self, source: str, target: Optional[str] = None) -> str:
        """Merges a source branch into the current (or specified) target.

        Args:
            source: The branch to merge from.
            target: The branch to merge into. Defaults to current branch.

        Returns:
            The merge command output.

        Raises:
            BranchError: If the merge fails.
        """
        if target:
            try:
                self._git.run_command(["git", "checkout", target])
            except (GitCommandError, GitNotInstalledError) as e:
                raise BranchError(f"Failed to checkout target '{target}': {e}") from e

        try:
            return self._git.run_command(["git", "merge", source])
        except (GitCommandError, GitNotInstalledError) as e:
            raise BranchError(f"Failed to merge '{source}': {e}") from e

    def get_merge_preview(self, source: str, target: str) -> List[str]:
        """Returns the list of commits that would be merged.

        Args:
            source: The source branch.
            target: The target branch.

        Returns:
            List of commit descriptions (hash + subject).

        Raises:
            BranchError: If the log command fails.
        """
        try:
            output = self._git.run_command(
                ["git", "log", "--oneline", f"{target}..{source}"]
            )
        except (GitCommandError, GitNotInstalledError) as e:
            raise BranchError(f"Failed to get merge preview: {e}") from e

        if not output:
            return []
        return output.splitlines()

    def push_branch(self, name: str, remote: str = "origin") -> None:
        """Pushes a branch to a remote.

        Args:
            name: The branch to push.
            remote: The remote name. Defaults to 'origin'.

        Raises:
            BranchError: If the push fails.
        """
        try:
            self._git.run_command(["git", "push", remote, name])
        except (GitCommandError, GitNotInstalledError) as e:
            raise BranchError(f"Failed to push '{name}' to '{remote}': {e}") from e

    def push_and_delete(self, name: str, remote: str = "origin") -> None:
        """Pushes a branch to remote, then deletes the local branch.

        Args:
            name: The branch to push and delete.
            remote: The remote name. Defaults to 'origin'.
        """
        self.push_branch(name, remote)
        self.delete_branch(name, force=True)

    def sync_branches(self, remote: str = "origin") -> List[str]:
        """Prunes remote-tracking branches and returns deleted ones.

        Args:
            remote: The remote name. Defaults to 'origin'.

        Returns:
            List of branch names that were pruned.

        Raises:
            BranchError: If the prune command fails.
        """
        try:
            output = self._git.run_command(
                ["git", "remote", "prune", remote, "--dry-run"]
            )
        except (GitCommandError, GitNotInstalledError) as e:
            raise BranchError(f"Failed to prune remote '{remote}': {e}") from e

        pruned: List[str] = []
        if output:
            for line in output.splitlines():
                if "* [pruned]" in line or "[pruned]" in line:
                    parts = line.split()
                    if parts:
                        name = parts[-1].strip()
                        if name:
                            pruned.append(name)

        try:
            self._git.run_command(["git", "remote", "prune", remote])
        except (GitCommandError, GitNotInstalledError) as e:
            raise BranchError(f"Failed to prune remote '{remote}': {e}") from e

        return pruned

    def get_branch_info(self, name: str) -> BranchInfo:
        """Returns detailed information about a specific branch.

        Args:
            name: The branch name.

        Returns:
            A BranchInfo with ahead/behind, upstream, and last commit details.

        Raises:
            BranchError: If the branch does not exist or info cannot be retrieved.
        """
        current = self.get_current_branch()
        is_current = name == current

        try:
            upstream = self._git.run_command(
                ["git", "rev-parse", "--abbrev-ref", f"{name}@{{upstream}}"],
                check=False,
            )
        except (GitCommandError, GitNotInstalledError):
            upstream = None

        if not upstream or "fatal" in upstream.lower():
            upstream = None

        ahead = 0
        behind = 0
        if upstream:
            try:
                count_output = self._git.run_command(
                    [
                        "git",
                        "rev-list",
                        "--left-right",
                        "--count",
                        f"{name}...{upstream}",
                    ]
                )
                parts = count_output.split()
                if len(parts) >= 2:
                    ahead = int(parts[0])
                    behind = int(parts[1])
            except (GitCommandError, GitNotInstalledError, ValueError):
                pass

        last_commit_hash = None
        last_commit_message = None
        last_commit_author = None
        last_commit_date = None

        try:
            log_output = self._git.run_command(
                ["git", "log", "-1", "--format=%h%n%s%n%an%n%ar", name]
            )
            if log_output:
                log_lines = log_output.splitlines()
                if len(log_lines) >= 1:
                    last_commit_hash = log_lines[0]
                if len(log_lines) >= 2:
                    last_commit_message = log_lines[1]
                if len(log_lines) >= 3:
                    last_commit_author = log_lines[2]
                if len(log_lines) >= 4:
                    last_commit_date = log_lines[3]
        except (GitCommandError, GitNotInstalledError):
            pass

        return BranchInfo(
            name=name,
            is_current=is_current,
            last_commit_hash=last_commit_hash,
            last_commit_message=last_commit_message,
            last_commit_author=last_commit_author,
            last_commit_date=last_commit_date,
            ahead=ahead,
            behind=behind,
            upstream=upstream,
        )

    def get_local_branch_names(self) -> List[str]:
        """Returns a list of local branch names (without metadata).

        Returns:
            List of local branch names.
        """
        try:
            output = self._git.run_command(
                ["git", "branch", "--format", "%(refname:short)"]
            )
        except (GitCommandError, GitNotInstalledError) as e:
            raise BranchError(f"Failed to list branches: {e}") from e

        if not output:
            return []
        return output.splitlines()
