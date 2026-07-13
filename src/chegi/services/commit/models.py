"""Data models for the commit service."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CommitStyle:
    """Defines a commit message style/format.

    Attributes:
        name: Unique identifier for the style.
        label: Human-readable label shown in prompts.
        description: Short description shown to the user.
        fields: Ordered list of field names to prompt for.
        types: Available conventional commit types (if applicable).
        emojis: Mapping of type -> emoji (for gitmoji style).
    """

    name: str
    label: str
    description: str
    fields: List[str]
    types: Optional[List[str]] = None
    emojis: Optional[Dict[str, str]] = None


@dataclass
class CommitContext:
    """Represents the state of a pending commit.

    Attributes:
        staged_files: List of file paths currently staged.
        diff_stat: The diff stat output string.
        name_status: List of (status, path) tuples for staged files.
        is_safe: Whether the staged files pass security guard.
        sensitive_files: List of sensitive files detected (if any).
        suggested_messages: List of suggested commit messages.
    """

    staged_files: List[str] = field(default_factory=list)
    diff_stat: str = ""
    name_status: List[Tuple[str, str]] = field(default_factory=list)
    is_safe: bool = True
    sensitive_files: List[str] = field(default_factory=list)
    suggested_messages: List[str] = field(default_factory=list)
