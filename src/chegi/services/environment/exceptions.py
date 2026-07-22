"""Custom exceptions for environment manager operations."""


class EnvManagerError(Exception):
    """Base exception for all EnvManager related errors."""

    pass


class NoEnvironmentsProvidedError(EnvManagerError):
    """Raised when no environment names are provided for gitignore generation."""

    pass


class EnvironmentNotFoundError(EnvManagerError):
    """Raised when a requested environment cannot be found in the database."""

    pass
