"""Public API re-exports for cheGi configuration constants and manager."""

from .constants import (
    DEFAULT_EXCLUDES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MCTS,
    DEFAULT_MIRRORS,
    DEFAULT_SENSITIVE_PATTERNS,
    GITIGNORE_COMMIT_MESSAGE,
    SUPPORTED_PMS,
)
from .exceptions import (
    ConfigError,
    InvalidMirrorFormatError,
    UnsupportedPackageManagerError,
)
from .global_config import GlobalConfig
from .manager import ChegiConfig
from .models import ChegiConfigModel

__all__ = [
    "ChegiConfig",
    "ChegiConfigModel",
    "GlobalConfig",
    "ConfigError",
    "UnsupportedPackageManagerError",
    "InvalidMirrorFormatError",
    "DEFAULT_SENSITIVE_PATTERNS",
    "SUPPORTED_PMS",
    "DEFAULT_EXCLUDES",
    "DEFAULT_MAX_DEPTH",
    "DEFAULT_MCTS",
    "DEFAULT_MIRRORS",
    "GITIGNORE_COMMIT_MESSAGE",
]
