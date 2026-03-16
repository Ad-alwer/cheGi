import os
from pathlib import Path
from typing import Iterator, List

def find_git_repos(start_path: str, exclude_dirs: List[str]) -> Iterator[Path]:
    """
    Scans the given path to find directories containing a .git folder.
    
    Key features:
    1. Ignores directories listed in `exclude_dirs` (Performance boost).
    2. Smart Pruning: Once a git repo is found, it stops searching its subdirectories.
    """
    exclude_set = set(exclude_dirs)
    base_path = Path(start_path).resolve()
    
    if not base_path.exists() or not base_path.is_dir():
        # Will be replaced with Rich console error logging later
        print(f"Error: The directory '{start_path}' does not exist.")
        return

    # Use os.walk for fine-grained control over directory traversal
    for root, dirs, files in os.walk(base_path):
        current_dir = Path(root)
        
        # 1. Filter out blacklisted directories in-place
        # By modifying 'dirs', we tell os.walk to skip these completely
        dirs[:] = [d for d in dirs if d not in exclude_set]
        
        git_dir = current_dir / ".git"
        
        if git_dir.is_dir():
            # Found a repository! Yield it immediately.
            yield current_dir
            
            # 2. Smart Pruning
            # Since we found a repo, we shouldn't scan its internal folders.
            # Clearing 'dirs' tells os.walk to stop going deeper from here.
            dirs[:] = []
