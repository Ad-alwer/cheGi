"""Data models for the new project service."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class NewProjectConfig:
    """Configuration for creating a new project.

    Attributes:
        name: Project name (used for directory and README).
        path: Parent directory path. Defaults to current working directory.
        template: Optional predefined template name (python, node, rust, etc.).
        license_type: Optional license type (mit, apache, gpl, etc.).
        technologies: List of technologies for .gitignore generation.
        skip_readme: If True, skip README.md generation.
        skip_gitignore: If True, skip .gitignore generation.
        skip_chegi: If True, skip .chegi/ directory creation.
        yes: If True, non-interactive mode (use defaults).
    """

    name: str
    path: Path = field(default_factory=Path.cwd)
    template: Optional[str] = None
    license_type: Optional[str] = None
    technologies: List[str] = field(default_factory=list)
    skip_readme: bool = False
    skip_gitignore: bool = False
    skip_chegi: bool = False
    yes: bool = False


@dataclass
class NewProjectResult:
    """Result of creating a new project.

    Attributes:
        project_path: The full path to the created project directory.
        files_created: List of files that were created.
        commit_hash: The SHA of the initial commit, if made.
        is_successful: Whether the project was created successfully.
    """

    project_path: Path
    files_created: List[str] = field(default_factory=list)
    commit_hash: Optional[str] = None
    is_successful: bool = True
