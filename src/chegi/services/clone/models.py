"""Data models for the clone service."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class CloneSource(Enum):
    """Where the repository URL comes from."""

    OWN_REPO = "own"
    EXTERNAL_URL = "url"


class TargetLocation(Enum):
    """How the target directory is determined."""

    HERE = "here"
    NEW_FOLDER = "folder"
    SPECIFIC_PATH = "path"


@dataclass
class CloneConfig:
    """Configuration for a clone operation."""

    url: str
    source: CloneSource
    target_dir: Path
    repo_name: str
    branch: Optional[str] = None
    depth: Optional[int] = None
    submodules: bool = True
    gitignore: bool = True
    chegi: bool = True
    technologies: List[str] = field(default_factory=list)


@dataclass
class CloneResult:
    """Result of a clone operation."""

    target_dir: Path
    repo_name: str
    detected_techs: List[str] = field(default_factory=list)
    had_submodules: bool = False
    submodules_inited: List[str] = field(default_factory=list)
    gitignore_was_missing: bool = False
    gitignore_created: bool = False
    chegi_created: bool = False
    default_branch: str = "main"
