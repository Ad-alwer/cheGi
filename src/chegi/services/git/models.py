"""Dataclasses representing repository status and metadata."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class GitStatus:
    """Represents the extracted status of a single Git repository.

    Attributes:
        path (Path): The file system path to the Git repository.
        repo_name (str): The name of the repository (typically the folder name).
        branch (str): The current active branch of the repository.
        is_dirty (bool): True if there are uncommitted changes in the working directory.
        has_remote (bool): True if the repository has at least one remote configured.
        error (str): Any error message encountered during status extraction. Defaults to "".
        has_staged_files (bool): True if there are changes staged in the index. Defaults to False.
        security_status (Optional[str]): Findings from security scans, if any. Defaults to None.
    """

    path: Path
    repo_name: str
    branch: str
    is_dirty: bool
    has_remote: bool
    error: str = ""
    has_staged_files: bool = False
    security_status: Optional[str] = None
    status: Optional[str] = None
