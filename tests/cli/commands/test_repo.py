"""Tests for the chegi repo CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app
from chegi.services.github.models import GitHubRepo

runner = CliRunner()


def _make_repo(
    name: str = "test-repo", private: bool = False, language: str = "Python"
) -> GitHubRepo:
    """Helper to create a test repo."""
    return GitHubRepo(
        name=name,
        full_name=f"user/{name}",
        html_url=f"https://github.com/user/{name}",
        private=private,
        default_branch="main",
        language=language,
        stargazers_count=42,
        forks_count=7,
        updated_at="2026-07-16T10:00:00Z",
    )


# ── list: no token ────────────────────────────────────────


@patch("chegi.cli.commands.repo.AuthService.get_credential_for_host")
def test_list_repos_no_token(mock_cred: MagicMock):
    """Tests that repo list shows error when no token."""
    mock_cred.return_value = None
    result = runner.invoke(app, ["repo", "list", "--format", "table"])
    assert result.exit_code == 1
    assert "No GitHub token found" in result.stdout


# ── list: table format ─────────────────────────────────────


@patch("chegi.cli.commands.repo.RepoCache.is_fresh")
@patch("chegi.cli.commands.repo.RepoCache.read")
@patch("chegi.cli.commands.repo.AuthService.get_credential_for_host")
def test_list_repos_table(
    mock_cred: MagicMock, mock_cache: MagicMock, mock_fresh: MagicMock
):
    """Tests that repo list --format table displays repos."""
    mock_cred.return_value = MagicMock(token="ghp_test123")
    mock_fresh.return_value = True
    mock_cache.return_value = [_make_repo("repo-a"), _make_repo("repo-b")]

    result = runner.invoke(app, ["repo", "list", "--format", "table"])
    assert result.exit_code == 0, result.stdout
    assert "repo-a" in result.stdout
    assert "repo-b" in result.stdout
    assert "42" in result.stdout  # stars


# ── list: json format ──────────────────────────────────────


@patch("chegi.cli.commands.repo.RepoCache.is_fresh")
@patch("chegi.cli.commands.repo.RepoCache.read")
@patch("chegi.cli.commands.repo.AuthService.get_credential_for_host")
def test_list_repos_json(
    mock_cred: MagicMock, mock_cache: MagicMock, mock_fresh: MagicMock
):
    """Tests that repo list --format json outputs valid JSON."""
    mock_cred.return_value = MagicMock(token="ghp_test123")
    mock_fresh.return_value = True
    mock_cache.return_value = [_make_repo("json-repo")]

    result = runner.invoke(app, ["repo", "list", "--format", "json"])
    assert result.exit_code == 0, result.stdout
    assert '"name": "json-repo"' in result.stdout
    assert '"stars": 42' in result.stdout


# ── list: limit ────────────────────────────────────────────


@patch("chegi.cli.commands.repo.RepoCache.is_fresh")
@patch("chegi.cli.commands.repo.RepoCache.read")
@patch("chegi.cli.commands.repo.AuthService.get_credential_for_host")
def test_list_repos_limit(
    mock_cred: MagicMock, mock_cache: MagicMock, mock_fresh: MagicMock
):
    """Tests that repo list --limit returns at most N repos."""
    mock_cred.return_value = MagicMock(token="ghp_test123")
    mock_fresh.return_value = True
    mock_cache.return_value = [_make_repo(f"repo-{i}") for i in range(10)]

    result = runner.invoke(app, ["repo", "list", "--format", "table", "--limit", "3"])
    assert result.exit_code == 0, result.stdout
    assert "repo-0" in result.stdout
    assert "repo-3" not in result.stdout  # beyond limit


# ── list: public filter ────────────────────────────────────


@patch("chegi.cli.commands.repo.RepoCache.is_fresh")
@patch("chegi.cli.commands.repo.RepoCache.read")
@patch("chegi.cli.commands.repo.AuthService.get_credential_for_host")
def test_list_repos_public(
    mock_cred: MagicMock, mock_cache: MagicMock, mock_fresh: MagicMock
):
    """Tests that repo list --public shows only public repos."""
    mock_cred.return_value = MagicMock(token="ghp_test123")
    mock_fresh.return_value = True
    mock_cache.return_value = [
        _make_repo("public-repo", private=False),
        _make_repo("private-repo", private=True),
    ]

    result = runner.invoke(app, ["repo", "list", "--format", "table", "--public"])
    assert result.exit_code == 0, result.stdout
    assert "public-repo" in result.stdout
    assert "private-repo" not in result.stdout


# ── list: private filter ───────────────────────────────────


@patch("chegi.cli.commands.repo.RepoCache.is_fresh")
@patch("chegi.cli.commands.repo.RepoCache.read")
@patch("chegi.cli.commands.repo.AuthService.get_credential_for_host")
def test_list_repos_private(
    mock_cred: MagicMock, mock_cache: MagicMock, mock_fresh: MagicMock
):
    """Tests that repo list --private shows only private repos."""
    mock_cred.return_value = MagicMock(token="ghp_test123")
    mock_fresh.return_value = True
    mock_cache.return_value = [
        _make_repo("public-repo", private=False),
        _make_repo("private-repo", private=True),
    ]

    result = runner.invoke(app, ["repo", "list", "--format", "table", "--private"])
    assert result.exit_code == 0, result.stdout
    assert "private-repo" in result.stdout
    assert "public-repo" not in result.stdout


# ── list: empty ────────────────────────────────────────────


@patch("chegi.cli.commands.repo.RepoCache.is_fresh")
@patch("chegi.cli.commands.repo.RepoCache.read")
@patch("chegi.cli.commands.repo.AuthService.get_credential_for_host")
def test_list_repos_empty(
    mock_cred: MagicMock, mock_cache: MagicMock, mock_fresh: MagicMock
):
    """Tests that repo list shows message when no repos."""
    mock_cred.return_value = MagicMock(token="ghp_test123")
    mock_fresh.return_value = True
    mock_cache.return_value = []

    result = runner.invoke(app, ["repo", "list", "--format", "table"])
    assert result.exit_code == 0, result.stdout
    assert "No repositories" in result.stdout


# ── list: refresh flag ─────────────────────────────────────


@patch("chegi.cli.commands.repo.GitHubRepoService.list_repos")
@patch("chegi.cli.commands.repo.RepoCache.write")
@patch("chegi.cli.commands.repo.RepoCache.is_fresh")
@patch("chegi.cli.commands.repo.RepoCache.read")
@patch("chegi.cli.commands.repo.AuthService.get_credential_for_host")
def test_list_repos_refresh(
    mock_cred: MagicMock,
    mock_cache_read: MagicMock,
    mock_cache_fresh: MagicMock,
    mock_cache_write: MagicMock,
    mock_api: MagicMock,
):
    """Tests that --refresh calls the API even when cache is fresh."""
    mock_cred.return_value = MagicMock(token="ghp_test123")
    mock_cache_fresh.return_value = True
    mock_cache_read.return_value = [_make_repo("old-repo")]
    mock_api.return_value = [_make_repo("fresh-repo")]

    result = runner.invoke(app, ["repo", "list", "--format", "table", "--refresh"])
    assert result.exit_code == 0, result.stdout
    assert "fresh-repo" in result.stdout
    assert "old-repo" not in result.stdout
