"""Tests for the WizardService class."""

from pathlib import Path
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
def test_get_git_version_returns_version(mock_run: MagicMock):
    """Test that _get_git_version returns the version string."""
    mock_run.return_value = MagicMock(stdout="git version 2.43.0\n", stderr="")
    result = WizardService._get_git_version()
    assert result == "git version 2.43.0"
    mock_run.assert_called_once_with(
        ["git", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_get_git_version_returns_none(mock_run: MagicMock):
    """Test that _get_git_version returns None when git is missing."""
    from subprocess import CalledProcessError

    mock_run.side_effect = CalledProcessError(1, "git")
    assert WizardService._get_git_version() is None


# --- git step tests ---


@patch.object(WizardService, "_log_wizard_event")
@patch.object(WizardService, "_get_git_version")
def test_step_git_check_installed(mock_version: MagicMock, mock_log: MagicMock):
    """Test that _step_git_check reports success when git is found."""
    mock_version.return_value = "git version 2.43.0"
    wizard = WizardService()
    wizard._step_git_check()
    assert wizard._git_available is True


@patch.object(WizardService, "_get_git_version")
def test_step_git_check_not_installed_decline(mock_version: MagicMock):
    """Test that _step_git_check skips when user declines install."""
    mock_version.return_value = None
    with patch(
        "chegi.services.wizard.wizard_service.typer.confirm", return_value=False
    ):
        wizard = WizardService()
        wizard._step_git_check()
    assert wizard._git_available is False


@patch.object(WizardService, "_log_wizard_event")
@patch.object(WizardService, "_get_git_version")
def test_step_git_check_installs_success(mock_version: MagicMock, mock_log: MagicMock):
    """Test that _step_git_check installs git when user accepts."""
    mock_version.return_value = None
    with patch("chegi.services.wizard.wizard_service.typer.confirm", return_value=True):
        with patch(
            "chegi.services.wizard.wizard_service.SystemInstaller.install_package",
            return_value=True,
        ):
            wizard = WizardService()
            wizard._step_git_check()
    assert wizard._git_available is True
    mock_log.assert_called_once_with("git_installed")


@patch.object(WizardService, "_get_git_version")
def test_step_git_check_install_fails(mock_version: MagicMock):
    """Test that _step_git_check handles install failure gracefully."""
    mock_version.return_value = None
    with patch("chegi.services.wizard.wizard_service.typer.confirm", return_value=True):
        with patch(
            "chegi.services.wizard.wizard_service.SystemInstaller.install_package",
            return_value=False,
        ):
            wizard = WizardService()
            wizard._step_git_check()
    assert wizard._git_available is False


@patch.object(WizardService, "_get_git_version")
def test_step_git_check_install_raises(mock_version: MagicMock):
    """Test that _step_git_check handles exception during install."""
    mock_version.return_value = None
    with patch("chegi.services.wizard.wizard_service.typer.confirm", return_value=True):
        with patch(
            "chegi.services.wizard.wizard_service.SystemInstaller.install_package",
            side_effect=RuntimeError("error"),
        ):
            wizard = WizardService()
            wizard._step_git_check()
    assert wizard._git_available is False


# --- identity step tests ---


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
@patch.object(WizardService, "_step_gh_check")
@patch.object(WizardService, "_step_ssh_key")
@patch.object(WizardService, "_step_project_config")
@patch.object(WizardService, "_mark_completed")
def test_execute_runs_all_steps(
    mock_mark: MagicMock,
    mock_config: MagicMock,
    mock_ssh: MagicMock,
    mock_gh: MagicMock,
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
    mock_gh.assert_called_once()
    mock_ssh.assert_called_once()
    mock_config.assert_called_once()
    mock_mark.assert_called_once()


@patch("chegi.services.wizard.wizard_service.os.path.isfile")
@patch.object(WizardService, "_step_git_check")
@patch.object(WizardService, "_step_identity")
@patch.object(WizardService, "_step_gh_check")
@patch.object(WizardService, "_step_ssh_key")
@patch.object(WizardService, "_step_project_config")
@patch.object(WizardService, "_mark_completed")
def test_execute_skips_when_marker_exists(
    mock_mark: MagicMock,
    mock_config: MagicMock,
    mock_ssh: MagicMock,
    mock_gh: MagicMock,
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
    mock_gh.assert_not_called()
    mock_ssh.assert_not_called()
    mock_config.assert_not_called()
    mock_mark.assert_not_called()


@patch("chegi.services.wizard.wizard_service.os.path.isfile")
@patch("chegi.services.wizard.wizard_service.sys.stdin.isatty")
@patch.object(WizardService, "_step_git_check")
@patch.object(WizardService, "_step_identity")
@patch.object(WizardService, "_step_gh_check")
@patch.object(WizardService, "_step_ssh_key")
@patch.object(WizardService, "_step_project_config")
@patch.object(WizardService, "_mark_completed")
def test_execute_skips_when_not_tty(
    mock_mark: MagicMock,
    mock_config: MagicMock,
    mock_ssh: MagicMock,
    mock_gh: MagicMock,
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
    mock_gh.assert_not_called()
    mock_ssh.assert_not_called()
    mock_config.assert_not_called()
    mock_mark.assert_not_called()


# --- SSH key step tests ---


def test_find_ssh_keys_returns_empty_when_dir_missing(tmp_path: Path):
    """Test that _find_ssh_keys returns empty list when .ssh dir is missing."""
    result = WizardService._find_ssh_keys(tmp_path / "nonexistent")
    assert result == []


def test_find_ssh_keys_finds_key_pairs(tmp_path: Path):
    """Test that _find_ssh_keys returns key names with both private and pub."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    for key in ("id_ed25519", "id_rsa"):
        (ssh_dir / key).write_text("private")
        (ssh_dir / f"{key}.pub").write_text("public")
    (ssh_dir / "id_ecdsa").write_text("private-only")  # no .pub

    result = WizardService._find_ssh_keys(ssh_dir)
    assert sorted(result) == ["id_ed25519", "id_rsa"]


def test_find_ssh_keys_returns_empty_when_no_keys(tmp_path: Path):
    """Test that _find_ssh_keys returns empty list when .ssh has no keys."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "config").write_text("some config")

    result = WizardService._find_ssh_keys(ssh_dir)
    assert result == []


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_ssh_agent_has_keys_returns_true(mock_run: MagicMock):
    """Test that _ssh_agent_has_keys returns True when ssh-add -l succeeds."""
    mock_run.return_value = MagicMock(returncode=0)
    assert WizardService._ssh_agent_has_keys() is True
    mock_run.assert_called_once_with(["ssh-add", "-l"], capture_output=True, text=True)


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_ssh_agent_has_keys_returns_false_when_empty(mock_run: MagicMock):
    """Test that _ssh_agent_has_keys returns False when no keys loaded."""
    mock_run.return_value = MagicMock(returncode=1)
    assert WizardService._ssh_agent_has_keys() is False


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_ssh_agent_has_keys_returns_false_when_no_agent(mock_run: MagicMock):
    """Test that _ssh_agent_has_keys returns False when ssh-add not found."""
    mock_run.side_effect = FileNotFoundError()
    assert WizardService._ssh_agent_has_keys() is False


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_generate_ssh_key_success_no_passphrase(mock_run: MagicMock):
    """Test that _generate_ssh_key returns True without passphrase."""
    mock_run.return_value = MagicMock()
    result = WizardService._generate_ssh_key(Path("/tmp/test_key"), "me@a.com")
    assert result is True
    mock_run.assert_called_once_with(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-C",
            "me@a.com",
            "-f",
            "/tmp/test_key",
            "-N",
            "",
        ],
        check=True,
    )


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_generate_ssh_key_success_with_passphrase(mock_run: MagicMock):
    """Test that _generate_ssh_key omits -N when passphrase requested."""
    mock_run.return_value = MagicMock()
    result = WizardService._generate_ssh_key(
        Path("/tmp/test_key"), "me@a.com", use_passphrase=True
    )
    assert result is True
    mock_run.assert_called_once_with(
        ["ssh-keygen", "-t", "ed25519", "-C", "me@a.com", "-f", "/tmp/test_key"],
        check=True,
    )


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_generate_ssh_key_failure(mock_run: MagicMock):
    """Test that _generate_ssh_key returns False on failure."""
    from subprocess import CalledProcessError

    mock_run.side_effect = CalledProcessError(1, "ssh-keygen")
    result = WizardService._generate_ssh_key(Path("/tmp/test_key"), "me@a.com")
    assert result is False


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_add_key_to_agent_success(mock_run: MagicMock):
    """Test that _add_key_to_agent returns True on success."""
    mock_run.return_value = MagicMock()
    result = WizardService._add_key_to_agent(Path("/tmp/key"))
    assert result is True
    mock_run.assert_called_once_with(
        ["ssh-add", "/tmp/key"], capture_output=True, text=True, check=True
    )


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_add_key_to_agent_failure(mock_run: MagicMock):
    """Test that _add_key_to_agent returns False on error."""
    from subprocess import CalledProcessError

    mock_run.side_effect = CalledProcessError(1, "ssh-add")
    result = WizardService._add_key_to_agent(Path("/tmp/key"))
    assert result is False


@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_add_key_to_agent_not_found(mock_run: MagicMock):
    """Test that _add_key_to_agent returns False when ssh-add missing."""
    mock_run.side_effect = FileNotFoundError()
    result = WizardService._add_key_to_agent(Path("/tmp/key"))
    assert result is False


def test_display_public_key_success(tmp_path: Path, capsys):
    """Test that _display_public_key prints the key content."""
    key_file = tmp_path / "id_ed25519.pub"
    key_file.write_text("ssh-ed25519 AAAAC3... me@a.com\n")
    wizard = WizardService()
    wizard._display_public_key(key_file)
    captured = capsys.readouterr()
    assert "ssh-ed25519 AAAAC3... me@a.com" in captured.out
    assert "github.com/settings/ssh/new" in captured.out


def test_display_public_key_error(tmp_path: Path, capsys):
    """Test that _display_public_key handles missing file gracefully."""
    wizard = WizardService()
    wizard._display_public_key(tmp_path / "nope.pub")
    captured = capsys.readouterr()
    assert "Could not read" in captured.out


# --- gh check tests ---


@patch.object(WizardService, "_check_latest_gh_version")
@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_step_gh_check_installed(mock_run: MagicMock, mock_latest: MagicMock):
    """Test that _step_gh_check reports success when gh is installed."""
    mock_run.return_value = MagicMock(stdout="gh version 2.45.0\n", stderr="")
    mock_latest.return_value = "2.45.0"
    with patch(
        "chegi.services.wizard.wizard_service.shutil.which", return_value="/usr/bin/gh"
    ):
        wizard = WizardService()
        wizard._step_gh_check()
    mock_run.assert_called_once_with(
        ["gh", "--version"], capture_output=True, text=True, check=True
    )


@patch("chegi.services.wizard.wizard_service.shutil.which")
def test_step_gh_check_not_installed(mock_which: MagicMock):
    """Test that _step_gh_check warns when gh is missing."""
    mock_which.return_value = None
    with patch(
        "chegi.services.wizard.wizard_service.typer.confirm", return_value=False
    ):
        wizard = WizardService()
        wizard._step_gh_check()
    mock_which.assert_called_with("gh")


@patch("chegi.services.wizard.wizard_service.shutil.which")
@patch.object(WizardService, "_log_wizard_event")
def test_step_gh_check_installs_success(
    mock_log: MagicMock,
    mock_which: MagicMock,
):
    """Test that _step_gh_check installs gh when user accepts."""
    mock_which.return_value = None
    with patch("chegi.services.wizard.wizard_service.typer.confirm", return_value=True):
        with patch(
            "chegi.services.wizard.wizard_service.SystemInstaller.install_package",
            return_value=True,
        ):
            wizard = WizardService()
            wizard._step_gh_check()
    mock_log.assert_called_once_with("gh_installed")


@patch("chegi.services.wizard.wizard_service.shutil.which")
def test_step_gh_check_install_fails(mock_which: MagicMock):
    """Test that _step_gh_check handles install failure gracefully."""
    mock_which.return_value = None
    with patch("chegi.services.wizard.wizard_service.typer.confirm", return_value=True):
        with patch(
            "chegi.services.wizard.wizard_service.SystemInstaller.install_package",
            return_value=False,
        ):
            wizard = WizardService()
            wizard._step_gh_check()


@patch("chegi.services.wizard.wizard_service.shutil.which")
@patch.object(WizardService, "_log_wizard_event")
def test_step_gh_check_handles_http_error(
    mock_log: MagicMock,
    mock_which: MagicMock,
):
    """Test that _step_gh_check handles exception during install."""
    mock_which.return_value = None
    with patch("chegi.services.wizard.wizard_service.typer.confirm", return_value=True):
        with patch(
            "chegi.services.wizard.wizard_service.SystemInstaller.install_package",
            side_effect=RuntimeError("network error"),
        ):
            wizard = WizardService()
            wizard._step_gh_check()


# --- gh version helpers ---


def test_parse_gh_version_extracts_number():
    """Test that _parse_gh_version extracts the version number."""
    result = WizardService._parse_gh_version("gh version 2.45.0 (2024-08-20)")
    assert result == "2.45.0"


def test_parse_gh_version_returns_none_on_mismatch():
    """Test that _parse_gh_version returns None when no version found."""
    result = WizardService._parse_gh_version("gh: command not found")
    assert result is None


@patch("chegi.services.wizard.wizard_service.urllib.request.urlopen")
def test_check_latest_gh_version_success(mock_urlopen: MagicMock):
    """Test that _check_latest_gh_version returns the tag from API."""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"tag_name": "v2.67.0"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response
    result = WizardService._check_latest_gh_version()
    assert result == "2.67.0"


@patch("chegi.services.wizard.wizard_service.urllib.request.urlopen")
def test_check_latest_gh_version_returns_none_on_error(
    mock_urlopen: MagicMock,
):
    """Test that _check_latest_gh_version returns None on network error."""
    mock_urlopen.side_effect = RuntimeError("timeout")
    result = WizardService._check_latest_gh_version()
    assert result is None


@patch.object(WizardService, "_log_wizard_event")
@patch.object(WizardService, "_check_latest_gh_version")
@patch("chegi.services.wizard.wizard_service.subprocess.run")
def test_step_gh_check_upgrade_offered(
    mock_run: MagicMock,
    mock_latest: MagicMock,
    mock_log: MagicMock,
):
    """Test that _step_gh_check offers upgrade when newer version available."""
    mock_run.return_value = MagicMock(stdout="gh version 2.45.0\n", stderr="")
    mock_latest.return_value = "2.67.0"
    with patch(
        "chegi.services.wizard.wizard_service.shutil.which", return_value="/usr/bin/gh"
    ):
        with patch(
            "chegi.services.wizard.wizard_service.typer.confirm", return_value=True
        ):
            with patch(
                "chegi.services.wizard.wizard_service.SystemInstaller.install_package",
                return_value=True,
            ):
                wizard = WizardService()
                wizard._step_gh_check()
    mock_log.assert_called_once_with("gh_upgraded", "2.67.0")


# --- SSH key step tests ---


@patch("chegi.services.wizard.wizard_service.Path.home")
@patch.object(WizardService, "_find_ssh_keys")
@patch.object(WizardService, "_ssh_agent_has_keys")
def test_step_ssh_key_keys_exist_and_loaded(
    mock_agent: MagicMock,
    mock_find: MagicMock,
    mock_home: MagicMock,
    tmp_path: Path,
):
    """Test that _step_ssh_key reports success when keys exist and agent loaded."""
    mock_home.return_value = tmp_path
    mock_find.return_value = ["id_ed25519"]
    mock_agent.return_value = True

    wizard = WizardService()
    wizard._step_ssh_key()

    mock_find.assert_called_once()
    mock_agent.assert_called_once()


@patch("chegi.services.wizard.wizard_service.Path.home")
@patch.object(WizardService, "_find_ssh_keys")
@patch.object(WizardService, "_ssh_agent_has_keys")
@patch.object(WizardService, "_add_key_to_agent")
@patch("chegi.services.wizard.wizard_service.typer.confirm")
def test_step_ssh_key_keys_exist_agent_empty_accepts_add(
    mock_confirm: MagicMock,
    mock_add: MagicMock,
    mock_agent: MagicMock,
    mock_find: MagicMock,
    mock_home: MagicMock,
    tmp_path: Path,
):
    """Test that _step_ssh_key offers to add key when agent has none."""
    mock_home.return_value = tmp_path
    mock_find.return_value = ["id_ed25519"]
    mock_agent.return_value = False
    mock_add.return_value = True
    mock_confirm.return_value = True

    wizard = WizardService()
    wizard._step_ssh_key()

    mock_find.assert_called_once()
    mock_agent.assert_called_once()
    mock_add.assert_called_once_with(tmp_path / ".ssh" / "id_ed25519")


@patch("chegi.services.wizard.wizard_service.Path.home")
@patch.object(WizardService, "_find_ssh_keys")
@patch("chegi.services.wizard.wizard_service.typer.confirm")
def test_step_ssh_key_no_keys_decline_generate(
    mock_confirm: MagicMock,
    mock_find: MagicMock,
    mock_home: MagicMock,
    tmp_path: Path,
):
    """Test that _step_ssh_key skips when user declines generation."""
    mock_home.return_value = tmp_path
    mock_find.return_value = []
    mock_confirm.return_value = False  # decline generation

    wizard = WizardService()
    wizard._step_ssh_key()

    # confirm called once (for "generate?"), no further prompts
    mock_confirm.assert_called_once()


@patch.object(WizardService, "_log_wizard_event")
@patch.object(WizardService, "_add_ssh_config_entry")
@patch.object(WizardService, "_backup_ssh_config")
@patch("chegi.services.wizard.wizard_service.Path.home")
@patch.object(WizardService, "_find_ssh_keys")
@patch.object(WizardService, "_get_git_config")
@patch.object(WizardService, "_generate_ssh_key")
@patch.object(WizardService, "_display_public_key")
@patch.object(WizardService, "_add_key_to_agent")
@patch("chegi.services.wizard.wizard_service.typer.confirm")
@patch("chegi.services.wizard.wizard_service.typer.prompt")
def test_step_ssh_key_generates_and_displays(
    mock_prompt: MagicMock,
    mock_confirm: MagicMock,
    mock_add: MagicMock,
    mock_display: MagicMock,
    mock_gen: MagicMock,
    mock_config: MagicMock,
    mock_find: MagicMock,
    mock_home: MagicMock,
    mock_backup_config: MagicMock,
    mock_add_config: MagicMock,
    mock_log: MagicMock,
    tmp_path: Path,
):
    """Test that _step_ssh_key generates key, displays, and offers to add."""
    mock_home.return_value = tmp_path
    mock_find.return_value = []
    mock_config.return_value = "me@a.com"
    mock_gen.return_value = True
    mock_add.return_value = True
    mock_backup_config.return_value = None  # no existing config
    mock_add_config.return_value = True
    mock_prompt.return_value = "me@a.com"
    # confirms: generate?, passphrase?, add to agent?, add to ~/.ssh/config?
    mock_confirm.side_effect = [True, False, True, True]

    wizard = WizardService()
    wizard._step_ssh_key()

    mock_gen.assert_called_once_with(tmp_path / ".ssh" / "id_ed25519", "me@a.com")
    mock_display.assert_called_once()
    mock_add.assert_called_once_with(tmp_path / ".ssh" / "id_ed25519")
    mock_add_config.assert_called_once_with(tmp_path / ".ssh" / "id_ed25519")


@patch("chegi.services.wizard.wizard_service.ChegiConfig")
@patch("chegi.services.wizard.wizard_service.typer.confirm")
@patch("chegi.services.wizard.wizard_service.typer.prompt")
def test_step_sensitive_patterns_decline(
    mock_prompt: MagicMock,
    mock_confirm: MagicMock,
    mock_config_cls: MagicMock,
):
    """Test that _step_sensitive_patterns skips when user declines."""
    mock_confirm.return_value = False

    wizard = WizardService()
    wizard._step_sensitive_patterns()

    mock_confirm.assert_called_once()
    mock_prompt.assert_not_called()


@patch("chegi.services.wizard.wizard_service.ChegiConfig")
@patch("chegi.services.wizard.wizard_service.typer.confirm")
@patch("chegi.services.wizard.wizard_service.typer.prompt")
def test_step_sensitive_patterns_adds_pattern(
    mock_prompt: MagicMock,
    mock_confirm: MagicMock,
    mock_config_cls: MagicMock,
):
    """Test that _step_sensitive_patterns adds a pattern and does not ask for more."""
    mock_config_instance = MagicMock()
    mock_config_cls.return_value = mock_config_instance
    mock_confirm.side_effect = [True, False]
    mock_prompt.return_value = "my_secret.env"

    wizard = WizardService()
    wizard._step_sensitive_patterns()

    mock_config_cls.assert_called_once()
    mock_config_instance.add_sensitive_pattern.assert_called_once_with("my_secret.env")


@patch("chegi.services.wizard.wizard_service.ChegiConfig")
@patch("chegi.services.wizard.wizard_service.typer.confirm")
@patch("chegi.services.wizard.wizard_service.typer.prompt")
def test_step_sensitive_patterns_empty_pattern_skips(
    mock_prompt: MagicMock,
    mock_confirm: MagicMock,
    mock_config_cls: MagicMock,
):
    """Test that _step_sensitive_patterns skips when empty pattern entered."""
    mock_confirm.return_value = True
    mock_prompt.return_value = ""

    wizard = WizardService()
    wizard._step_sensitive_patterns()

    mock_config_cls.assert_not_called()


def test_backup_key_success(tmp_path: Path):
    """Test that _backup_key copies the key file."""
    key = tmp_path / "id_ed25519"
    key.write_text("private key data")
    pub = tmp_path / "id_ed25519.pub"
    pub.write_text("public key data")

    backup = WizardService._backup_key(key)

    assert backup is not None
    assert backup.name == "id_ed25519.backup"
    assert backup.read_text() == "private key data"
    assert (tmp_path / "id_ed25519.pub.backup").read_text() == "public key data"


def test_backup_key_no_pub(tmp_path: Path):
    """Test that _backup_key works without a .pub file."""
    key = tmp_path / "id_rsa"
    key.write_text("private")
    backup = WizardService._backup_key(key)
    assert backup is not None
    assert backup.read_text() == "private"


def test_backup_key_missing_source(tmp_path: Path):
    """Test that _backup_key returns None when source missing."""
    backup = WizardService._backup_key(tmp_path / "nonexistent")
    assert backup is None


@patch("chegi.services.wizard.wizard_service.shutil.copy2")
def test_backup_ssh_config_exists(mock_copy: MagicMock, tmp_path: Path):
    """Test that _backup_ssh_config backs up an existing config."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    config = ssh_dir / "config"
    config.write_text("some config")
    with patch.object(Path, "home", return_value=tmp_path):
        backup = WizardService._backup_ssh_config()
    assert backup is not None
    assert backup.name == "config.chegi.backup"


@patch.object(Path, "home")
def test_backup_ssh_config_missing(mock_home: MagicMock, tmp_path: Path):
    """Test that _backup_ssh_config returns None when no config exists."""
    mock_home.return_value = tmp_path
    result = WizardService._backup_ssh_config()
    assert result is None


def test_add_ssh_config_entry_new(tmp_path: Path):
    """Test that _add_ssh_config_entry appends a new Host block."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    config = ssh_dir / "config"
    config.write_text("")
    key = tmp_path / "id_ed25519"
    with patch.object(Path, "home", return_value=tmp_path):
        result = WizardService._add_ssh_config_entry(key)
    assert result is True
    content = config.read_text()
    assert "Host github.com" in content
    assert "id_ed25519" in content


def test_add_ssh_config_entry_already_exists(tmp_path: Path):
    """Test that _add_ssh_config_entry skips when entry already exists."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    config = ssh_dir / "config"
    config.write_text("Host github.com\n  IdentityFile ~/.ssh/old\n")
    key = tmp_path / "id_ed25519"
    with patch.object(Path, "home", return_value=tmp_path):
        result = WizardService._add_ssh_config_entry(key)
    assert result is False
    # content unchanged
    assert "old" in config.read_text()


def test_log_wizard_event_creates_log(tmp_path: Path):
    """Test that _log_wizard_event writes to wizard.log."""
    with patch("chegi.services.wizard.wizard_service.WIZARD_MARKER_DIR", tmp_path):
        WizardService._log_wizard_event("test_event", "some detail")
    log_file = tmp_path / "wizard.log"
    assert log_file.is_file()
    content = log_file.read_text()
    assert "test_event" in content
    assert "some detail" in content
