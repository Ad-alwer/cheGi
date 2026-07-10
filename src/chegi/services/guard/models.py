from dataclasses import dataclass
from typing import List


@dataclass
class GuardScanResult:
    """Represents the result of a repository guard scan."""

    is_safe: bool
    sensitive_files: List[str]
