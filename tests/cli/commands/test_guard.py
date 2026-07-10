from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from chegi.cli.main import app

runner = CliRunner()


@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
def test_guard_fails_when_not_in_git_repo(mock_is_valid_repo: MagicMock):
    # Tests guard command behavior when executed outside a git repository.
    mock_is_valid_repo.return_value = False
    
    result = runner.invoke(app, ["guard"])
    
    assert result.exit_code == 1
    assert "fatal: not a git repository" in result.stdout.lower()


@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
@patch("chegi.cli.commands.guard.SecurityGuard.find_sensitive_files")
@patch("chegi.cli.commands.guard.SecurityGuard.get_staged_files")
def test_guard_success_no_secrets(
    mock_get_staged: MagicMock, 
    mock_find_sensitive: MagicMock, 
    mock_is_valid_repo: MagicMock
):
    # Tests guard command when it is in a git repo and no sensitive files are detected.
    mock_is_valid_repo.return_value = True
    mock_get_staged.return_value = ["clean.py"]
    mock_find_sensitive.return_value = []

    result = runner.invoke(app, ["guard"])
    
    assert result.exit_code == 0
    assert "Security check passed" in result.stdout


@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
@patch("chegi.cli.commands.guard.SecurityGuard.unstage_files")
@patch("chegi.cli.commands.guard.SecurityGuard.find_sensitive_files")
@patch("chegi.cli.commands.guard.SecurityGuard.get_staged_files")
def test_guard_failure_secrets_found_accept_unstage(
    mock_get: MagicMock, 
    mock_find: MagicMock, 
    mock_unstage: MagicMock, 
    mock_is_valid_repo: MagicMock
):
    # Tests guard behavior when secrets are found and user accepts unstaging.
    mock_is_valid_repo.return_value = True
    mock_get.return_value = [".env"]
    mock_find.return_value = [".env"]
    mock_unstage.return_value = True

    result = runner.invoke(app, ["guard"], input="y\n")

    assert result.exit_code == 1
    assert "WARNING: Sensitive files detected" in result.stdout
    assert "Files successfully unstaged" in result.stdout


@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
@patch("chegi.cli.commands.guard.SecurityGuard.unstage_files")
@patch("chegi.cli.commands.guard.SecurityGuard.find_sensitive_files")
@patch("chegi.cli.commands.guard.SecurityGuard.get_staged_files")
def test_guard_failure_secrets_found_with_fix_flag(
    mock_get: MagicMock, 
    mock_find: MagicMock, 
    mock_unstage: MagicMock, 
    mock_is_valid_repo: MagicMock
):
    # Tests guard behavior when secrets are found and --fix flag is used.
    mock_is_valid_repo.return_value = True
    mock_get.return_value = ["secret_key.pem"]
    mock_find.return_value = ["secret_key.pem"]
    mock_unstage.return_value = True

    result = runner.invoke(app, ["guard", "--fix"])

    assert result.exit_code == 1
    assert "WARNING: Sensitive files detected" in result.stdout
    assert "automatically (via --fix)" in result.stdout


@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
@patch("chegi.cli.commands.guard.SecurityGuard.find_sensitive_files")
@patch("chegi.cli.commands.guard.SecurityGuard.get_staged_files")
def test_guard_display_command_quotes_filenames(
    mock_get: MagicMock,
    mock_find: MagicMock,
    mock_is_valid_repo: MagicMock,
):
    # Tests that the displayed `git rm --cached` command quotes filenames safely.
    mock_is_valid_repo.return_value = True
    mock_get.return_value = [".env", "file; rm -rf /", "$(whoami).txt"]
    mock_find.return_value = [".env", "file; rm -rf /", "$(whoami).txt"]

    result = runner.invoke(app, ["guard"])

    assert result.exit_code == 1
    assert "WARNING: Sensitive files detected" in result.stdout
    assert "git rm --cached .env 'file; rm -rf /' '$(whoami).txt'" in result.stdout
