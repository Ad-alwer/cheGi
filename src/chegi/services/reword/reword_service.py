import re
from typing import List, Optional, Tuple

from chegi.services.git.client import GitClient
from chegi.services.git.exceptions import GitCommandError

GIT_HASH_PATTERN = re.compile(r"^(HEAD|[0-9a-f]{7,40})$")


class RewordService:
    """Service layer for handling git commit rewording logic.

    Attributes:
        git_client (GitClient): The core Git client for executing commands.
    """

    def __init__(self, git_client: GitClient) -> None:
        """Initializes the RewordService.

        Args:
            git_client (GitClient): Instance of the core Git client.
        """
        self.git_client = git_client

    def calculate_pagination(
        self, last: Optional[int], start: Optional[int], end: Optional[int]
    ) -> Tuple[int, int]:
        """Calculates skip and limit values for git log based on user arguments.

        Args:
            last (Optional[int]): Number of recent commits to fetch.
            start (Optional[int]): Starting index.
            end (Optional[int]): Ending index.

        Returns:
            Tuple[int, int]: A tuple containing (skip, limit).

        Raises:
            ValueError: If start index is greater than or equal to end index.
        """
        if start is not None and end is not None:
            if start >= end:
                raise ValueError("--start must be less than --end.")
            return start, end - start

        if start is not None:
            return start, 10

        if end is not None:
            # Ensure skip doesn't go below zero
            skip = max(0, end - 10)
            return skip, end - skip

        # Default behavior: fallback to 'last' or default 10 commits
        return 0, last if last else 10

    def get_commits(self, skip: int, limit: int) -> List[str]:
        """Fetches a list of formatted commit hashes and messages.

        Args:
            skip (int): Number of commits to skip.
            limit (int): Maximum number of commits to fetch.

        Returns:
            List[str]: A list of strings in the format '<hash> <message>'.
        """
        try:
            output = self.git_client.run_command(
                [
                    "git",
                    "log",
                    f"--max-count={limit}",
                    f"--skip={skip}",
                    "--format=%h %s",
                ]
            )
            # Filter out empty lines
            return [line for line in output.split("\n") if line]
        except Exception as e:
            raise GitCommandError(f"Failed to fetch git history: {e}")

    @staticmethod
    def _validate_hash(target_hash: str) -> None:
        """Validates that the hash is a valid git hash or HEAD.

        Args:
            target_hash (str): The hash to validate.

        Raises:
            ValueError: If the hash format is invalid.
        """
        if not GIT_HASH_PATTERN.match(target_hash):
            raise ValueError(f"Invalid commit hash format: {target_hash}")

    def is_head(self, target_hash: str) -> bool:
        """Checks if the given commit hash is the current HEAD.

        Args:
            target_hash (str): The short hash of the target commit.

        Returns:
            bool: True if the target hash matches the HEAD hash.
        """
        self._validate_hash(target_hash)
        try:
            head_hash = self.git_client.run_command(
                ["git", "rev-parse", "--short", "HEAD"]
            )
            return target_hash == head_hash
        except Exception as e:
            raise GitCommandError(f"Failed to resolve HEAD: {e}")

    def get_commit_message(self, commit_hash: str) -> str:
        """Retrieves the full commit message for a specific commit.

        Args:
            commit_hash (str): The hash of the target commit.

        Returns:
            str: The raw commit message.
        """
        self._validate_hash(commit_hash)
        try:
            return self.git_client.run_command(
                ["git", "log", "--format=%B", "-n", "1", commit_hash]
            )
        except Exception as e:
            raise GitCommandError(
                f"Failed to fetch commit message for {commit_hash}: {e}"
            )

    def amend_head(self, new_message: str) -> None:
        """Modifies the message of the most recent commit (HEAD).

        Args:
            new_message (str): The new commit message.
        """
        try:
            self.git_client.run_command(["git", "commit", "--amend", "-m", new_message])
        except Exception as e:
            raise GitCommandError(f"Failed to amend HEAD commit: {e}")

    def perform_automated_rebase(self, target_hash: str, new_message: str) -> None:
        """Performs an interactive rebase automatically to modify an older commit.

        Args:
            target_hash (str): The short hash of the commit to modify.
            new_message (str): The new commit message.
        """
        self._validate_hash(target_hash)
        try:
            # Use sed as the sequence editor to automatically change 'pick' to 'reword'
            env = {
                "GIT_SEQUENCE_EDITOR": f"sed -i -e 's/^pick {target_hash}/reword {target_hash}/'"
            }

            self.git_client.run_command(
                ["git", "rebase", "-i", f"{target_hash}~1"], env=env
            )
            self.git_client.run_command(["git", "commit", "--amend", "-m", new_message])
            self.git_client.run_command(["git", "rebase", "--continue"])
        except Exception as e:
            # Attempt to safely abort the rebase if anything fails
            self.git_client.run_command(["git", "rebase", "--abort"], check=False)
            raise GitCommandError(f"Automated rebase failed: {e}")
