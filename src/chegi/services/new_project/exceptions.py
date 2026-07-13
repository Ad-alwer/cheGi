"""Custom exceptions for the new project service."""


class NewProjectError(Exception):
    """Base exception for new project operations."""

    pass


class ProjectAlreadyExistsError(NewProjectError):
    """Raised when the target directory already exists."""

    pass


class GitInitError(NewProjectError):
    """Raised when git init fails."""

    pass


class ProjectCreationError(NewProjectError):
    """Raised when project creation fails."""

    pass
