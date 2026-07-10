"""Exceptions specific to the Reword service."""

from chegi.services.git.exceptions import GitCoreError


class RewordError(GitCoreError):
    """Base exception for errors that occur during the reword process."""
    pass
