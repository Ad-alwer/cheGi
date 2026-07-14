"""
Data structures and models for the configuration module.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set

from .constants import (
    DEFAULT_EXCLUDES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MCTS,
    DEFAULT_MIRRORS,
)


@dataclass
class ChegiConfigModel:
    """Data model representing the state and structure of the cheGi configuration."""

    exclude_dirs: Set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDES))
    max_depth: int = DEFAULT_MAX_DEPTH
    mcts: int = DEFAULT_MCTS
    mirrors: Dict[str, List[str]] = field(
        default_factory=lambda: {k: list(v) for k, v in DEFAULT_MIRRORS.items()}
    )
    sensitive_patterns: Set[str] = field(default_factory=set)
