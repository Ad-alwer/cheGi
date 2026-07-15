"""Cache for GitHub repository listings."""

import json
import time
from pathlib import Path
from typing import List, Optional

from chegi.services.github.models import GitHubRepo

CACHE_TTL = 300  # 5 minutes


def _cache_path() -> Path:
    """Returns the path to the repo cache file.

    Returns:
        Path to repo_cache.json in the cheGi config directory.
    """
    from chegi.config.global_config import GLOBAL_CONFIG_DIR

    return GLOBAL_CONFIG_DIR / "repo_cache.json"


def _serialize_repos(repos: List[GitHubRepo]) -> list:
    """Converts GitHubRepo objects to serializable dicts.

    Args:
        repos: List of GitHubRepo objects.

    Returns:
        List of dicts.
    """
    return [
        {
            "name": r.name,
            "full_name": r.full_name,
            "html_url": r.html_url,
            "private": r.private,
            "default_branch": r.default_branch,
            "description": r.description,
            "language": r.language,
            "stargazers_count": r.stargazers_count,
            "forks_count": r.forks_count,
            "updated_at": r.updated_at,
            "fork": r.fork,
        }
        for r in repos
    ]


def _deserialize_repos(data: list) -> List[GitHubRepo]:
    """Converts serialized dicts back to GitHubRepo objects.

    Args:
        data: List of dicts from cache.

    Returns:
        List of GitHubRepo objects.
    """
    return [GitHubRepo(**item) for item in data]


class RepoCache:
    """Manages local caching of GitHub repository listings."""

    @staticmethod
    def is_fresh() -> bool:
        """Checks if the cache exists and is within the TTL window.

        Returns:
            True if the cache is fresh, False otherwise.
        """
        path = _cache_path()
        if not path.exists():
            return False
        try:
            mtime = path.stat().st_mtime
            return (time.time() - mtime) < CACHE_TTL
        except OSError:
            return False

    @staticmethod
    def read() -> Optional[List[GitHubRepo]]:
        """Reads repos from the cache.

        Returns:
            List of GitHubRepo objects, or None if cache is missing/corrupt.
        """
        path = _cache_path()
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return _deserialize_repos(data)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def write(repos: List[GitHubRepo]) -> None:
        """Writes repos to the cache.

        Args:
            repos: List of GitHubRepo objects to cache.
        """
        path = _cache_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = _serialize_repos(repos)
            path.write_text(json.dumps(data, indent=2))
        except OSError:
            pass

    @staticmethod
    def clear() -> None:
        """Removes the cache file."""
        path = _cache_path()
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass

    @staticmethod
    def age() -> Optional[float]:
        """Returns the age of the cache in seconds.

        Returns:
            Cache age in seconds, or None if no cache.
        """
        path = _cache_path()
        if not path.exists():
            return None
        try:
            return time.time() - path.stat().st_mtime
        except OSError:
            return None
