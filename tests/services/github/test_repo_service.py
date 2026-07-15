"""Tests for GitHubRepoService."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chegi.services.github.exceptions import (
    GitHubAuthError,
    GitHubError,
    RepoExistsError,
)
from chegi.services.github.repo_service import GitHubRepoService

# ── create_repo ─────────────────────────────────────────────


@patch("chegi.services.github.repo_service.urllib.request.urlopen")
def test_create_repo_returns_repo(mock_urlopen: MagicMock):
    """Tests that create_repo returns a GitHubRepo on success."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {
            "name": "my-project",
            "full_name": "user/my-project",
            "html_url": "https://github.com/user/my-project",
            "private": False,
            "default_branch": "main",
            "description": "A test project",
        }
    ).encode()
    mock_urlopen.return_value.__enter__.return_value = mock_response

    repo = GitHubRepoService.create_repo(
        name="my-project",
        token="ghp_test123",
        description="A test project",
    )

    assert repo.name == "my-project"
    assert repo.full_name == "user/my-project"
    assert repo.html_url == "https://github.com/user/my-project"
    assert repo.private is False
    assert repo.default_branch == "main"
    assert repo.description == "A test project"


@patch("chegi.services.github.repo_service.urllib.request.urlopen")
def test_create_repo_private(mock_urlopen: MagicMock):
    """Tests that create_repo with private=True creates a private repo."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {
            "name": "secret-project",
            "full_name": "user/secret-project",
            "html_url": "https://github.com/user/secret-project",
            "private": True,
            "default_branch": "main",
        }
    ).encode()
    mock_urlopen.return_value.__enter__.return_value = mock_response

    repo = GitHubRepoService.create_repo(
        name="secret-project",
        token="ghp_test123",
        private=True,
    )

    assert repo.private is True
    assert repo.name == "secret-project"


@patch("chegi.services.github.repo_service.urllib.request.urlopen")
def test_create_repo_raises_auth_error(mock_urlopen: MagicMock):
    """Tests that create_repo raises GitHubAuthError on 401."""
    from urllib.error import HTTPError

    mock_urlopen.side_effect = HTTPError(
        url="https://api.github.com/user/repos",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=None,
    )

    with pytest.raises(GitHubAuthError, match="invalid or has been revoked"):
        GitHubRepoService.create_repo(name="my-project", token="bad-token")


@patch("chegi.services.github.repo_service.urllib.request.urlopen")
def test_create_repo_raises_repo_exists(mock_urlopen: MagicMock):
    """Tests that create_repo raises RepoExistsError on 422 name conflict."""
    from urllib.error import HTTPError

    error_response = MagicMock()
    error_response.read.return_value = json.dumps(
        {
            "message": "Repository creation failed.",
            "errors": [{"message": "name already exists on this account"}],
        }
    ).encode()

    mock_urlopen.side_effect = HTTPError(
        url="https://api.github.com/user/repos",
        code=422,
        msg="Unprocessable Entity",
        hdrs={},
        fp=error_response,
    )

    with pytest.raises(RepoExistsError, match="already exists"):
        GitHubRepoService.create_repo(name="existing-repo", token="ghp_test123")


@patch("chegi.services.github.repo_service.urllib.request.urlopen")
def test_create_repo_raises_other_http_error(mock_urlopen: MagicMock):
    """Tests that create_repo raises GitHubError on other HTTP errors."""
    from urllib.error import HTTPError

    mock_urlopen.side_effect = HTTPError(
        url="https://api.github.com/user/repos",
        code=403,
        msg="Forbidden",
        hdrs={},
        fp=None,
    )

    with pytest.raises(GitHubError, match="HTTP 403"):
        GitHubRepoService.create_repo(name="my-project", token="ghp_test123")


# ── list_repos ──────────────────────────────────────────────


@patch("chegi.services.github.repo_service.urllib.request.urlopen")
def test_list_repos_returns_list(mock_urlopen: MagicMock):
    """Tests that list_repos returns a list of GitHubRepo objects."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        [
            {
                "name": "repo-one",
                "full_name": "user/repo-one",
                "html_url": "https://github.com/user/repo-one",
                "private": False,
                "default_branch": "main",
            },
            {
                "name": "repo-two",
                "full_name": "user/repo-two",
                "html_url": "https://github.com/user/repo-two",
                "private": True,
                "default_branch": "master",
            },
        ]
    ).encode()
    mock_urlopen.return_value.__enter__.return_value = mock_response

    repos = GitHubRepoService.list_repos(token="ghp_test123")

    assert len(repos) == 2
    assert repos[0].name == "repo-one"
    assert repos[0].private is False
    assert repos[1].name == "repo-two"
    assert repos[1].private is True
    assert repos[1].default_branch == "master"


@patch("chegi.services.github.repo_service.urllib.request.urlopen")
def test_list_repos_empty(mock_urlopen: MagicMock):
    """Tests that list_repos returns empty list when no repos."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps([]).encode()
    mock_urlopen.return_value.__enter__.return_value = mock_response

    repos = GitHubRepoService.list_repos(token="ghp_test123")

    assert repos == []


@patch("chegi.services.github.repo_service.urllib.request.urlopen")
def test_list_repos_raises_auth_error(mock_urlopen: MagicMock):
    """Tests that list_repos raises GitHubAuthError on 401."""
    from urllib.error import HTTPError

    mock_urlopen.side_effect = HTTPError(
        url="https://api.github.com/user/repos",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=None,
    )

    with pytest.raises(GitHubAuthError, match="invalid or has been revoked"):
        GitHubRepoService.list_repos(token="bad-token")


# ── push_project ────────────────────────────────────────────


@patch("chegi.services.github.repo_service.subprocess.run")
def test_push_project_adds_remote_and_pushes(mock_run: MagicMock):
    """Tests that push_project adds a remote and pushes."""
    # First call: remote get-url fails (no remote yet)
    # Second call: git remote add
    # Third call: git push
    mock_run.side_effect = [
        MagicMock(
            returncode=128, stdout="", stderr="fatal: not a git repository"
        ),  # no remote
        MagicMock(returncode=0),  # remote add
        MagicMock(returncode=0),  # push
    ]

    url = GitHubRepoService.push_project(
        project_path=Path("/tmp/test-project"),
        remote_url="git@github.com:user/my-project.git",
    )

    assert url == "git@github.com:user/my-project.git"
    assert mock_run.call_count == 3


@patch("chegi.services.github.repo_service.subprocess.run")
def test_push_project_updates_existing_remote(mock_run: MagicMock):
    """Tests that push_project updates remote URL when it differs."""
    mock_run.side_effect = [
        MagicMock(stdout="git@github.com:old/url.git", returncode=0),  # remote exists
        MagicMock(returncode=0),  # set-url
        MagicMock(returncode=0),  # push
    ]

    url = GitHubRepoService.push_project(
        project_path=Path("/tmp/test-project"),
        remote_url="git@github.com:user/my-project.git",
    )

    assert url == "git@github.com:user/my-project.git"
    assert mock_run.call_count == 3
    mock_run.assert_any_call(
        ["git", "remote", "set-url", "origin", "git@github.com:user/my-project.git"],
        cwd=str(Path("/tmp/test-project")),
        capture_output=True,
        check=True,
    )


@patch("chegi.services.github.repo_service.subprocess.run")
def test_push_project_raises_error_on_failure(mock_run: MagicMock):
    """Tests that push_project raises GitHubError on git failure."""
    mock_run.side_effect = subprocess.CalledProcessError(
        128, "git", stderr="fatal: not a git repository"
    )

    with pytest.raises(GitHubError, match="not a git repository"):
        GitHubRepoService.push_project(
            project_path=Path("/tmp/test-project"),
            remote_url="git@github.com:user/my-project.git",
        )
