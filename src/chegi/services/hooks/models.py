"""Data models for the hooks service."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class HookInfo:
    """Information about an installed hook.

    Attributes:
        installed: Whether the cheGi hook is currently installed.
        path: Absolute path to the hook file (if installed).
        version: The cheGi version that last installed this hook.
    """

    installed: bool
    path: Optional[str] = None
    version: Optional[str] = None
