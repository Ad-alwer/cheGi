"""Data models for GitHub repository metadata."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GitHubRepo:
    """Represents a GitHub repository.

    Attributes:
        name: Repository name (e.g. my-project).
        full_name: Full name with owner (e.g. username/my-project).
        html_url: Web URL for the repository.
        private: Whether the repository is private.
        default_branch: Default branch name (e.g. main, master).
        description: Optional repository description.
        language: Primary programming language.
        stargazers_count: Number of stars.
        forks_count: Number of forks.
        updated_at: ISO timestamp of last update.
        fork: Whether this is a forked repo.
    """

    name: str
    full_name: str
    html_url: str
    private: bool = False
    default_branch: str = "main"
    description: str = ""
    language: Optional[str] = None
    stargazers_count: int = 0
    forks_count: int = 0
    updated_at: str = ""
    fork: bool = False
