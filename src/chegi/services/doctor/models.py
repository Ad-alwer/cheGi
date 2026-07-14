"""Data models for the doctor service."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class CheckStatus(Enum):
    """Status of a single health check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"

    @property
    def emoji(self) -> str:
        mapping = {
            CheckStatus.PASS: "✓",
            CheckStatus.WARN: "⚠",
            CheckStatus.FAIL: "✗",
            CheckStatus.SKIP: "→",
        }
        return mapping[self]

    @property
    def rich_style(self) -> str:
        mapping = {
            CheckStatus.PASS: "bold green",
            CheckStatus.WARN: "bold yellow",
            CheckStatus.FAIL: "bold red",
            CheckStatus.SKIP: "dim",
        }
        return mapping[self]


class CheckCategory(Enum):
    """Category of health checks."""

    HEALTH = "Health"
    SECURITY = "Security"
    STATS = "Stats"


@dataclass
class CheckResult:
    """Result of a single health check.

    Attributes:
        name: Short check name (e.g., "Git Installed").
        category: Which category this check belongs to.
        status: PASS, WARN, FAIL, or SKIP.
        message: Human-readable result message.
        suggestion: Optional actionable suggestion if check fails.
    """

    name: str
    category: CheckCategory
    status: CheckStatus
    message: str
    suggestion: Optional[str] = None


@dataclass
class DoctorReport:
    """Complete doctor report for a project.

    Attributes:
        results: List of individual check results.
        repo_path: Path to the checked repository (if any).
        pass_count: Number of passed checks.
        warn_count: Number of warnings.
        fail_count: Number of failures.
        skip_count: Number of skipped checks.
    """

    results: List[CheckResult] = field(default_factory=list)
    repo_path: Optional[str] = None

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.PASS)

    @property
    def warn_count(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.WARN)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.FAIL)

    @property
    def skip_count(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.SKIP)

    @property
    def total(self) -> int:
        return len(self.results)
