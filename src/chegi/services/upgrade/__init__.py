"""Upgrade service for self-updating cheGi."""

from chegi.services.upgrade.exceptions import UpgradeError
from chegi.services.upgrade.models import UpgradeInfo
from chegi.services.upgrade.upgrade_service import UpgradeService

__all__ = [
    "UpgradeService",
    "UpgradeInfo",
    "UpgradeError",
]
