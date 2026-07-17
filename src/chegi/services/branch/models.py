"""Data models for the branch service."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BranchInfo:
    """Represents a Git branch with its metadata.

    Attributes:
        name: The branch name.
        is_current: Whether this is the currently checked-out branch.
        is_remote: Whether this is a remote-tracking branch.
        last_commit_hash: The abbreviated hash of the latest commit.
        last_commit_message: The subject of the latest commit.
        last_commit_author: The author name of the latest commit.
        last_commit_date: The relative date of the latest commit.
        ahead: Number of commits ahead of the upstream.
        behind: Number of commits behind the upstream.
        upstream: The upstream tracking branch, if any.
    """

    name: str
    is_current: bool = False
    is_remote: bool = False
    last_commit_hash: Optional[str] = None
    last_commit_message: Optional[str] = None
    last_commit_author: Optional[str] = None
    last_commit_date: Optional[str] = None
    ahead: int = 0
    behind: int = 0
    upstream: Optional[str] = None
