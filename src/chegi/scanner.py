import os
from pathlib import Path
from typing import Iterator

from chegi.config import ChegiConfig

def find_git_repos(start_path: str, config: ChegiConfig) -> Iterator[Path]:
    """Scans directories recursively to find Git repositories.

    It uses the provided configuration object to limit depth and 
    exclude specific directories. It stops traversing deeper if a 
    Git repository is found (smart pruning).

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
        raise NotADirectoryError(f"Error: '{base_path}' does not exist or is not a directory.")

    exclude_set = set(config.exclude_dirs)

    for root, dirs, files in os.walk(base_path):
        current_path = Path(root)
        
        # Calculate depth relative to the starting path
        try:
            rel_path = current_path.relative_to(base_path)
            depth = len(rel_path.parts)
        except ValueError:
            depth = 0
            
        # If the current depth has reached or exceeded max_depth, 
        # we do not check it for a repo and we do not go any deeper.
        if depth >= config.max_depth:
            dirs.clear()  
            continue

        # Check if current directory is a Git repository
        if ".git" in dirs or ".git" in files:
            yield current_path
            # Smart pruning: Do not scan subdirectories of a discovered repository
            dirs.clear()  
            continue

        # Prune excluded directories and standard hidden folders (except .git)
        dirs[:] = [
            d for d in dirs 
            if d not in exclude_set and not d.startswith('.')
        ]
