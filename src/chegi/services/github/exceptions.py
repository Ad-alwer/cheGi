"""Exceptions for GitHub service."""


class GitHubError(Exception):
    """Base exception for GitHub operations."""


class GitHubAuthError(GitHubError):
    """Raised when GitHub authentication fails."""


class RepoExistsError(GitHubError):
    """Raised when a repository with the same name already exists."""
