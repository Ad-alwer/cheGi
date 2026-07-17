"""Exceptions for the branch service."""


class BranchError(Exception):
    """Base exception for branch-related errors."""

    pass


class ProtectedBranchError(BranchError):
    """Raised when attempting to delete a protected branch."""

    pass
