"""Data models for the auth module."""

from dataclasses import dataclass
from enum import Enum


class AuthProvider(Enum):
    """Supported Git hosting providers."""

    GITHUB = "github"
    GITLAB = "gitlab"


@dataclass
class Credential:
    """Stored credential for a Git provider account.

    Attributes:
        provider: The Git provider (github / gitlab).
        label: Human-friendly label for this account (e.g. "personal", "work").
        username: Git username associated with the token.
        token: The personal access token (encrypted at rest).
        host: Git hostname (e.g. github.com, gitlab.example.com).
        api_url: Base URL for API calls.
        is_default: Whether this is the default account for the host.
        scope_hint: Cached scope hint from validation.
    """

    provider: AuthProvider
    label: str
    username: str
    token: str
    host: str = ""
    api_url: str = ""
    is_default: bool = False
    scope_hint: str = ""
