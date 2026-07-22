"""Dataclasses for guard scan results, history findings, and summaries."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GuardScanResult:
    """Represents the result of a repository guard scan."""

    is_safe: bool
    sensitive_files: List[str]


@dataclass
class HistoryFinding:
    """Represents a single secret finding in Git history.

    Attributes:
        commit_hash: The full SHA of the commit containing the secret.
        file_path: The path of the sensitive file in the commit.
        pattern_matched: The pattern that triggered the detection.
        commit_message: The first line of the commit message.
        author: The author name of the commit.
        date: The commit date string.
        branch: The branch(es) containing this commit.
    """

    commit_hash: str
    file_path: str
    pattern_matched: str
    commit_message: str
    author: str
    date: str
    branch: Optional[str] = None


@dataclass
class HistoryScanResult:
    """Represents the complete result of a Git history scan.

    Attributes:
        findings: List of secret findings across history.
        total_commits_scanned: Number of commits examined.
        total_findings: Total number of secrets found.
        repo_path: The repository path that was scanned.
    """

    findings: List[HistoryFinding] = field(default_factory=list)
    total_commits_scanned: int = 0
    total_findings: int = 0
    repo_path: Optional[str] = None
