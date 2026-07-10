"""Exceptions specific to the Sync service."""

from chegi.services.git.exceptions import GitCoreError


class SyncError(GitCoreError):
    """Base exception for errors that occur during the sync process."""
    pass
