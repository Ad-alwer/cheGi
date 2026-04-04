import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

# Updated import to point to the new main architecture
from chegi.cli.main import app
from chegi.git_utils import GitStatus

# Initialize the CLI Runner for testing
runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_valid_git_env():
    """Automatically mocks the Git environment check to pass for all tests."""
    with patch("chegi.cli.check_git_environment") as mock_check:
        mock_check.return_value = (True, "")
        yield mock_check


# ==========================================
# Global Setup & Installation Prompt Tests
# ==========================================


def test_global_setup_git_failure_abort(mock_valid_git_env, tmp_path: Path):
    """Tests if the CLI gracefully exits when the user aborts Git installation."""
    mock_valid_git_env.return_value = (False, "Git version is too old: 2.10.0")
    result = runner.invoke(app, ["scan", str(tmp_path)], input="n\n")

    assert result.exit_code == 1
    assert "Environment Check Failed" in result.stdout
    assert "Installation aborted" in result.stdout


@patch("chegi.cli.SystemInstaller.install_package")
def test_global_setup_git_install_success(
    mock_install: MagicMock, mock_valid_git_env, tmp_path: Path
):
    """Tests successful automatic installation flow when Git is missing."""
    mock_valid_git_env.return_value = (False, "Git is missing")
    mock_install.return_value = True

    result = runner.invoke(app, ["scan", str(tmp_path)], input="y\n")

    assert result.exit_code == 0
    assert "Starting installation process" in result.stdout
    assert "Success! Git has been installed" in result.stdout
    mock_install.assert_called_once_with("git")


# ==========================================
# Scan Command Tests
# ==========================================


def test_scan_invalid_path():
    """Tests the CLI behavior when an invalid directory path is provided."""
    result = runner.invoke(app, ["scan", "/non/existent/mock/path/12345"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout.lower()


@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_with_repos(
    mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path
):
    """Tests successful scan execution and UI output."""
    mock_find_repos.return_value = [tmp_path]
    mock_status = GitStatus(
        path=tmp_path,
        repo_name="mock_project",
        branch="main",
        is_dirty=True,
        has_staged_files=False,
        has_remote=True,
    )
    mock_analyze.return_value = [mock_status]

    result = runner.invoke(app, ["scan", str(tmp_path)])

    assert result.exit_code == 0
    assert "Scanning" in result.stdout
    assert "mock_project" in result.stdout


@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_filter_dirty(
    mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path
):
    """Tests the --dirty flag to ensure clean repositories are filtered out."""
    mock_find_repos.return_value = [Path("/repo1"), Path("/repo2")]

    dirty_repo = GitStatus(
        Path("/repo1"),
        "dirty_repo",
        "main",
        is_dirty=True,
        has_staged_files=False,
        has_remote=True,
    )
    clean_repo = GitStatus(
        Path("/repo2"),
        "clean_repo",
        "main",
        is_dirty=False,
        has_staged_files=False,
        has_remote=True,
    )

    mock_analyze.return_value = [dirty_repo, clean_repo]

    result = runner.invoke(app, ["scan", "--dirty", str(tmp_path)])

    assert "dirty_repo" in result.stdout
    assert "clean_repo" not in result.stdout


@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_filter_staged(
    mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path
):
    """Tests the --staged flag to ensure only repos with staged files are shown."""
    mock_find_repos.return_value = [Path("/repo1"), Path("/repo2")]

    staged_repo = GitStatus(
        Path("/repo1"),
        "staged_repo",
        "main",
        is_dirty=True,
        has_staged_files=True,
        has_remote=True,
    )
    unstaged_repo = GitStatus(
        Path("/repo2"),
        "unstaged_repo",
        "main",
        is_dirty=True,
        has_staged_files=False,
        has_remote=True,
    )

    mock_analyze.return_value = [staged_repo, unstaged_repo]

    result = runner.invoke(app, ["scan", "--staged", str(tmp_path)])

    assert "staged_repo" in result.stdout
    assert "unstaged_repo" not in result.stdout


@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_with_security_flag(
    mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path
):
    """Tests if --security flag correctly triggers the security scanner."""
    mock_find_repos.return_value = [tmp_path]
    mock_status = GitStatus(
        tmp_path, "mock_project", "main", False, False, True, "[green]Safe[/green]"
    )
    mock_analyze.return_value = [mock_status]

    result = runner.invoke(app, ["scan", "--security", str(tmp_path)])

    assert result.exit_code == 0
    mock_analyze.assert_called_once()
    assert "security_scanner" in mock_analyze.call_args.kwargs


# ==========================================
# Guard Command Tests
# ==========================================


@patch("chegi.cli.SecurityGuard.find_sensitive_files")
@patch("chegi.cli.SecurityGuard.get_staged_files")
def test_guard_success_no_secrets(
    mock_get_staged: MagicMock, mock_find_sensitive: MagicMock
):
    """Tests guard command when no sensitive files are detected."""
    mock_get_staged.return_value = ["clean.py"]
    mock_find_sensitive.return_value = []

    result = runner.invoke(app, ["guard"])
    assert result.exit_code == 0


@patch("chegi.cli.SecurityGuard.unstage_files")
@patch("chegi.cli.SecurityGuard.find_sensitive_files")
@patch("chegi.cli.SecurityGuard.get_staged_files")
def test_guard_failure_secrets_found_accept_unstage(mock_get, mock_find, mock_unstage):
    """Tests guard behavior when secrets are found and user accepts unstaging."""
    mock_get.return_value = [".env"]
    mock_find.return_value = [".env"]
    mock_unstage.return_value = True

    result = runner.invoke(app, ["guard"], input="y\n")

    assert result.exit_code == 1
    assert "WARNING: Sensitive files detected" in result.stdout
    assert "Files successfully unstaged" in result.stdout


# ==========================================
# Gitignore Command Tests
# ==========================================


@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
def test_gitignore_success_without_commit(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests successful .gitignore creation but user declines commit."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = ["python", "node"]
    mock_instance.has_existing_gitignore.return_value = False
    mock_instance.is_git_repo.return_value = True

    mock_checkbox.return_value.ask.return_value = ["Python"]

    result = runner.invoke(app, ["gitignore"], input="n\n")

    assert result.exit_code == 0
    assert "Created:" in result.stdout
    assert "Skipping commit" in result.stdout
    mock_instance.generate_gitignore.assert_called_once_with(["python"], ".")
    mock_instance.commit_gitignore.assert_not_called()


@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
def test_gitignore_success_with_commit(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests .gitignore creation with user accepting the automatic commit."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = ["python"]
    mock_instance.has_existing_gitignore.return_value = False
    mock_instance.is_git_repo.return_value = True
    mock_instance.commit_gitignore.return_value = "chore(gitignore): auto add..."

    mock_checkbox.return_value.ask.return_value = ["Python"]

    result = runner.invoke(app, ["gitignore"], input="y\n")

    assert result.exit_code == 0
    assert "Committed with message:" in result.stdout
    mock_instance.commit_gitignore.assert_called_once_with(".")


@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
@patch("chegi.cli.Confirm.ask")
def test_gitignore_overwrite_abort(
    mock_confirm: MagicMock, mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests that the command asks before overwriting and aborts if declined."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = ["python"]
    mock_instance.has_existing_gitignore.return_value = True

    mock_checkbox.return_value.ask.return_value = ["Python"]
    mock_confirm.return_value = False

    result = runner.invoke(app, ["gitignore"])

    assert result.exit_code == 0
    assert "Aborted" in result.stdout
    mock_instance.generate_gitignore.assert_not_called()


@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
def test_gitignore_multiple_languages(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests if multiple selected templates are correctly passed to EnvManager."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = ["python", "node", "ruby"]
    mock_instance.has_existing_gitignore.return_value = False

    mock_checkbox.return_value.ask.return_value = ["Python", "Node"]

    result = runner.invoke(app, ["gitignore"], input="n\n")

    assert result.exit_code == 0
    mock_instance.generate_gitignore.assert_called_once_with(["python", "node"], ".")


@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
def test_gitignore_no_selection_abort(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests the command behavior when the user cancels or selects no languages."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = ["python"]

    mock_checkbox.return_value.ask.return_value = []

    result = runner.invoke(app, ["gitignore"])

    assert result.exit_code == 1
    assert "cancelled or no technologies selected" in result.stdout
    mock_instance.generate_gitignore.assert_not_called()


@patch("chegi.cli.EnvManager")
def test_gitignore_no_templates_found(mock_env_manager: MagicMock):
    """Tests exit with error if no gitignore templates are found in the database."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = []

    result = runner.invoke(app, ["gitignore"])

    assert result.exit_code == 1
    assert "No gitignore templates found" in result.stdout


@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
def test_gitignore_not_a_git_repo(
    mock_checkbox: MagicMock, mock_env_manager: MagicMock
):
    """Tests that the commit prompt is skipped if the target is not a git repository."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_envs_with_gitignore.return_value = ["python"]
    mock_instance.has_existing_gitignore.return_value = False
    mock_instance.is_git_repo.return_value = False

    mock_checkbox.return_value.ask.return_value = ["Python"]

    result = runner.invoke(app, ["gitignore"])

    assert result.exit_code == 0
    assert "Skipped commit: Not a git repository" in result.stdout
    mock_instance.commit_gitignore.assert_not_called()


# ==========================================
# Reword Command Tests
# ==========================================


@patch("chegi.cli.subprocess.run")
def test_reword_head_direct_message(mock_subprocess: MagicMock):
    """Tests rewording HEAD directly by providing the message argument."""
    mock_subprocess.return_value = MagicMock(returncode=0)

    result = runner.invoke(app, ["reword", "chore: new message"])

    assert result.exit_code == 0
    assert "Last commit message updated successfully" in result.stdout

    mock_subprocess.assert_any_call(
        ["git", "commit", "--amend", "-m", "chore: new message"], check=True
    )


@patch("chegi.cli.subprocess.run")
def test_reword_not_a_git_repo(mock_subprocess: MagicMock):
    """Tests reword command when executed outside a git repository."""
    # Force the first subprocess.run (rev-parse) to fail
    mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")
    result = runner.invoke(app, ["reword", "new message"])

    assert result.exit_code == 1
    assert "Not a git repository" in result.stdout


@patch("chegi.cli.subprocess.run")
@patch("chegi.cli.perform_automated_rebase")
@patch("chegi.cli.questionary.select")
@patch("chegi.cli.questionary.text")
def test_reword_last_interactive_head(
    mock_text: MagicMock,
    mock_select: MagicMock,
    mock_rebase: MagicMock,
    mock_subprocess: MagicMock,
):
    """Tests interactive selection of HEAD using --last flag."""
    mock_log_result = MagicMock()
    mock_log_result.stdout = "abc1234 feat: old msg\ndef5678 chore: older msg"

    def mock_run_side_effect(cmd, *args, **kwargs):
        if "log" in cmd:
            return mock_log_result
        if "rev-parse" in cmd and "--short" in cmd:
            return MagicMock(stdout="abc1234\n", returncode=0)
        return MagicMock(returncode=0)

    mock_subprocess.side_effect = mock_run_side_effect

    # User selects the first commit (HEAD)
    mock_select.return_value.ask.return_value = "abc1234 feat: old msg"
    mock_text.return_value.ask.return_value = "feat: updated msg"

    result = runner.invoke(app, ["reword", "--last", "2"])

    assert result.exit_code == 0
    assert "updated successfully" in result.stdout

    # Since the selected commit is HEAD, it should use 'commit --amend' instead of automated rebase
    mock_rebase.assert_not_called()
    mock_subprocess.assert_any_call(
        ["git", "commit", "--amend", "-m", "feat: updated msg"], check=True
    )


@patch("chegi.cli.subprocess.run")
@patch("chegi.cli.perform_automated_rebase")
@patch("chegi.cli.questionary.select")
def test_reword_last_interactive_older_commit(
    mock_select: MagicMock, mock_rebase: MagicMock, mock_subprocess: MagicMock
):
    """Tests modifying an older commit which triggers a rebase."""
    mock_log_result = MagicMock()
    mock_log_result.stdout = "abc1234 feat: head msg\ndef5678 chore: target msg"

    def mock_run_side_effect(cmd, *args, **kwargs):
        if "log" in cmd:
            return mock_log_result
        if "rev-parse" in cmd and "--short" in cmd:
            return MagicMock(stdout="abc1234\n", returncode=0)
        return MagicMock(returncode=0)

    mock_subprocess.side_effect = mock_run_side_effect

    # User selects the older commit
    mock_select.return_value.ask.return_value = "def5678 chore: target msg"

    # Run the command with the new message directly as argument, using --last 2
    result = runner.invoke(app, ["reword", "chore: fixed target msg", "--last", "2"])

    assert result.exit_code == 0
    mock_rebase.assert_called_once_with("def5678", "chore: fixed target msg")
    assert "updated successfully" in result.stdout


@patch("chegi.cli.subprocess.run")
@patch("chegi.cli.questionary.text")
def test_reword_unchanged_message(mock_text: MagicMock, mock_subprocess: MagicMock):
    """Tests that rewording gracefully exits if the message is left unchanged."""

    def mock_run_side_effect(cmd, *args, **kwargs):
        if "rev-parse" in cmd:
            return MagicMock(returncode=0)
        if "log" in cmd:
            return MagicMock(stdout="chore: old message\n", returncode=0)
        return MagicMock(returncode=0)

    mock_subprocess.side_effect = mock_run_side_effect
    mock_text.return_value.ask.return_value = "chore: old message"

    result = runner.invoke(app, ["reword"])
    assert result.exit_code == 0
    assert "Message is unchanged" in result.stdout


@patch("chegi.cli.subprocess.run")
def test_reword_pagination_invalid_range(mock_subprocess: MagicMock):
    mock_subprocess.return_value = MagicMock(returncode=0)
    result = runner.invoke(app, ["reword", "--start", "20", "--end", "15"])
    assert result.exit_code == 1
    assert "Error: --start must be less than --end" in result.stdout


@patch("chegi.cli.subprocess.run")
@patch("chegi.cli.questionary.select")
@patch("chegi.cli.questionary.text")
def test_reword_pagination_start_and_end(
    mock_text: MagicMock, mock_select: MagicMock, mock_subprocess: MagicMock
):
    """Tests the correct calculation of skip and limit when both start and end are provided."""

    def mock_run_side_effect(cmd, *args, **kwargs):
        if "rev-parse" in cmd:
            return MagicMock(stdout="abc1234\n", returncode=0)
        if "log" in cmd and "--format=%h %s" in cmd:
            return MagicMock(
                stdout="abc1234 feat: msg1\ndef5678 chore: msg2\n", returncode=0
            )
        if "log" in cmd and "--format=%B" in cmd:
            return MagicMock(stdout="feat: msg1\n", returncode=0)
        return MagicMock(returncode=0)

    mock_subprocess.side_effect = mock_run_side_effect
    # User selects the first option and changes the message
    mock_select.return_value.ask.return_value = "abc1234 feat: msg1"
    mock_text.return_value.ask.return_value = "feat: new msg1"
    # We want to list commits from index 10 to 15 (skip 10, limit 5)
    result = runner.invoke(app, ["reword", "--start", "10", "--end", "15"])
    assert result.exit_code == 0
    # Verify the correct git log pagination command was constructed
    mock_subprocess.assert_any_call(
        ["git", "log", "--max-count=5", "--skip=10", "--format=%h %s"],
        check=True,
        capture_output=True,
        text=True,
    )


@patch("chegi.cli.subprocess.run")
@patch("chegi.cli.questionary.select")
@patch("chegi.cli.questionary.text")
def test_reword_pagination_only_end(
    mock_text: MagicMock, mock_select: MagicMock, mock_subprocess: MagicMock
):
    """Tests the logic skip = max(0, end - 10) when only --end is provided."""

    def mock_run_side_effect(cmd, *args, **kwargs):
        if "rev-parse" in cmd:
            return MagicMock(stdout="abc1234\n", returncode=0)
        if "log" in cmd and "--format=%h %s" in cmd:
            return MagicMock(stdout="abc1234 feat: msg1\n", returncode=0)
        if "log" in cmd and "--format=%B" in cmd:
            return MagicMock(stdout="feat: msg1\n", returncode=0)
        return MagicMock(returncode=0)

    mock_subprocess.side_effect = mock_run_side_effect

    mock_select.return_value.ask.return_value = "abc1234 feat: msg1"
    mock_text.return_value.ask.return_value = "feat: new msg1"

    # If end is 25, formula says: skip = max(0, 25-10) = 15. limit = 25 - 15 = 10.
    result = runner.invoke(app, ["reword", "--end", "25"])
    assert result.exit_code == 0
    mock_subprocess.assert_any_call(
        ["git", "log", "--max-count=10", "--skip=15", "--format=%h %s"],
        check=True,
        capture_output=True,
        text=True,
    )


# ==========================================
# Sync Command Tests
# ==========================================


@patch("chegi.cli.push_changes")
@patch("chegi.cli.pull_rebase")
@patch("chegi.cli.is_workspace_clean")
def test_sync_clean_workspace_success(
    mock_is_clean: MagicMock, mock_pull: MagicMock, mock_push: MagicMock
):
    """Tests normal sync flow when the workspace has no uncommitted changes."""
    mock_is_clean.return_value = True
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    assert "Synchronization completed successfully" in result.stdout
    mock_pull.assert_called_once()
    mock_push.assert_called_once()


@patch("chegi.cli.is_workspace_clean")
def test_sync_dirty_workspace_abort_first_confirm(mock_is_clean: MagicMock):
    """Tests if sync aborts when the user declines the first stash confirmation."""
    mock_is_clean.return_value = False

    # Input "N" for the first confirmation prompt
    result = runner.invoke(app, ["sync"], input="N\n")

    assert result.exit_code == 1
    assert "Sync aborted" in result.stdout


@patch("chegi.cli.is_workspace_clean")
def test_sync_dirty_workspace_abort_second_confirm(mock_is_clean: MagicMock):
    """Tests if sync aborts when the user declines the second safety confirmation."""
    mock_is_clean.return_value = False

    result = runner.invoke(app, ["sync"], input="Y\nN\n")
    assert result.exit_code == 1
    assert "Sync aborted" in result.stdout


@patch("chegi.cli.pop_stash")
@patch("chegi.cli.push_changes")
@patch("chegi.cli.pull_rebase")
@patch("chegi.cli.stash_changes")
@patch("chegi.cli.is_workspace_clean")
def test_sync_dirty_workspace_full_success(
    mock_is_clean, mock_stash, mock_pull, mock_push, mock_pop
):
    mock_is_clean.return_value = False

    # Input "Y" for both confirmations
    result = runner.invoke(app, ["sync"], input="Y\nY\n")
    assert result.exit_code == 0
    assert "Synchronization completed successfully" in result.stdout

    # Developer Note: Ensure all 4 git operations were called in order
    mock_stash.assert_called_once()
    mock_pull.assert_called_once()
    mock_push.assert_called_once()
    mock_pop.assert_called_once()


@patch("chegi.cli.pull_rebase")
@patch("chegi.cli.is_workspace_clean")
def test_sync_pull_rebase_conflict(mock_is_clean: MagicMock, mock_pull: MagicMock):
    """Tests if sync handles a git pull --rebase failure (e.g., merge conflict)."""
    mock_is_clean.return_value = True
    mock_pull.side_effect = RuntimeError("Git rebase conflict detected.")
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 1
    assert "Conflict or error during pull" in result.stdout


@patch("chegi.cli.pop_stash")
@patch("chegi.cli.push_changes")
@patch("chegi.cli.pull_rebase")
@patch("chegi.cli.stash_changes")
@patch("chegi.cli.is_workspace_clean")
def test_sync_pop_stash_conflict_warning(
    mock_is_clean, mock_stash, mock_pull, mock_push, mock_pop
):
    mock_is_clean.return_value = False
    mock_pop.side_effect = RuntimeError("Auto-merging failed")
    result = runner.invoke(app, ["sync"], input="Y\nY\n")
    assert result.exit_code == 0
    assert "Conflict or error occurred while restoring" in result.stdout
    assert "Synchronization completed successfully" in result.stdout
