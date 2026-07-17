"""Constants for the upgrade service."""

# PyPI JSON API URL for checking latest version
PYPI_JSON_URL = "https://pypi.org/pypi/chegi/json"

# GitHub raw CHANGELOG URL for release notes
CHANGELOG_RAW_URL = "https://raw.githubusercontent.com/Ad-alwer/cheGi/main/CHANGELOG.md"

# Cooldown between auto-checks (in seconds: 24 hours)
AUTO_CHECK_COOLDOWN = 86400

# Marker file name inside .chegi/ directory
CHECK_MARKER_FILE = ".last_upgrade_check"
