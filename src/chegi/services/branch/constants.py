"""Constants for the branch service."""

from typing import FrozenSet

# Branches that cannot be deleted through chegi
PROTECTED_BRANCHES: FrozenSet[str] = frozenset({"main", "master", "develop"})
