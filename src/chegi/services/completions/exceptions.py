"""Exceptions for the completions service."""


class CompletionsError(Exception):
    """Base exception for completions-related errors."""

    pass


class UnsupportedShellError(CompletionsError):
    """Raised when an unsupported shell is requested."""

    pass


class InstallationError(CompletionsError):
    """Raised when the completion script cannot be installed."""

    pass
