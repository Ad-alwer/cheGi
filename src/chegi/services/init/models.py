"""Data models for the init/project module."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ProjectConfig:
    """Represents the content of a .chegi/config.json file."""

    exclude_dirs: List[str] = field(default_factory=list)
    max_depth: Optional[int] = None
    mcts: Optional[int] = None
    mirrors: Dict[str, List[str]] = field(default_factory=dict)
    guard_rules: List[str] = field(default_factory=list)
    guard_excludes: List[str] = field(default_factory=list)


@dataclass
class GuardRules:
    """Represents the content of a .chegi/guard-rules.json file."""

    patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)


@dataclass
class ChegiProject:
    """Represents a cheGi project with its .chegi/ directory.

    Attributes:
        root: The project root directory (contains .chegi/).
        chegi_dir: Path to the .chegi/ directory.
        config: Loaded project configuration.
        guard_rules: Loaded guard rules.
        chegiignore: List of ignore patterns from .chegiignore.
    """

    root: Path
    chegi_dir: Path
    config: Optional[ProjectConfig] = None
    guard_rules: Optional[GuardRules] = None
    chegiignore: List[str] = field(default_factory=list)
