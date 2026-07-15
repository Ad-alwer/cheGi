"""Tests for AuthService."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chegi.services.auth import AuthProvider, AuthService
from chegi.services.auth.exceptions import TokenValidationError

# ── Encryption helpers ────────────────────────────────────────


def test_ensure_key_creates_key_file(tmp_path: Path):
    """Tests that _ensure_key generates and persists a Fernet key."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        key = AuthService._ensure_key()
    assert len(key) == 44  # Fernet keys are 44 base64 bytes
    assert (tmp_path / "auth.key").is_file()


def test_encrypt_decrypt_roundtrip(tmp_path: Path):
    """Tests that encrypt then decrypt returns the original data."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        original = {"hello": "world", "nested": {"a": 1}}
        encrypted = AuthService._encrypt(original)
        decrypted = AuthService._decrypt(encrypted)
    assert decrypted == original


def test_decrypt_corrupted_data_raises_error(tmp_path: Path):
    """Tests that corrupted encrypted data raises AuthError."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        AuthService._ensure_key()
        with pytest.raises(Exception):
            AuthService._decrypt("garbage-data")


# ── Data persistence ──────────────────────────────────────────


def test_load_data_returns_empty_when_no_file(tmp_path: Path):
    """Tests that _load_data returns empty dict when auth.json doesn't exist."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        data = AuthService._load_data()
    assert data == {}


def test_save_and_load_data_persists_encrypted(tmp_path: Path):
    """Tests that saved data can be loaded back correctly."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        data = {"test-key": {"provider": "github", "label": "test", "token": "secret"}}
        AuthService._save_data(data)
        assert AuthService._data_path().is_file()
        loaded = AuthService._load_data()
    assert loaded == data


# ── Provider detection ────────────────────────────────────────


@pytest.mark.parametrize(
    "token, expected",
    [
        ("ghp_abc123def456", AuthProvider.GITHUB),
        ("gho_xyz789", AuthProvider.GITHUB),
        ("github_pat_11abc", AuthProvider.GITHUB),
        ("glpat-abc123", AuthProvider.GITLAB),
        ("unknown-token-format", None),
    ],
)
def test_detect_provider(token, expected):
    """Tests magic provider detection from token prefix."""
    assert AuthService.detect_provider(token) == expected


# ── Token validation (mocked) ─────────────────────────────────


@patch("urllib.request.urlopen")
def test_validate_token_github_success(mock_urlopen: MagicMock):
    """Tests successful GitHub token validation."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"login": "ad-alwer"}).encode()
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    username, scopes = AuthService.validate_token(AuthProvider.GITHUB, "ghp_valid")

    assert username == "ad-alwer"
    assert scopes == []


@patch("urllib.request.urlopen")
def test_validate_token_gitlab_success(mock_urlopen: MagicMock):
    """Tests successful GitLab token validation."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {"username": "myuser", "scopes": ["api", "read_user"]}
    ).encode()
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    username, scopes = AuthService.validate_token(AuthProvider.GITLAB, "glpat-valid")

    assert username == "myuser"
    assert scopes == ["api", "read_user"]


@patch("urllib.request.urlopen")
def test_validate_token_401_raises_error(mock_urlopen: MagicMock):
    """Tests that a 401 response raises TokenValidationError."""
    from urllib.error import HTTPError

    mock_urlopen.side_effect = HTTPError(
        "https://api.github.com/user", 401, "Unauthorized", {}, None
    )
    with pytest.raises(TokenValidationError):
        AuthService.validate_token(AuthProvider.GITHUB, "bad-token")


# ── Login flow ────────────────────────────────────────────────


def test_login_stores_credential(tmp_path: Path):
    """Tests that login stores a new credential."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        with patch.object(AuthService, "validate_token") as mock_validate:
            mock_validate.return_value = ("ad-alwer", ["repo"])
            cred = AuthService.login(
                provider=AuthProvider.GITHUB,
                label="personal",
                username="ad-alwer",
                token="ghp_secret",
                make_default=True,
            )
    assert cred.label == "personal"
    assert cred.provider == AuthProvider.GITHUB
    assert cred.username == "ad-alwer"
    assert cred.host == "github.com"
    assert cred.is_default is True


def test_login_uses_api_username(tmp_path: Path):
    """Tests that the API-returned username takes priority."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        with patch.object(AuthService, "validate_token") as mock_validate:
            mock_validate.return_value = ("from-api", ["repo"])
            cred = AuthService.login(
                provider=AuthProvider.GITHUB,
                label="personal",
                username="user-provided",
                token="ghp_secret",
            )
    assert cred.username == "from-api"


def test_login_with_make_default_un_sets_others(tmp_path: Path):
    """Tests that marking a credential as default un-defaults others on same host."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        with patch.object(AuthService, "validate_token") as mock_validate:
            mock_validate.return_value = ("user", ["repo"])
            AuthService.login(
                provider=AuthProvider.GITHUB,
                label="old",
                username="user",
                token="ghp_old",
                make_default=True,
            )
            AuthService.login(
                provider=AuthProvider.GITHUB,
                label="new",
                username="user",
                token="ghp_new",
                make_default=True,
            )
            creds = AuthService.status()
            old = [c for c in creds if c.label == "old"][0]
            new = [c for c in creds if c.label == "new"][0]
            assert old.is_default is False
            assert new.is_default is True


# ── Status ────────────────────────────────────────────────────


def test_status_returns_all_credentials(tmp_path: Path):
    """Tests that status returns all stored credentials."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        with patch.object(AuthService, "validate_token") as mock_validate:
            mock_validate.return_value = ("user", ["repo"])
            AuthService.login(AuthProvider.GITHUB, "personal", "u1", "tok1")
            AuthService.login(AuthProvider.GITLAB, "work", "u2", "tok2")
            creds = AuthService.status()
    assert len(creds) == 2


# ── Logout ────────────────────────────────────────────────────


def test_logout_removes_credential(tmp_path: Path):
    """Tests that logout removes a credential by label."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        with patch.object(AuthService, "validate_token") as mock_validate:
            mock_validate.return_value = ("user", ["repo"])
            AuthService.login(AuthProvider.GITHUB, "personal", "u1", "tok1")
            assert len(AuthService.status()) == 1
            result = AuthService.logout("personal")
    assert result is True
    assert len(AuthService.status()) == 0


def test_logout_unknown_label_returns_false(tmp_path: Path):
    """Tests that logout returns False for a non-existent label."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        assert AuthService.logout("nonexistent") is False


# ── Switch ────────────────────────────────────────────────────


def test_switch_changes_default(tmp_path: Path):
    """Tests that switch changes the default credential for a host."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        with patch.object(AuthService, "validate_token") as mock_validate:
            mock_validate.return_value = ("user", ["repo"])
            AuthService.login(
                AuthProvider.GITHUB, "first", "u1", "tok1", make_default=True
            )
            AuthService.login(
                AuthProvider.GITHUB, "second", "u2", "tok2", make_default=False
            )
            switched = AuthService.switch("second")
            assert switched is not None
            assert switched.is_default is True
            creds = AuthService.status()
            first = [c for c in creds if c.label == "first"][0]
            assert first.is_default is False


def test_switch_unknown_label_returns_none(tmp_path: Path):
    """Tests that switch returns None for unknown label."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        assert AuthService.switch("nonexistent") is None


# ── get_credential_for_host ───────────────────────────────────


def test_get_credential_for_host_returns_default(tmp_path: Path):
    """Tests that get_credential_for_host returns the default credential."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        with patch.object(AuthService, "validate_token") as mock_validate:
            mock_validate.return_value = ("user", ["repo"])
            AuthService.login(
                AuthProvider.GITHUB, "personal", "u1", "tok1", make_default=True
            )
            cred = AuthService.get_credential_for_host("github.com")
            assert cred is not None
            assert cred.username == "user"


def test_get_credential_for_host_no_match_returns_none(tmp_path: Path):
    """Tests that get_credential_for_host returns None when no match."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        cred = AuthService.get_credential_for_host("unknown.com")
        assert cred is None


# ── get_token ─────────────────────────────────────────────────


def test_get_token_returns_default(tmp_path: Path):
    """Tests that get_token returns the token for the default credential."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        with patch.object(AuthService, "validate_token") as mock_validate:
            mock_validate.return_value = ("user", [])
            AuthService.login(AuthProvider.GITHUB, "personal", "u1", "ghp_secret")
            token = AuthService.get_token(AuthProvider.GITHUB)
            assert token == "ghp_secret"


def test_get_token_no_creds_returns_none(tmp_path: Path):
    """Tests that get_token returns None when no credentials exist."""
    with patch("chegi.services.auth.auth_service.AUTH_DIR", tmp_path):
        assert AuthService.get_token(AuthProvider.GITHUB) is None
