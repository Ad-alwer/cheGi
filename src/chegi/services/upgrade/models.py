"""Data models for the upgrade service."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UpgradeInfo:
    """Represents the result of a version check against PyPI.

    Attributes:
        current_version: The currently installed version.
        latest_version: The latest version available on PyPI.
        is_outdated: True when a newer version exists.
        changelog_diff: Release notes / changelog for newer versions.
        error: Error message if the check failed.
    """

    current_version: str
    latest_version: Optional[str] = None
    is_outdated: bool = False
    changelog_diff: Optional[str] = None
    error: Optional[str] = None
