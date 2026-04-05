class GitCoreError(Exception):
    """Base exception for all Git-related errors."""
    pass

class GitCommandError(GitCoreError):
    """Raised when a git command fails."""
    pass

class GitNotInstalledError(GitCoreError):
    """Raised when git is not found on the system."""
    pass
