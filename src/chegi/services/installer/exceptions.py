"""Custom exceptions for system installation failures."""

class InstallerError(Exception):
    """Base exception for all installer-related errors."""

    pass


class TargetNotSupportedError(InstallerError):
    """Raised when the requested environment or target is not supported/found."""

    pass


class InstallationFailedError(InstallerError):
    """Raised when a system installation command fails."""

    pass


class UserAbortedSetupError(InstallerError):
    """Raised when the user cancels the setup process."""

    pass
