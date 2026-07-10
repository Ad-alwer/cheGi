"""Service for handling Git synchronization operations (pull, push, stash)."""

from chegi.services.git.client import GitClient
from chegi.services.sync.exceptions import SyncError


class SyncService:
    """Service to handle automated syncing of the Git repository.

    Attributes:
        git_client (GitClient): The core Git client instance.
    """

    def __init__(self, git_client: GitClient):
        """Initializes the SyncService.

        Args:
            git_client (GitClient): The core Git client instance.
        """
        self.git_client = git_client

    def stash_changes(self) -> None:
        """Stashes any uncommitted changes in the repository.

        Raises:
            GitCommandError: If the stash command fails.
        """
        self.git_client.run_command(["git", "stash", "push", "-m", "cheGi auto-stash"])

    def pop_stash(self) -> None:
        """Pops the most recent stash.

        Raises:
            GitCommandError: If popping the stash fails (e.g., due to conflicts).
        """
        self.git_client.run_command(["git", "stash", "pop"])

    def pull_rebase(self) -> None:
        """Pulls changes from the remote using rebase.

        Raises:
            SyncError: If the pull with rebase fails, it aborts the rebase and raises this error.
        """
        try:
            self.git_client.run_command(["git", "pull", "--rebase"])
        except Exception as e:
            self.git_client.run_command(["git", "rebase", "--abort"], check=False)
            raise SyncError(f"Pull rebase failed. Rebase aborted. Details: {e}") from e

    def push_changes(self) -> None:
        """Pushes committed changes to the remote repository.

        Raises:
            SyncError: If the push command fails.
        """
        try:
            self.git_client.run_command(["git", "push"])
        except Exception as e:
            raise SyncError(f"Push failed. Details: {e}") from e
