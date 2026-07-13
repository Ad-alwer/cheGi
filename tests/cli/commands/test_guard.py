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
    mock_is_valid_repo: MagicMock,
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
    mock_is_valid_repo: MagicMock,
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
    mock_is_valid_repo: MagicMock,
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


@patch("chegi.cli.commands.guard.GuardHistoryService.print_findings")
@patch("chegi.cli.commands.guard.GuardHistoryService")
@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
def test_guard_history_subcommand(
    mock_is_valid: MagicMock,
    mock_history_cls: MagicMock,
    mock_print: MagicMock,
):
    """Tests guard history subcommand scans and prints findings."""
    mock_is_valid.return_value = True
    mock_instance = mock_history_cls.return_value
    mock_result = MagicMock()
    mock_result.findings = []
    mock_result.total_commits_scanned = 10
    mock_result.total_findings = 0
    mock_instance.scan.return_value = mock_result

    result = runner.invoke(app, ["guard", "history"])

    assert result.exit_code == 0
    mock_instance.scan.assert_called_once()
    mock_print.assert_called_once_with(mock_result)


@patch("chegi.cli.commands.guard.GuardHistoryService.print_findings")
@patch("chegi.cli.commands.guard.GuardHistoryService.generate_report")
@patch("chegi.cli.commands.guard.GuardHistoryService")
@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
def test_guard_history_with_report(
    mock_is_valid: MagicMock,
    mock_history_cls: MagicMock,
    mock_report: MagicMock,
    mock_print: MagicMock,
):
    """Tests guard history --report generates an HTML report."""
    mock_is_valid.return_value = True
    mock_instance = mock_history_cls.return_value
    mock_result = MagicMock()
    mock_result.findings = [MagicMock()]
    mock_result.total_commits_scanned = 10
    mock_result.total_findings = 1
    mock_instance.scan.return_value = mock_result

    result = runner.invoke(app, ["guard", "history", "--report"])

    assert result.exit_code == 0
    mock_instance.scan.assert_called_once()
    mock_report.assert_called_once()


@patch("chegi.cli.commands.guard._handle_history_removal")
@patch("chegi.cli.commands.guard.GuardHistoryService.print_findings")
@patch("chegi.cli.commands.guard.GuardHistoryService")
@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
def test_guard_history_with_fix(
    mock_is_valid: MagicMock,
    mock_history_cls: MagicMock,
    mock_print: MagicMock,
    mock_removal: MagicMock,
):
    """Tests guard history --fix calls the removal handler."""
    mock_is_valid.return_value = True
    mock_instance = mock_history_cls.return_value
    mock_result = MagicMock()
    mock_result.findings = [MagicMock()]
    mock_result.total_commits_scanned = 10
    mock_result.total_findings = 1
    mock_instance.scan.return_value = mock_result

    result = runner.invoke(app, ["guard", "history", "--fix"])

    assert result.exit_code == 0
    mock_instance.scan.assert_called_once()
    mock_removal.assert_called_once()


@patch("chegi.cli.commands.guard.GuardHistoryService.print_findings")
@patch("chegi.cli.commands.guard.GuardHistoryService")
@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
def test_guard_history_fails_not_in_repo(
    mock_is_valid: MagicMock,
    mock_history_cls: MagicMock,
    mock_print: MagicMock,
):
    """Tests guard history fails when not in a git repo."""
    mock_is_valid.return_value = False

    result = runner.invoke(app, ["guard", "history"])

    assert result.exit_code == 1
    assert "fatal: not a git repository" in result.stdout.lower()


# --- strict mode tests ---


@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
@patch("chegi.cli.commands.guard.SecurityGuard.scan_strict")
def test_guard_strict_clean(
    mock_scan_strict: MagicMock,
    mock_is_valid: MagicMock,
):
    """Test guard --strict passes when no sensitive files exist."""
    mock_is_valid.return_value = True
    mock_result_staged = MagicMock(is_safe=True, sensitive_files=[])
    mock_result_unstaged = MagicMock(is_safe=True, sensitive_files=[])
    mock_scan_strict.return_value = (mock_result_staged, mock_result_unstaged)

    result = runner.invoke(app, ["guard", "--strict"])

    assert result.exit_code == 0
    assert "Strict security check passed" in result.stdout


@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
@patch("chegi.cli.commands.guard.SecurityGuard.scan_strict")
@patch("chegi.cli.commands.guard.SecurityGuard.unstage_files")
def test_guard_strict_staged_sensitive_with_fix(
    mock_unstage: MagicMock,
    mock_scan_strict: MagicMock,
    mock_is_valid: MagicMock,
):
    """Test guard --strict --fix auto-unstages sensitive staged files."""
    mock_is_valid.return_value = True
    mock_result_staged = MagicMock(is_safe=False, sensitive_files=[".env"])
    mock_result_unstaged = MagicMock(is_safe=True, sensitive_files=[])
    mock_scan_strict.return_value = (mock_result_staged, mock_result_unstaged)
    mock_unstage.return_value = True

    result = runner.invoke(app, ["guard", "--strict", "--fix"])

    assert result.exit_code == 1
    assert "Sensitive files detected in staging" in result.stdout
    assert "Files successfully unstaged" in result.stdout


@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
@patch("chegi.cli.commands.guard.SecurityGuard.scan_strict")
def test_guard_strict_unstaged_only(
    mock_scan_strict: MagicMock,
    mock_is_valid: MagicMock,
):
    """Test guard --strict warns about unstaged sensitive files."""
    mock_is_valid.return_value = True
    mock_result_staged = MagicMock(is_safe=True, sensitive_files=[])
    mock_result_unstaged = MagicMock(is_safe=False, sensitive_files=[".env"])
    mock_scan_strict.return_value = (mock_result_staged, mock_result_unstaged)

    result = runner.invoke(app, ["guard", "--strict"])

    assert result.exit_code == 1
    assert "Sensitive files detected in working directory" in result.stdout


@patch("chegi.cli.commands.guard.GitClient.is_valid_repo")
@patch("chegi.cli.commands.guard.SecurityGuard.scan_strict")
def test_guard_strict_fails_not_in_repo(
    mock_scan_strict: MagicMock,
    mock_is_valid: MagicMock,
):
    """Test guard --strict fails when not in a git repo."""
    mock_is_valid.return_value = False

    result = runner.invoke(app, ["guard", "--strict"])

    assert result.exit_code == 1
    assert "fatal: not a git repository" in result.stdout.lower()
    mock_scan_strict.assert_not_called()


# --- scan mode tests ---


@patch("chegi.cli.commands.guard.SecurityGuard.scan_directory")
def test_guard_scan_clean(
    mock_scan_dir: MagicMock,
    tmp_path,
):
    """Test guard --scan returns clean when no sensitive files found."""
    mock_scan_dir.return_value = MagicMock(is_safe=True, sensitive_files=[])

    result = runner.invoke(app, ["guard", "--scan", str(tmp_path)])

    assert result.exit_code == 0
    assert "No sensitive files found" in result.stdout


@patch("chegi.cli.commands.guard.SecurityGuard.scan_directory")
def test_guard_scan_finds_sensitive(
    mock_scan_dir: MagicMock,
    tmp_path,
):
    """Test guard --scan reports sensitive files."""
    mock_scan_dir.return_value = MagicMock(
        is_safe=False, sensitive_files=["/path/.env"]
    )

    result = runner.invoke(app, ["guard", "--scan", str(tmp_path)])

    assert result.exit_code == 1
    assert "Found 1 sensitive file(s)" in result.stdout
    assert ".env" in result.stdout
