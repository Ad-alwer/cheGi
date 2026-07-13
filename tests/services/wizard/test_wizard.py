"""Tests for the WizardService class."""

from unittest.mock import MagicMock, patch

from chegi.services.wizard import WizardService


@patch("chegi.services.wizard.wizard_service.os.path.isfile")
def test_should_run_returns_true_when_no_marker(mock_isfile: MagicMock):
    """Test that should_run returns True when marker file doesn't exist."""
    mock_isfile.return_value = False
    wizard = WizardService()
    assert wizard.should_run() is True


@patch("chegi.services.wizard.wizard_service.os.path.isfile")
def test_should_run_returns_false_when_marker_exists(mock_isfile: MagicMock):
    """Test that should_run returns False when marker file exists."""
    mock_isfile.return_value = True
    wizard = WizardService()
    assert wizard.should_run() is False


@patch("builtins.open")
@patch("chegi.services.wizard.wizard_service.os.makedirs")
def test_mark_completed_creates_marker(mock_makedirs: MagicMock, mock_open: MagicMock):
    """Test that _mark_completed writes the marker file."""
    wizard = WizardService()
    wizard._mark_completed()
    mock_makedirs.assert_called_once()
    mock_open.assert_called_once()


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_check_git_installed_returns_true(mock_run: MagicMock):
    """Test that _check_git_installed returns True when git is found."""
    mock_run.return_value = MagicMock()
    assert WizardService._check_git_installed() is True
    mock_run.assert_called_once_with(
        ["git", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_check_git_installed_returns_false(mock_run: MagicMock):
    """Test that _check_git_installed returns False when git is missing."""
    from subprocess import CalledProcessError

    mock_run.side_effect = CalledProcessError(1, "git")
    assert WizardService._check_git_installed() is False


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_get_git_config_returns_value(mock_run: MagicMock):
    """Test that _get_git_config returns the config value."""
    mock_run.return_value = MagicMock(stdout="Alice\n", stderr="")
    result = WizardService._get_git_config("user.name")
    assert result == "Alice"
    mock_run.assert_called_once_with(
        ["git", "config", "--global", "user.name"],
        capture_output=True,
        text=True,
        check=True,
    )


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_get_git_config_returns_none_when_not_set(mock_run: MagicMock):
    """Test that _get_git_config returns None when key is not set."""
    from subprocess import CalledProcessError

    mock_run.side_effect = CalledProcessError(1, "git")
    result = WizardService._get_git_config("user.name")
    assert result is None


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_set_git_identity(mock_run: MagicMock):
    """Test that _set_git_identity sets both name and email."""
    mock_run.return_value = MagicMock()
    WizardService._set_git_identity("Alice", "alice@example.com")

    assert mock_run.call_count == 2
    mock_run.assert_any_call(
        ["git", "config", "--global", "user.name", "Alice"],
        check=True,
        capture_output=True,
        text=True,
    )
    mock_run.assert_any_call(
        ["git", "config", "--global", "user.email", "alice@example.com"],
        check=True,
        capture_output=True,
        text=True,
    )


@patch("chegi.services.wizard.wizard_service.os.path.isfile")
@patch("chegi.services.wizard.wizard_service.sys.stdin.isatty")
@patch.object(WizardService, "_step_git_check")
@patch.object(WizardService, "_step_identity")
@patch.object(WizardService, "_step_project_config")
@patch.object(WizardService, "_mark_completed")
def test_execute_runs_all_steps(
    mock_mark: MagicMock,
    mock_config: MagicMock,
    mock_identity: MagicMock,
    mock_git: MagicMock,
    mock_tty: MagicMock,
    mock_isfile: MagicMock,
):
    """Test that execute runs all wizard steps when it should run."""
    mock_isfile.return_value = False
    mock_tty.return_value = True

    wizard = WizardService()
    wizard.execute()

    mock_git.assert_called_once()
    mock_identity.assert_called_once()
    mock_config.assert_called_once()
    mock_mark.assert_called_once()


@patch("chegi.services.wizard.wizard_service.os.path.isfile")
@patch.object(WizardService, "_step_git_check")
@patch.object(WizardService, "_step_identity")
@patch.object(WizardService, "_step_project_config")
@patch.object(WizardService, "_mark_completed")
def test_execute_skips_when_marker_exists(
    mock_mark: MagicMock,
    mock_config: MagicMock,
    mock_identity: MagicMock,
    mock_git: MagicMock,
    mock_isfile: MagicMock,
):
    """Test that execute skips when marker file already exists."""
    mock_isfile.return_value = True

    wizard = WizardService()
    wizard.execute()

    mock_git.assert_not_called()
    mock_identity.assert_not_called()
    mock_config.assert_not_called()
    mock_mark.assert_not_called()


@patch("chegi.services.wizard.wizard_service.os.path.isfile")
@patch("chegi.services.wizard.wizard_service.sys.stdin.isatty")
@patch.object(WizardService, "_step_git_check")
@patch.object(WizardService, "_step_identity")
@patch.object(WizardService, "_step_project_config")
@patch.object(WizardService, "_mark_completed")
def test_execute_skips_when_not_tty(
    mock_mark: MagicMock,
    mock_config: MagicMock,
    mock_identity: MagicMock,
    mock_git: MagicMock,
    mock_tty: MagicMock,
    mock_isfile: MagicMock,
):
    """Test that execute skips when not in a TTY (CI mode)."""
    mock_isfile.return_value = False
    mock_tty.return_value = False

    wizard = WizardService()
    wizard.execute()

    mock_git.assert_not_called()
    mock_identity.assert_not_called()
    mock_config.assert_not_called()
    mock_mark.assert_not_called()
