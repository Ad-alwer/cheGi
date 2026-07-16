"""Clone service for cloning repositories with smart defaults."""

from chegi.services.clone.clone_service import CloneService, parse_url
from chegi.services.clone.exceptions import (
    CloneAuthError,
    CloneError,
    CloneTargetExistsError,
    CloneUrlError,
)
from chegi.services.clone.models import CloneConfig, CloneResult, CloneSource

__all__ = [
    "CloneService",
    "CloneConfig",
    "CloneResult",
    "CloneSource",
    "parse_url",
    "CloneError",
    "CloneUrlError",
    "CloneAuthError",
    "CloneTargetExistsError",
]
