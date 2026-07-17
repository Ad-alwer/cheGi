"""Service for checking and performing cheGi upgrades."""

import json
import subprocess
import time
from pathlib import Path
from typing import Optional

from chegi.services.upgrade.constants import (
    AUTO_CHECK_COOLDOWN,
    CHANGELOG_RAW_URL,
    CHECK_MARKER_FILE,
    PYPI_JSON_URL,
)
from chegi.services.upgrade.exceptions import UpgradeError
from chegi.services.upgrade.models import UpgradeInfo


class UpgradeService:
    """Service for checking and installing cheGi updates.

    Checks the latest version on PyPI, fetches changelog diffs,
    and performs pip upgrades. Supports a 24-hour cooldown for
    automatic background checks.
    """

    def __init__(self, repo_path: Optional[Path] = None):
        """Initializes the UpgradeService.

        Args:
            repo_path: Path to the project root (for .chegi/ marker).
                       Defaults to current directory.
        """
        self.repo_path = repo_path or Path.cwd()

    @staticmethod
    def get_current_version() -> str:
        """Returns the currently installed cheGi version.

        Returns:
            The version string, or '0.0.0' if undetectable.
        """
        try:
            from importlib.metadata import PackageNotFoundError, version

            return version("chegi")
        except PackageNotFoundError:
            return "0.0.0"

    def check_version(self, timeout: int = 5) -> UpgradeInfo:
        """Checks the latest version on PyPI.

        Args:
            timeout: Request timeout in seconds.

        Returns:
            An UpgradeInfo with current vs latest version info.
        """
        current = self.get_current_version()

        try:
            import urllib.request

            req = urllib.request.Request(
                PYPI_JSON_URL,
                headers={"User-Agent": "chegi-upgrade/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())

            latest = data.get("info", {}).get("version", "")
            if not latest:
                return UpgradeInfo(
                    current_version=current,
                    error="Could not parse version from PyPI response.",
                )

            is_outdated = self._compare_versions(current, latest) < 0
            changelog_diff = None

            if is_outdated:
                changelog_diff = self._fetch_changelog_diff(current, latest)

            return UpgradeInfo(
                current_version=current,
                latest_version=latest,
                is_outdated=is_outdated,
                changelog_diff=changelog_diff,
            )

        except Exception as e:
            return UpgradeInfo(
                current_version=current,
                error=f"Failed to check for updates: {e}",
            )

    def upgrade(self, yes: bool = False) -> str:
        """Upgrades cheGi to the latest version via pip.

        Args:
            yes: Skip confirmation.

        Returns:
            The pip command output.

        Raises:
            UpgradeError: If the upgrade fails.
        """
        try:
            cmd = [
                "pip", "install", "--upgrade",
                "--quiet", "--quiet",
                "chegi",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise UpgradeError(
                f"Upgrade failed: {e.stderr.strip()}"
            ) from e
        except subprocess.TimeoutExpired as e:
            raise UpgradeError("Upgrade timed out after 120 seconds.") from e
        except FileNotFoundError:
            raise UpgradeError("pip is not installed. Cannot upgrade.")

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Compares two semantic version strings.

        Args:
            v1: First version string.
            v2: Second version string.

        Returns:
            Negative if v1 < v2, positive if v1 > v2, 0 if equal.
        """
        def parse(ver: str):
            try:
                return [int(p) for p in ver.split(".")]
            except ValueError:
                return [0]

        parts1 = parse(v1)
        parts2 = parse(v2)

        # Pad to same length
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))

        for a, b in zip(parts1, parts2):
            if a != b:
                return a - b
        return 0

    @staticmethod
    def _fetch_changelog_diff(current: str, latest: str) -> Optional[str]:
        """Fetches the changelog section for versions between current and latest.

        Args:
            current: The current version.
            latest: The latest version.

        Returns:
            The changelog section text, or None if fetch fails.
        """
        try:
            import urllib.request

            req = urllib.request.Request(
                CHANGELOG_RAW_URL,
                headers={"User-Agent": "chegi-upgrade/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                content = resp.read().decode()

            # Extract content between the latest version header and current version
            # Format: ## [X.Y.Z] - YYYY-MM-DD
            lines = content.splitlines()
            result: list[str] = []
            recording = False
            for line in lines:
                if line.startswith(f"## [{latest}"):
                    recording = True
                    result.append(line)
                elif line.startswith(f"## [{current}"):
                    break
                elif line.startswith("## [") and recording:
                    # Another version header before current — keep going
                    result.append(line)
                elif recording:
                    result.append(line)

            return "\n".join(result).strip() if result else None

        except Exception:
            return None

    def should_check(self) -> bool:
        """Checks if the 24-hour cooldown has passed since last check.

        Returns:
            True if enough time has passed (or marker doesn't exist).
        """
        path = self._cooldown_path()
        if not path.exists():
            return True

        try:
            last_check = float(path.read_text().strip())
            return (time.time() - last_check) > AUTO_CHECK_COOLDOWN
        except (ValueError, OSError):
            return True

    def mark_checked(self) -> None:
        """Writes the current timestamp to the cooldown marker file."""
        path = self._cooldown_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(int(time.time())))
        except OSError:
            pass

    def _cooldown_path(self) -> Path:
        """Returns the path to the cooldown marker file under repo_path."""
        return self.repo_path / ".chegi" / CHECK_MARKER_FILE
