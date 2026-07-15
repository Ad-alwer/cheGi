"""Service for creating and managing GitHub repositories via API."""

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import List

from chegi.services.github.exceptions import (
    GitHubAuthError,
    GitHubError,
    RepoExistsError,
)
from chegi.services.github.models import GitHubRepo

GITHUB_API_BASE = "https://api.github.com"


def _build_headers(token: str) -> dict:
    """Builds standard headers for GitHub API requests.

    Args:
        token: GitHub personal access token.

    Returns:
        Dict of HTTP headers.
    """
    return {
        "Authorization": f"Bearer {token}",
        "User-Agent": "cheGi",
        "Accept": "application/json",
    }


def _parse_repo(data: dict) -> GitHubRepo:
    """Converts a GitHub API response dict into a GitHubRepo.

    Args:
        data: The API response dict for a repository.

    Returns:
        A GitHubRepo instance.
    """
    return GitHubRepo(
        name=data.get("name", ""),
        full_name=data.get("full_name", ""),
        html_url=data.get("html_url", ""),
        private=data.get("private", False),
        default_branch=data.get("default_branch", "main"),
        description=data.get("description") or "",
    )


class GitHubRepoService:
    """Service for creating and querying GitHub repositories."""

    @staticmethod
    def create_repo(
        name: str,
        token: str,
        private: bool = False,
        description: str = "",
    ) -> GitHubRepo:
        """Creates a new repository on GitHub.

        Args:
            name: Repository name.
            token: GitHub personal access token.
            private: Whether the repo should be private.
            description: Optional description.

        Returns:
            The created GitHubRepo.

        Raises:
            GitHubAuthError: If the token is invalid.
            RepoExistsError: If the repo already exists.
            GitHubError: For other API errors.
        """
        payload = {
            "name": name,
            "private": private,
            "description": description,
            "auto_init": False,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{GITHUB_API_BASE}/user/repos",
            data=body,
            headers=_build_headers(token),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                return _parse_repo(data)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise GitHubAuthError(
                    "GitHub token is invalid or has been revoked."
                ) from e
            if e.code == 422:
                try:
                    err_body = json.loads(e.read())
                    msg = err_body.get("message", "")
                    errors = err_body.get("errors", [])
                    if any(
                        err.get("message", "").startswith("name already exists")
                        for err in errors
                    ):
                        raise RepoExistsError(
                            f"Repository '{name}' already exists on your account."
                        ) from e
                except (json.JSONDecodeError, AttributeError):
                    pass
                raise GitHubError(
                    f"Unable to create repository: {msg or e.reason}"
                ) from e
            raise GitHubError(f"GitHub API returned HTTP {e.code}: {e.reason}") from e
        except (urllib.error.URLError, OSError) as e:
            raise GitHubError(f"Could not reach GitHub API: {e}") from e

    @staticmethod
    def list_repos(
        token: str,
        per_page: int = 50,
        sort: str = "updated",
    ) -> List[GitHubRepo]:
        """Lists repositories for the authenticated user.

        Args:
            token: GitHub personal access token.
            per_page: Number of repos per page (max 100).
            sort: Sort criteria (updated, created, full_name, pushed).

        Returns:
            List of GitHubRepo objects.

        Raises:
            GitHubAuthError: If the token is invalid.
            GitHubError: For other API errors.
        """
        repos: List[GitHubRepo] = []
        url = f"{GITHUB_API_BASE}/user/repos?per_page={per_page}&sort={sort}"
        req = urllib.request.Request(url, headers=_build_headers(token))

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                for item in data:
                    repos.append(_parse_repo(item))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise GitHubAuthError(
                    "GitHub token is invalid or has been revoked."
                ) from e
            raise GitHubError(f"GitHub API returned HTTP {e.code}: {e.reason}") from e
        except (urllib.error.URLError, OSError) as e:
            raise GitHubError(f"Could not reach GitHub API: {e}") from e

        return repos

    @staticmethod
    def push_project(
        project_path: Path,
        remote_url: str,
        branch: str = "main",
        remote_name: str = "origin",
    ) -> str:
        """Adds a remote and pushes the project to GitHub.

        Args:
            project_path: Path to the local Git repository.
            remote_url: The remote URL (git@ or https://).
            branch: Branch name to push.
            remote_name: Remote name (default: origin).

        Returns:
            The full remote URL that was pushed to.

        Raises:
            GitHubError: If git operations fail.
        """
        try:
            # Check if remote already exists
            result = subprocess.run(
                ["git", "remote", "get-url", remote_name],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                existing_url = result.stdout.strip()
                if existing_url != remote_url:
                    subprocess.run(
                        ["git", "remote", "set-url", remote_name, remote_url],
                        cwd=str(project_path),
                        capture_output=True,
                        check=True,
                    )
            else:
                subprocess.run(
                    ["git", "remote", "add", remote_name, remote_url],
                    cwd=str(project_path),
                    capture_output=True,
                    check=True,
                )

            subprocess.run(
                ["git", "push", "-u", remote_name, branch],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                check=True,
            )
            return remote_url
        except subprocess.CalledProcessError as e:
            detail = e.stderr.strip() if e.stderr else str(e)
            raise GitHubError(f"Failed to push to remote: {detail}") from e
        except FileNotFoundError as e:
            raise GitHubError("Git is not installed.") from e
