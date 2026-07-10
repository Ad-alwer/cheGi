from dataclasses import dataclass, field
from typing import List


@dataclass
class InstallTask:
    """Represents a single tool or package to be installed."""
    name: str
    cmd: str
    level: str = "default"
    requires: List[str] = field(default_factory=list)
