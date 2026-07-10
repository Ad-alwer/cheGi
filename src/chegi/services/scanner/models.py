"""Data models for the scanner service."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScanOptions:
    """Data model representing the configuration options for a scan operation."""

    path: str
    max_depth: Optional[int] = None
    workers: int = os.cpu_count() or 1
    security: bool = False
    dirty: bool = False
    staged: bool = False
