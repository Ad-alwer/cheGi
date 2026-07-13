"""Custom exceptions for the init/project module."""


class InitError(Exception):
    """Base exception for all init/project-related errors."""

    pass


class ProjectNotFoundError(InitError):
    """Raised when no .chegi/ project directory is found."""

    pass
