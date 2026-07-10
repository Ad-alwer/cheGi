class ScannerError(Exception):
    """Base exception for all scanner-related errors."""

    pass


class InvalidDirectoryError(ScannerError):
    """Raised when the provided directory path is invalid or does not exist."""

    pass
