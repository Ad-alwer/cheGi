"""Service for cloning repositories with smart defaults."""

import re
from pathlib import Path
from typing import List

from chegi.services.clone.constants import DETECTION_FILES, DETECTION_RULES
from chegi.services.clone.exceptions import CloneError, CloneUrlError
from chegi.services.clone.models import (
    CloneConfig,
    CloneResult,
)
from chegi.services.git.client import GitClient
from chegi.services.git.exceptions import GitCommandError, GitNotInstalledError

# Regex to detect shorthand user/repo format
_SHORTHAND_RE = re.compile(r"^[\w.-]+/[\w.-]+$")


def parse_url(value: str) -> str:
    """Parses a user-provided URL or shorthand into a full Git URL.

    Supports:
      - user/repo -> https://github.com/user/repo.git
      - https://...  -> unchanged
      - git@...     -> unchanged
      - git://...   -> unchanged

    Args:
        value: The raw URL or shorthand.

    Returns:
        A fully qualified Git remote URL.

    Raises:
        CloneUrlError: If the value is not a valid URL or shorthand.
    """
    value = value.strip()

    if not value:
        raise CloneUrlError("URL cannot be empty.")

    # Already a full URL
    if value.startswith(("https://", "http://", "git@", "git://", "ssh://")):
        return value

    # user/repo shorthand
    if _SHORTHAND_RE.match(value):
        return f"https://github.com/{value}.git"

    raise CloneUrlError(
        f"Invalid repository URL: '{value}'. "
        "Use a full URL (https://... / git@...) or user/repo shorthand."
    )


def _target_dir_name(url: str) -> str:
    """Extracts a human-friendly directory name from a Git URL.

    Args:
        url: The repository URL.

    Returns:
        The repository name without .git suffix.
    """
    name = url.rstrip("/").rsplit("/", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name


class CloneService:
    """Service for cloning repositories and setting up projects.

    Provides clone, submodule init, .gitignore generation, and .chegi/
    initialization in a single workflow.
    """

    def __init__(self, config: CloneConfig):
        """Initializes the CloneService.

        Args:
            config: The clone configuration.
        """
        self.config = config

    def execute(self) -> CloneResult:
        """Runs the full clone workflow.

        Returns:
            The clone result with details about what was created.

        Raises:
            CloneError: If any step of the clone process fails.
        """
        result = self._clone_repo()

        # Detect default branch
        try:
            git_client = GitClient(result.target_dir)
            branch = git_client.run_command(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"]
            )
            result.default_branch = branch or "main"
        except (GitCommandError, GitNotInstalledError):
            result.default_branch = "main"

        # Smart-detect technologies
        result.detected_techs = self._smart_detect_techs(result.target_dir)

        return result

    def _clone_repo(self) -> CloneResult:
        """Clones the repository.

        Returns:
            A partial CloneResult with basic fields filled.

        Raises:
            CloneError: If the clone operation fails.
        """
        config = self.config
        parent = config.target_dir.parent
        parent.mkdir(parents=True, exist_ok=True)

        try:
            git_client = GitClient(parent)
            git_client.clone(
                url=config.url,
                target_dir=config.target_dir,
                branch=config.branch,
                depth=config.depth,
            )
        except GitCommandError as e:
            raise CloneError(f"Failed to clone repository: {e}") from e
        except GitNotInstalledError as e:
            raise CloneError("Git is not installed.") from e

        return CloneResult(
            target_dir=config.target_dir,
            repo_name=config.repo_name,
        )

    @staticmethod
    def _smart_detect_techs(target_dir: Path) -> List[str]:
        """Scans the cloned directory for recognizable project files.

        Checks for files like package.json, Cargo.toml, etc. to
        automatically suggest .gitignore technologies.

        Args:
            target_dir: The cloned repository path.

        Returns:
            List of detected technology names (lowercase).
        """
        detected: List[str] = []
        for filename in DETECTION_FILES:
            if (target_dir / filename).exists():
                tech = DETECTION_RULES[filename]
                if tech not in detected:
                    detected.append(tech)
        return detected
