"""Tests for RepoCache."""

import json
import time
from pathlib import Path
from unittest.mock import patch

from chegi.services.github.cache import RepoCache
from chegi.services.github.models import GitHubRepo


def _make_repo(name: str = "test-repo") -> GitHubRepo:
    """Helper to create a test repo."""
    return GitHubRepo(
        name=name,
        full_name=f"user/{name}",
        html_url=f"https://github.com/user/{name}",
        private=False,
        default_branch="main",
        language="Python",
        stargazers_count=42,
        forks_count=7,
        updated_at="2026-07-16T10:00:00Z",
    )


def test_cache_write_and_read(tmp_path: Path):
    """Tests that written repos can be read back."""
    with patch(
        "chegi.services.github.cache._cache_path",
        return_value=tmp_path / "repo_cache.json",
    ):
        repos = [_make_repo("repo-one"), _make_repo("repo-two")]
        RepoCache.write(repos)

        assert (tmp_path / "repo_cache.json").exists()

        loaded = RepoCache.read()
        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0].name == "repo-one"
        assert loaded[1].name == "repo-two"


def test_cache_read_missing_file(tmp_path: Path):
    """Tests that read returns None when no cache file exists."""
    with patch(
        "chegi.services.github.cache._cache_path",
        return_value=tmp_path / "repo_cache.json",
    ):
        loaded = RepoCache.read()
        assert loaded is None


def test_cache_read_corrupt_file(tmp_path: Path):
    """Tests that read returns None when cache is corrupt."""
    cache_file = tmp_path / "repo_cache.json"
    cache_file.write_text("not valid json")
    with patch("chegi.services.github.cache._cache_path", return_value=cache_file):
        loaded = RepoCache.read()
        assert loaded is None


def test_cache_is_fresh_returns_true(tmp_path: Path):
    """Tests that is_fresh returns True within TTL."""
    cache_file = tmp_path / "repo_cache.json"
    repos = [_make_repo()]
    cache_file.write_text(
        json.dumps(
            [
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
        )
    )

    with patch("chegi.services.github.cache._cache_path", return_value=cache_file):
        assert RepoCache.is_fresh() is True


def test_cache_is_fresh_returns_false_when_expired(tmp_path: Path):
    """Tests that is_fresh returns False after TTL expires."""
    cache_file = tmp_path / "repo_cache.json"
    cache_file.write_text("[]")
    old_mtime = time.time() - 600  # 10 minutes ago
    os_util = __import__("os")
    os_util.utime(str(cache_file), (old_mtime, old_mtime))

    with patch("chegi.services.github.cache._cache_path", return_value=cache_file):
        assert RepoCache.is_fresh() is False


def test_cache_is_fresh_returns_false_when_missing(tmp_path: Path):
    """Tests that is_fresh returns False when no cache."""
    with patch(
        "chegi.services.github.cache._cache_path",
        return_value=tmp_path / "repo_cache.json",
    ):
        assert RepoCache.is_fresh() is False


def test_cache_clear_removes_file(tmp_path: Path):
    """Tests that clear removes the cache file."""
    cache_file = tmp_path / "repo_cache.json"
    cache_file.write_text("[]")

    with patch("chegi.services.github.cache._cache_path", return_value=cache_file):
        RepoCache.clear()
        assert not cache_file.exists()


def test_cache_clear_no_file(tmp_path: Path):
    """Tests that clear does not error when no cache."""
    with patch(
        "chegi.services.github.cache._cache_path",
        return_value=tmp_path / "repo_cache.json",
    ):
        RepoCache.clear()  # should not raise


def test_cache_age_returns_none_when_missing(tmp_path: Path):
    """Tests that age returns None when no cache."""
    with patch(
        "chegi.services.github.cache._cache_path",
        return_value=tmp_path / "repo_cache.json",
    ):
        assert RepoCache.age() is None


def test_cache_age_returns_float(tmp_path: Path):
    """Tests that age returns a positive number."""
    cache_file = tmp_path / "repo_cache.json"
    cache_file.write_text("[]")
    with patch("chegi.services.github.cache._cache_path", return_value=cache_file):
        age = RepoCache.age()
        assert age is not None
        assert age >= 0
