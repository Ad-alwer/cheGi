"""Installer service for managing system-level tool installations."""

from .exceptions import (
    InstallationFailedError,
    InstallerError,
    TargetNotSupportedError,
    UserAbortedSetupError,
)
from .setup_service import SetupService
from .system_installer import SystemInstaller

__all__ = [
    "SetupService",
    "SystemInstaller",
    "InstallerError",
    "TargetNotSupportedError",
    "InstallationFailedError",
    "UserAbortedSetupError",
]
