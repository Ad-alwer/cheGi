"""Constants for commit styles and branding."""

from typing import List

from chegi.services.commit.models import CommitStyle

BRAND_SUFFIX: str = " 🐆"

BUILTIN_STYLES: List[CommitStyle] = [
    CommitStyle(
        name="free",
        label="Free",
        description="No prefix, no scope. Just write.",
        fields=["description"],
    ),
    CommitStyle(
        name="conventional",
        label="Conventional",
        description="type: description",
        fields=["type", "description"],
        types=[
            "feat",
            "fix",
            "docs",
            "test",
            "refactor",
            "chore",
            "perf",
            "ci",
            "style",
            "revert",
        ],
    ),
    CommitStyle(
        name="conventional-scope",
        label="Conventional with scope",
        description="type(scope): description",
        fields=["type", "scope", "description"],
        types=[
            "feat",
            "fix",
            "docs",
            "test",
            "refactor",
            "chore",
            "perf",
            "ci",
            "style",
            "revert",
        ],
    ),
    CommitStyle(
        name="conventional-body",
        label="Conventional with body",
        description="type(scope): description\n\n- body bullet",
        fields=["type", "scope", "description", "body"],
        types=[
            "feat",
            "fix",
            "docs",
            "test",
            "refactor",
            "chore",
            "perf",
            "ci",
            "style",
            "revert",
        ],
    ),
    CommitStyle(
        name="gitmoji",
        label="Gitmoji",
        description="✨ type: description",
        fields=["emoji", "type", "description"],
        types=[
            "feat",
            "fix",
            "docs",
            "test",
            "refactor",
            "chore",
            "perf",
            "ci",
            "style",
            "revert",
        ],
        emojis={
            "feat": "✨",
            "fix": "🐛",
            "docs": "📖",
            "test": "🧪",
            "refactor": "♻️",
            "chore": "🔧",
            "perf": "⚡",
            "ci": "👷",
            "style": "🎨",
            "revert": "⏪",
        },
    ),
]
