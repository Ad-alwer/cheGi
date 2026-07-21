"""Service for cloning repositories with smart defaults."""

import re
from pathlib import Path
from typing import List

from chegi.services.clone.constants import DETECTION_FILES, DETECTION_RULES
from chegi.services.clone.exceptions import (
    CloneError,
    CloneTargetExistsError,
    CloneUrlError,
)
from chegi.services.clone.models import (
    CloneConfig,
    CloneResult,
)
from chegi.services.environment import EnvManager
from chegi.services.git.client import GitClient
from chegi.services.git.exceptions import GitCommandError, GitNotInstalledError
from chegi.services.init import InitService

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

    def __init__(self, config: CloneConfig) -> None:
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
        config = self.config
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

        # Submodule init
        if config.submodules and (result.target_dir / ".gitmodules").exists():
            result.had_submodules = True
            try:
                output = git_client.submodule_update(recursive=True)
                result.submodules_inited = _parse_submodule_output(output)
            except (GitCommandError, GitNotInstalledError):
                result.submodules_inited = []

        # .gitignore generation
        if config.gitignore:
            gitignore_path = result.target_dir / ".gitignore"
            if not gitignore_path.exists():
                result.gitignore_was_missing = True
                techs = config.technologies or result.detected_techs
                if techs:
                    try:
                        env_mgr = EnvManager()
                        env_mgr.generate_gitignore(techs, str(result.target_dir))
                        result.gitignore_created = True
                    except Exception:
                        result.gitignore_created = False

        # .chegi/ setup
        if config.chegi:
            try:
                InitService.create_project_directory(result.target_dir)
                result.chegi_created = True
            except Exception:
                result.chegi_created = False

        return result

    def _clone_repo(self) -> CloneResult:
        """Clones the repository.

        Returns:
            A partial CloneResult with basic fields filled.

        Raises:
            CloneError: If the clone operation fails.
            CloneTargetExistsError: If target exists and is not empty.
        """
        config = self.config
        target = config.target_dir

        # Safety check: warn if target exists and is not empty
        if target.exists() and any(target.iterdir()):
            raise CloneTargetExistsError(
                f"Target directory already exists and is not empty: {target}"
            )

        parent = target.parent
        parent.mkdir(parents=True, exist_ok=True)

        try:
            git_client = GitClient(parent)
            git_client.clone(
                url=config.url,
                target_dir=target,
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


def _parse_submodule_output(output: str) -> List[str]:
    """Parses git submodule update output to extract submodule names.

    Args:
        output: The raw stdout from git submodule update.

    Returns:
        List of submodule paths that were initialized.
    """
    if not output:
        # When no submodules need updating, output may be empty
        return []
    # Typical output lines: "Cloning into '/path/to/submodule'..."
    names: List[str] = []
    for line in output.splitlines():
        if "Cloning into" in line:
            parts = line.split("'")
            if len(parts) >= 2:
                path = parts[1]
                name = Path(path).name
                if name not in names:
                    names.append(name)
    # If no Cloning lines, maybe all cached; still return something
    if not names:
        return ["<unknown>"]
    return names
