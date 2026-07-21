"""
Custom exceptions for the configuration module.
"""


class ConfigError(Exception):
    """Base exception for all configuration-related errors."""

    pass


class UnsupportedPackageManagerError(ConfigError):
    """Raised when an unsupported package manager is specified for mirrors."""

    pass


class InvalidMirrorFormatError(ConfigError):
    """Raised when the mirror string format is invalid."""

    pass


class InvalidConfigFormatError(ConfigError):
    """Raised when the config JSON structure is invalid."""

    pass
