"""Data models for GitHub repository metadata."""

from dataclasses import dataclass


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
    """

    name: str
    full_name: str
    html_url: str
    private: bool = False
    default_branch: str = "main"
    description: str = ""
