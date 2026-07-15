"""Tests for the auth CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app
from chegi.services.auth.exceptions import TokenValidationError

runner = CliRunner()


# ── login ─────────────────────────────────────────────────────


@patch("chegi.cli.commands.auth._check_git_installed")
@patch("chegi.cli.commands.auth._has_credential_helper")
@patch("chegi.services.auth.auth_service.AuthService.validate_token")
@patch("chegi.services.auth.auth_service.AuthService._load_data")
@patch("chegi.services.auth.auth_service.AuthService._save_data")
@patch("chegi.services.auth.auth_service.AuthService._ensure_key")
def test_login_non_interactive(
    mock_key: MagicMock,
    mock_save: MagicMock,
    mock_load: MagicMock,
    mock_validate: MagicMock,
    mock_has_helper: MagicMock,
    mock_git_installed: MagicMock,
):
    """Tests non-interactive login with --token and --username."""
    mock_key.return_value = b"test-key-here"
    mock_load.return_value = {}
    mock_validate.return_value = ("ad-alwer", ["repo"])
    mock_git_installed.return_value = False

    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--token",
            "ghp_test123",
            "--username",
            "ad-alwer",
            "--provider",
            "github",
            "--label",
            "personal",
        ],
    )

    assert result.exit_code == 0
    assert "Token valid" in result.stdout
    assert "ad-alwer" in result.stdout


@patch("chegi.cli.commands.auth._check_git_installed")
@patch("chegi.cli.commands.auth._has_credential_helper")
@patch("chegi.services.auth.auth_service.AuthService.validate_token")
@patch("chegi.services.auth.auth_service.AuthService._load_data")
@patch("chegi.services.auth.auth_service.AuthService._save_data")
@patch("chegi.services.auth.auth_service.AuthService._ensure_key")
def test_login_uses_api_username(
    mock_key: MagicMock,
    mock_save: MagicMock,
    mock_load: MagicMock,
    mock_validate: MagicMock,
    mock_has_helper: MagicMock,
    mock_git_installed: MagicMock,
):
    """Tests that the API-returned username overrides the --username flag."""
    mock_key.return_value = b"test-key-here"
    mock_load.return_value = {}
    mock_validate.return_value = ("from-api", ["repo"])
    mock_git_installed.return_value = False

    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--token",
            "ghp_test456",
            "--username",
            "local-user",
            "--provider",
            "github",
        ],
    )

    assert result.exit_code == 0
    assert "from-api" in result.stdout


@patch("chegi.services.auth.auth_service.AuthService.validate_token")
def test_login_invalid_token(mock_validate: MagicMock):
    """Tests that an invalid token returns a non-zero exit code."""
    mock_validate.side_effect = TokenValidationError("Token is invalid.")

    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--token",
            "ghp_bad",
            "--username",
            "user",
            "--provider",
            "github",
        ],
    )

    assert result.exit_code != 0
    assert "invalid" in result.stdout.lower() or "Token" in result.stdout


@patch("chegi.cli.commands.auth._check_git_installed")
@patch("chegi.cli.commands.auth._has_credential_helper")
@patch("chegi.cli.commands.auth._setup_git_credential_helper")
@patch("chegi.services.auth.auth_service.AuthService.validate_token")
@patch("chegi.services.auth.auth_service.AuthService._load_data")
@patch("chegi.services.auth.auth_service.AuthService._save_data")
@patch("chegi.services.auth.auth_service.AuthService._ensure_key")
def test_login_sets_up_credential_helper(
    mock_key: MagicMock,
    mock_save: MagicMock,
    mock_load: MagicMock,
    mock_validate: MagicMock,
    mock_setup: MagicMock,
    mock_has_helper: MagicMock,
    mock_git_installed: MagicMock,
):
    """Tests non-interactive login auto-sets up the credential helper."""
    mock_key.return_value = b"test-key-here"
    mock_load.return_value = {}
    mock_validate.return_value = ("user", ["repo"])
    mock_git_installed.return_value = True
    mock_has_helper.return_value = False

    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--token",
            "ghp_setup_test",
            "--username",
            "user",
            "--provider",
            "github",
        ],
    )

    assert result.exit_code == 0
    assert "Credential helper registered" in result.stdout
    mock_setup.assert_called_once_with("github.com")


@patch("chegi.cli.commands.auth._check_git_installed")
@patch("chegi.cli.commands.auth._has_credential_helper")
@patch("chegi.services.auth.auth_service.AuthService.validate_token")
@patch("chegi.services.auth.auth_service.AuthService._load_data")
@patch("chegi.services.auth.auth_service.AuthService._save_data")
@patch("chegi.services.auth.auth_service.AuthService._ensure_key")
def test_login_credential_helper_already_set(
    mock_key: MagicMock,
    mock_save: MagicMock,
    mock_load: MagicMock,
    mock_validate: MagicMock,
    mock_has_helper: MagicMock,
    mock_git_installed: MagicMock,
):
    """Tests login messages when credential helper is already configured."""
    mock_key.return_value = b"test-key-here"
    mock_load.return_value = {}
    mock_validate.return_value = ("user", ["repo"])
    mock_git_installed.return_value = True
    mock_has_helper.return_value = True

    result = runner.invoke(
        app,
        [
            "auth",
            "login",
            "--token",
            "ghp_already",
            "--username",
            "user",
            "--provider",
            "github",
        ],
    )

    assert result.exit_code == 0
    assert "already configured" in result.stdout


# ── status ────────────────────────────────────────────────────


@patch("chegi.services.auth.auth_service.AuthService._load_data")
@patch("chegi.services.auth.auth_service.AuthService._ensure_key")
def test_status_shows_credentials(
    mock_key: MagicMock,
    mock_load: MagicMock,
):
    """Tests that status displays stored credentials."""
    mock_key.return_value = b"test"
    mock_load.return_value = {
        "github-default": {
            "provider": "github",
            "label": "default",
            "username": "ad-alwer",
            "token": "ghp_xxx",
            "host": "github.com",
            "api_url": "",
            "is_default": True,
            "scope_hint": "repo",
        }
    }

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "ad-alwer" in result.stdout
    assert "github" in result.stdout.lower() or "GitHub" in result.stdout


@patch("chegi.services.auth.auth_service.AuthService._load_data")
@patch("chegi.services.auth.auth_service.AuthService._ensure_key")
def test_status_empty(mock_key: MagicMock, mock_load: MagicMock):
    """Tests that status shows a message when no credentials exist."""
    mock_key.return_value = b"test"
    mock_load.return_value = {}

    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "No credentials stored" in result.stdout


# ── logout ────────────────────────────────────────────────────


@patch("chegi.cli.commands.auth._remove_git_credential_helper")
@patch("chegi.services.auth.auth_service.AuthService.get_credential_by_label")
@patch("chegi.services.auth.auth_service.AuthService._load_data")
@patch("chegi.services.auth.auth_service.AuthService._save_data")
@patch("chegi.services.auth.auth_service.AuthService._ensure_key")
def test_logout_non_interactive(
    mock_key: MagicMock,
    mock_save: MagicMock,
    mock_load: MagicMock,
    mock_get_cred: MagicMock,
    mock_remove_helper: MagicMock,
):
    """Tests logout with --label flag."""
    from chegi.services.auth.models import AuthProvider, Credential

    mock_key.return_value = b"test"
    mock_load.return_value = {
        "github-default": {
            "provider": "github",
            "label": "default",
            "username": "u",
            "token": "t",
            "host": "github.com",
            "api_url": "",
            "is_default": True,
            "scope_hint": "",
        }
    }
    mock_get_cred.return_value = Credential(
        provider=AuthProvider.GITHUB,
        label="default",
        username="u",
        token="t",
        host="github.com",
        is_default=True,
    )

    result = runner.invoke(app, ["auth", "logout", "--label", "default"])

    assert result.exit_code == 0
    assert "removed" in result.stdout.lower()
    mock_remove_helper.assert_called_once_with("github.com")


def test_logout_nonexistent_label():
    """Tests logout with a label that doesn't exist."""
    result = runner.invoke(app, ["auth", "logout", "--label", "ghost"])

    assert result.exit_code == 0
    assert "not found" in result.stdout.lower()


@patch("chegi.cli.commands.auth._remove_git_credential_helper")
@patch("chegi.services.auth.auth_service.AuthService.get_credential_by_label")
@patch("chegi.services.auth.auth_service.AuthService._load_data")
@patch("chegi.services.auth.auth_service.AuthService._save_data")
@patch("chegi.services.auth.auth_service.AuthService._ensure_key")
def test_logout_removes_credential_helper(
    mock_key: MagicMock,
    mock_save: MagicMock,
    mock_load: MagicMock,
    mock_get_cred: MagicMock,
    mock_remove_helper: MagicMock,
):
    """Tests logout removes the git credential helper for the host."""
    from chegi.services.auth.models import AuthProvider, Credential

    mock_key.return_value = b"test"
    mock_load.return_value = {
        "github-default": {
            "provider": "github",
            "label": "default",
            "username": "u",
            "token": "t",
            "host": "github.com",
            "api_url": "",
            "is_default": True,
            "scope_hint": "",
        }
    }
    mock_get_cred.return_value = Credential(
        provider=AuthProvider.GITHUB,
        label="default",
        username="u",
        token="t",
        host="github.com",
        is_default=True,
    )

    result = runner.invoke(app, ["auth", "logout", "--label", "default"])

    assert result.exit_code == 0
    mock_remove_helper.assert_called_once_with("github.com")


@patch("chegi.cli.commands.auth._remove_git_credential_helper")
@patch("chegi.services.auth.auth_service.AuthService.status")
@patch("chegi.services.auth.auth_service.AuthService.logout")
def test_logout_all_removes_helpers(
    mock_logout: MagicMock,
    mock_status: MagicMock,
    mock_remove_helper: MagicMock,
):
    """Tests that --all removes credential helpers for all stored credentials."""
    from chegi.services.auth.models import AuthProvider, Credential

    mock_status.return_value = [
        Credential(
            provider=AuthProvider.GITHUB,
            label="gh",
            username="u1",
            token="t1",
            host="github.com",
            is_default=True,
        ),
        Credential(
            provider=AuthProvider.GITLAB,
            label="gl",
            username="u2",
            token="t2",
            host="gitlab.com",
            is_default=True,
        ),
    ]

    result = runner.invoke(app, ["auth", "logout", "--all"])

    assert result.exit_code == 0
    assert "All credentials removed" in result.stdout
    assert mock_remove_helper.call_count == 2
    mock_remove_helper.assert_any_call("github.com")
    mock_remove_helper.assert_any_call("gitlab.com")


# ── switch ────────────────────────────────────────────────────


@patch("chegi.services.auth.auth_service.AuthService._load_data")
@patch("chegi.services.auth.auth_service.AuthService._save_data")
@patch("chegi.services.auth.auth_service.AuthService._ensure_key")
def test_switch_non_interactive(
    mock_key: MagicMock,
    mock_save: MagicMock,
    mock_load: MagicMock,
):
    """Tests switch with a label argument."""
    mock_key.return_value = b"test"
    mock_load.return_value = {
        "github-a": {
            "provider": "github",
            "label": "a",
            "username": "user_a",
            "token": "tok_a",
            "host": "github.com",
            "api_url": "",
            "is_default": True,
            "scope_hint": "",
        },
        "github-b": {
            "provider": "github",
            "label": "b",
            "username": "user_b",
            "token": "tok_b",
            "host": "github.com",
            "api_url": "",
            "is_default": False,
            "scope_hint": "",
        },
    }

    result = runner.invoke(app, ["auth", "switch", "b"])

    assert result.exit_code == 0
    assert "switched" in result.stdout.lower() or "default" in result.stdout.lower()


def test_switch_nonexistent_label():
    """Tests switch with a label that doesn't exist."""
    result = runner.invoke(app, ["auth", "switch", "ghost"])

    assert result.exit_code == 0
    assert "not found" in result.stdout.lower()


# ── get-credential (hidden) ───────────────────────────────────


def test_get_credential_returns_username_and_password():
    """Tests the hidden get-credential helper."""
    cred_data = {
        "github-default": {
            "provider": "github",
            "label": "default",
            "username": "ad-alwer",
            "token": "ghp_secret",
            "host": "github.com",
            "api_url": "",
            "is_default": True,
            "scope_hint": "",
        }
    }

    with patch(
        "chegi.services.auth.auth_service.AuthService._load_data",
        return_value=cred_data,
    ):
        with patch(
            "chegi.services.auth.auth_service.AuthService._ensure_key",
            return_value=b"test",
        ):
            result = runner.invoke(
                app,
                ["auth", "get-credential"],
                input="protocol=https\nhost=github.com\n",
            )

    assert result.exit_code == 0
    assert "username=ad-alwer" in result.stdout
    assert "password=ghp_secret" in result.stdout


def test_get_credential_no_match():
    """Tests get-credential when no credential matches the host."""
    cred_data = {
        "github-default": {
            "provider": "github",
            "label": "default",
            "username": "u",
            "token": "t",
            "host": "github.com",
            "api_url": "",
            "is_default": True,
            "scope_hint": "",
        }
    }

    with patch(
        "chegi.services.auth.auth_service.AuthService._load_data",
        return_value=cred_data,
    ):
        with patch(
            "chegi.services.auth.auth_service.AuthService._ensure_key",
            return_value=b"test",
        ):
            result = runner.invoke(
                app,
                ["auth", "get-credential"],
                input="protocol=https\nhost=gitlab.com\n",
            )

    assert result.exit_code == 0
    assert result.stdout == ""
