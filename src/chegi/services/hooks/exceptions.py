"""Custom exceptions for the hooks service."""


class HookError(Exception):
    """Base exception for hook operations."""

    pass


class HookInstallError(HookError):
    """Raised when hook installation fails."""

    pass


class HookRemoveError(HookError):
    """Raised when hook removal fails."""

    pass
