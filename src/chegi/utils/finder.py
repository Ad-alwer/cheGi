import os
from pathlib import Path
from typing import Iterator

from chegi.config import ChegiConfig


def find_git_repos(start_path: str, config: ChegiConfig) -> Iterator[Path]:
    """Scans directories recursively to find Git repositories.

    Uses the provided configuration to limit depth, exclude specific
    directories, and perform smart pruning to stop traversing deeper 
    once a Git repository is found.

    Args:
        start_path (str): The base directory where the scan begins.
        config (ChegiConfig): Configuration object containing settings
            like max_depth and exclude_dirs.

    Yields:
        Path: The absolute path to a discovered Git repository.

    Raises:
        NotADirectoryError: If the start_path is not a valid directory.
    """
    base_path = Path(start_path).resolve()

    if not base_path.is_dir():
        raise NotADirectoryError(
            f"Error: '{base_path}' does not exist or is not a directory."
        )

    exclude_set = set(config.exclude_dirs)

    for root, dirs, files in os.walk(base_path):
        current_path = Path(root)

        # Calculate depth relative to the starting path
        try:
            rel_path = current_path.relative_to(base_path)
            depth = len(rel_path.parts)
        except ValueError:
            depth = 0

        # Enforce max depth limit
        if depth >= config.max_depth:
            dirs.clear()
            continue

        # Check for Git repository indicator
        if ".git" in dirs or ".git" in files:
            yield current_path
            # Smart pruning: stop scanning subdirectories of this repo
            dirs.clear()
            continue

        # Filter out excluded and hidden directories
        dirs[:] = [d for d in dirs if d not in exclude_set and not d.startswith(".")]
