"""Git global configuration service for cheGi."""

from chegi.services.git_config.exceptions import GitConfigError
from chegi.services.git_config.models import (
    CATEGORY_ICONS,
    CATEGORY_LABELS,
    CATEGORY_MAP,
    ConfigChange,
    GitConfigCategory,
    GitConfigEntry,
    categorize_key,
)
from chegi.services.git_config.service import GitConfigService

__all__ = [
    "GitConfigService",
    "GitConfigEntry",
    "GitConfigCategory",
    "ConfigChange",
    "GitConfigError",
    "categorize_key",
    "CATEGORY_ICONS",
    "CATEGORY_LABELS",
    "CATEGORY_MAP",
]
