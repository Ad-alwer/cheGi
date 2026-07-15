"""Tests for GhService."""

from unittest.mock import MagicMock, patch

from chegi.services.github.gh_service import GhService

# ── get_version ─────────────────────────────────────────────


@patch("chegi.services.github.gh_service.subprocess.run")
def test_get_version_returns_version(mock_run: MagicMock):
    """Tests that get_version returns the parsed version string."""
    mock_run.return_value = MagicMock(
        stdout="gh version 2.45.0 (2024-05-01)\n",
        stderr="",
    )
    version = GhService.get_version()
    assert version == "2.45.0"


@patch("chegi.services.github.gh_service.subprocess.run")
def test_get_version_returns_none_when_not_installed(mock_run: MagicMock):
    """Tests that get_version returns None when gh is not installed."""

    mock_run.side_effect = FileNotFoundError()

    version = GhService.get_version()
    assert version is None


@patch("chegi.services.github.gh_service.subprocess.run")
def test_get_version_returns_none_on_nonzero_exit(mock_run: MagicMock):
    """Tests that get_version returns None when gh exits with error."""
    from subprocess import CalledProcessError

    mock_run.side_effect = CalledProcessError(1, "gh")

    version = GhService.get_version()
    assert version is None


# ── check_installed ─────────────────────────────────────────


@patch.object(GhService, "get_version")
def test_check_installed_returns_true(mock_version: MagicMock):
    """Tests that check_installed returns True when gh is installed."""
    mock_version.return_value = "2.45.0"
    assert GhService.check_installed() is True


@patch.object(GhService, "get_version")
def test_check_installed_returns_false(mock_version: MagicMock):
    """Tests that check_installed returns False when gh is not installed."""
    mock_version.return_value = None
    assert GhService.check_installed() is False


# ── check_auth ──────────────────────────────────────────────


@patch("chegi.services.github.gh_service.subprocess.run")
def test_check_auth_returns_true(mock_run: MagicMock):
    """Tests that check_auth returns True when authenticated."""
    mock_run.return_value = MagicMock(returncode=0)
    assert GhService.check_auth() is True
    mock_run.assert_called_once_with(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
        check=False,
    )


@patch("chegi.services.github.gh_service.subprocess.run")
def test_check_auth_returns_false(mock_run: MagicMock):
    """Tests that check_auth returns False when not authenticated."""
    mock_run.return_value = MagicMock(returncode=1)
    assert GhService.check_auth() is False


@patch("chegi.services.github.gh_service.subprocess.run")
def test_check_auth_returns_false_when_not_installed(mock_run: MagicMock):
    """Tests that check_auth returns False when gh is not installed."""
    mock_run.side_effect = FileNotFoundError()
    assert GhService.check_auth() is False


# ── login ───────────────────────────────────────────────────


@patch("chegi.services.github.gh_service.subprocess.run")
def test_login_returns_true(mock_run: MagicMock):
    """Tests that login returns True on success."""
    mock_run.return_value = MagicMock(returncode=0)
    assert GhService.login() is True


@patch("chegi.services.github.gh_service.subprocess.run")
def test_login_returns_false(mock_run: MagicMock):
    """Tests that login returns False on failure."""
    mock_run.return_value = MagicMock(returncode=1)
    assert GhService.login() is False


@patch("chegi.services.github.gh_service.subprocess.run")
def test_login_returns_false_when_not_installed(mock_run: MagicMock):
    """Tests that login returns False when gh is not installed."""
    mock_run.side_effect = FileNotFoundError()
    assert GhService.login() is False


# ── ensure_authenticated ────────────────────────────────────


@patch.object(GhService, "login")
@patch.object(GhService, "check_auth")
def test_ensure_authenticated_already_auth(
    mock_check: MagicMock, mock_login: MagicMock
):
    """Tests that ensure_authenticated returns True when already authenticated."""
    mock_check.return_value = True
    assert GhService.ensure_authenticated() is True
    mock_login.assert_not_called()


@patch.object(GhService, "login")
@patch.object(GhService, "check_auth")
def test_ensure_authenticated_logs_in(mock_check: MagicMock, mock_login: MagicMock):
    """Tests that ensure_authenticated calls login when not authenticated."""
    mock_check.return_value = False
    mock_login.return_value = True
    assert GhService.ensure_authenticated() is True
    mock_login.assert_called_once()


@patch.object(GhService, "login")
@patch.object(GhService, "check_auth")
def test_ensure_authenticated_fails(mock_check: MagicMock, mock_login: MagicMock):
    """Tests that ensure_authenticated returns False when login fails."""
    mock_check.return_value = False
    mock_login.return_value = False
    assert GhService.ensure_authenticated() is False
