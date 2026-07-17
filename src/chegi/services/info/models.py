"""Data models for the info service."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class LastCommit:
    hash: str
    message: str
    author: str
    date: str


@dataclass
class InfoReport:
    path: Path
    is_git_repo: bool

    # Git
    branch: Optional[str] = None
    remote_name: Optional[str] = None
    remote_url: Optional[str] = None
    ahead: int = 0
    behind: int = 0

    # Changes
    staged: int = 0
    modified: int = 0
    untracked: int = 0

    # Commit
    last_commit: Optional[LastCommit] = None
    contributor_count: int = 0

    # Security & Config
    has_sensitive_files: bool = False
    sensitive_file_count: int = 0
    has_hooks: bool = False
    has_chegi_dir: bool = False
    git_identity_set: bool = False

    # Project
    latest_tag: Optional[str] = None
    commits_since_tag: int = 0
    stash_count: int = 0

    # Partial failure tracking
    errors: Dict[str, str] = field(default_factory=dict)
