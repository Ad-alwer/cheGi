"""Data models for Git global configuration entries."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GitConfigCategory(str, Enum):
    """Categorizes git config keys for display purposes."""

    USER = "user"
    CORE = "core"
    ALIAS = "alias"
    CREDENTIAL = "credential"
    INIT = "init"
    PULL = "pull"
    FETCH = "fetch"
    COMMIT_TAG = "commit_tag"
    SAFE = "safe"
    OTHER = "other"


CATEGORY_MAP: dict[str, GitConfigCategory] = {
    "user.": GitConfigCategory.USER,
    "core.": GitConfigCategory.CORE,
    "alias.": GitConfigCategory.ALIAS,
    "credential.": GitConfigCategory.CREDENTIAL,
    "init.": GitConfigCategory.INIT,
    "pull.": GitConfigCategory.PULL,
    "fetch.": GitConfigCategory.FETCH,
    "commit.": GitConfigCategory.COMMIT_TAG,
    "tag.": GitConfigCategory.COMMIT_TAG,
    "safe.": GitConfigCategory.SAFE,
}

CATEGORY_ICONS: dict[GitConfigCategory, str] = {
    GitConfigCategory.USER: "👤",
    GitConfigCategory.CORE: "⚙️",
    GitConfigCategory.ALIAS: "🔗",
    GitConfigCategory.CREDENTIAL: "🔐",
    GitConfigCategory.INIT: "🌱",
    GitConfigCategory.PULL: "🚚",
    GitConfigCategory.FETCH: "📡",
    GitConfigCategory.COMMIT_TAG: "💎",
    GitConfigCategory.SAFE: "🛡️",
    GitConfigCategory.OTHER: "📋",
}

CATEGORY_LABELS: dict[GitConfigCategory, str] = {
    GitConfigCategory.USER: "User Identity",
    GitConfigCategory.CORE: "Core",
    GitConfigCategory.ALIAS: "Aliases",
    GitConfigCategory.CREDENTIAL: "Credentials",
    GitConfigCategory.INIT: "Init",
    GitConfigCategory.PULL: "Pull",
    GitConfigCategory.FETCH: "Fetch",
    GitConfigCategory.COMMIT_TAG: "Commit / Tag",
    GitConfigCategory.SAFE: "Safe",
    GitConfigCategory.OTHER: "Other",
}


def categorize_key(key: str) -> GitConfigCategory:
    """Determines the category of a git config key based on its prefix.

    Args:
        key: The git config key (e.g. user.name, core.editor).

    Returns:
        The matching GitConfigCategory.
    """
    for prefix, category in CATEGORY_MAP.items():
        if key.startswith(prefix):
            return category
    return GitConfigCategory.OTHER


@dataclass
class GitConfigEntry:
    """Represents a single git global configuration entry."""

    key: str
    value: str
    category: GitConfigCategory = field(init=False)

    def __post_init__(self) -> None:
        self.category = categorize_key(self.key)


@dataclass
class ConfigChange:
    """Tracks a single configuration change for revert purposes."""

    key: str
    old_value: Optional[str]
    new_value: Optional[str]

    @property
    def summary(self) -> str:
        old = self.old_value or "(not set)"
        new = self.new_value or "(unset)"
        return f"{self.key}: {old} → {new}"
