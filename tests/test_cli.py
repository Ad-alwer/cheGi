import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path
from chegi.cli import app
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
def test_global_setup_git_install_success(mock_install: MagicMock, mock_valid_git_env, tmp_path: Path):
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
def test_scan_with_repos(mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path):
    """Tests successful scan execution and UI output."""
    mock_find_repos.return_value = [tmp_path]
    mock_status = GitStatus(
        path=tmp_path,
        repo_name="mock_project",
        branch="main",
        is_dirty=True,
        has_staged_files=False,
        has_remote=True
    )
    mock_analyze.return_value = [mock_status]
    
    result = runner.invoke(app, ["scan", str(tmp_path)])
    
    assert result.exit_code == 0
    assert "Scanning" in result.stdout
    assert "mock_project" in result.stdout

@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_filter_dirty(mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path):
    """Tests the --dirty flag to ensure clean repositories are filtered out."""
    mock_find_repos.return_value = [Path("/repo1"), Path("/repo2")]
    
    dirty_repo = GitStatus(Path("/repo1"), "dirty_repo", "main", is_dirty=True, has_staged_files=False, has_remote=True)
    clean_repo = GitStatus(Path("/repo2"), "clean_repo", "main", is_dirty=False, has_staged_files=False, has_remote=True)
    
    mock_analyze.return_value = [dirty_repo, clean_repo]
    
    result = runner.invoke(app, ["scan", "--dirty", str(tmp_path)])
    
    assert "dirty_repo" in result.stdout
    assert "clean_repo" not in result.stdout

@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_filter_staged(mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path):
    """Tests the --staged flag to ensure only repos with staged files are shown."""
    mock_find_repos.return_value = [Path("/repo1"), Path("/repo2")]
    
    staged_repo = GitStatus(Path("/repo1"), "staged_repo", "main", is_dirty=True, has_staged_files=True, has_remote=True)
    unstaged_repo = GitStatus(Path("/repo2"), "unstaged_repo", "main", is_dirty=True, has_staged_files=False, has_remote=True)
    
    mock_analyze.return_value = [staged_repo, unstaged_repo]
    
    result = runner.invoke(app, ["scan", "--staged", str(tmp_path)])
    
    assert "staged_repo" in result.stdout
    assert "unstaged_repo" not in result.stdout

@patch("chegi.cli.GitAnalyzer.analyze_concurrently")
@patch("chegi.cli.find_git_repos")
def test_scan_with_security_flag(mock_find_repos: MagicMock, mock_analyze: MagicMock, tmp_path: Path):
    """Tests if --security flag correctly triggers the security scanner."""
    mock_find_repos.return_value = [tmp_path]
    mock_status = GitStatus(tmp_path, "mock_project", "main", False, False, True, "[green]Safe[/green]")
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
def test_guard_success_no_secrets(mock_get_staged: MagicMock, mock_find_sensitive: MagicMock):
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
# Configuration Command Tests
# ==========================================

def test_config_list(tmp_path: Path):
    """Tests listing configuration settings."""
    result = runner.invoke(app, ["config", "list", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Max Depth" in result.stdout

def test_config_set(tmp_path: Path):
    """Tests updating a configuration value."""
    result = runner.invoke(app, ["config", "set", "max_depth", "5", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Successfully updated 'max_depth' to 5" in result.stdout

def test_config_exclude_add_remove(tmp_path: Path):
    """Tests adding and then removing an item from the exclude list."""
    runner.invoke(app, ["config", "exclude-add", "junk", "--path", str(tmp_path)])
    res_remove = runner.invoke(app, ["config", "exclude-remove", "junk", "--path", str(tmp_path)])
    assert res_remove.exit_code == 0
    assert "Removed 'junk'" in res_remove.stdout

# ==========================================
# Gitignore Command Tests
# ==========================================

@patch("chegi.cli.EnvManager")
@patch("chegi.cli.questionary.checkbox")
def test_gitignore_success_without_commit(mock_checkbox: MagicMock, mock_env_manager: MagicMock):
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
def test_gitignore_success_with_commit(mock_checkbox: MagicMock, mock_env_manager: MagicMock):
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
def test_gitignore_overwrite_abort(mock_confirm: MagicMock, mock_checkbox: MagicMock, mock_env_manager: MagicMock):
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
def test_gitignore_multiple_languages(mock_checkbox: MagicMock, mock_env_manager: MagicMock):
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
def test_gitignore_no_selection_abort(mock_checkbox: MagicMock, mock_env_manager: MagicMock):
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
def test_gitignore_not_a_git_repo(mock_checkbox: MagicMock, mock_env_manager: MagicMock):
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
    
    # Removed capture_output=True to match actual code
    mock_subprocess.assert_any_call(
        ["git", "commit", "--amend", "-m", "chore: new message"],
        check=True
    )


@patch("chegi.cli.subprocess.run")
def test_reword_not_a_git_repo(mock_subprocess: MagicMock):
    """Tests reword command when executed outside a git repository."""
    import subprocess
    
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
    mock_text: MagicMock, mock_select: MagicMock, mock_rebase: MagicMock, mock_subprocess: MagicMock
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
            # Mock git log returning the existing commit message
            return MagicMock(stdout="chore: old message\n", returncode=0)
        return MagicMock(returncode=0)
        
    mock_subprocess.side_effect = mock_run_side_effect
    
    # Simulate the user submitting the exact same message
    mock_text.return_value.ask.return_value = "chore: old message"
    
    result = runner.invoke(app, ["reword"])
    
    assert result.exit_code == 0
    # Updated to match the new unchanged message
    assert "Message is unchanged" in result.stdout

@patch("chegi.cli.subprocess.run")
def test_reword_pagination_invalid_range(mock_subprocess: MagicMock):
    """Tests that providing a start index >= end index raises an error."""
    # Mock is-inside-work-tree to pass
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
            # This is the menu fetch call
            return MagicMock(stdout="abc1234 feat: msg1\ndef5678 chore: msg2\n", returncode=0)
        if "log" in cmd and "--format=%B" in cmd:
            # This is the old message fetch call
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
        check=True, capture_output=True, text=True
    )

@patch("chegi.cli.subprocess.run")
@patch("chegi.cli.questionary.select")
@patch("chegi.cli.questionary.text")
def test_reword_pagination_only_end(
    mock_text: MagicMock, mock_select: MagicMock, mock_subprocess: MagicMock
):
    """Tests the logic $skip = max(0, end - 10)$ when only --end is provided."""
    
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
    
    # Verify the formula calculated correctly
    mock_subprocess.assert_any_call(
        ["git", "log", "--max-count=10", "--skip=15", "--format=%h %s"],
        check=True, capture_output=True, text=True
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
    assert "Sync aborted. Please commit or stash" in result.stdout


@patch("chegi.cli.is_workspace_clean")
def test_sync_dirty_workspace_abort_second_confirm(mock_is_clean: MagicMock):
    """Tests if sync aborts when the user declines the second safety confirmation."""
    mock_is_clean.return_value = False
    
    # Input "Y" for first confirm, "N" for the second
    result = runner.invoke(app, ["sync"], input="Y\nN\n")
    
    assert result.exit_code == 1
    assert "Sync aborted. Please commit or stash" in result.stdout


@patch("chegi.cli.pop_stash")
@patch("chegi.cli.push_changes")
@patch("chegi.cli.pull_rebase")
@patch("chegi.cli.stash_changes")
@patch("chegi.cli.is_workspace_clean")
def test_sync_dirty_workspace_full_success(
    mock_is_clean: MagicMock, mock_stash: MagicMock, mock_pull: MagicMock, 
    mock_push: MagicMock, mock_pop: MagicMock
):
    """Tests the full flow: stash -> pull -> push -> pop when user confirms both prompts."""
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
    assert "Conflict or error during pull --rebase" in result.stdout
    assert "Please resolve conflicts manually" in result.stdout


@patch("chegi.cli.pop_stash")
@patch("chegi.cli.push_changes")
@patch("chegi.cli.pull_rebase")
@patch("chegi.cli.stash_changes")
@patch("chegi.cli.is_workspace_clean")
def test_sync_pop_stash_conflict_warning(
    mock_is_clean: MagicMock, mock_stash: MagicMock, mock_pull: MagicMock, 
    mock_push: MagicMock, mock_pop: MagicMock
):
    """
    Tests that a conflict during 'stash pop' only issues a warning 
    but DOES NOT fail the sync command (exit 0).
    """
    mock_is_clean.return_value = False
    # Simulate a conflict when popping stash
    mock_pop.side_effect = RuntimeError("Auto-merging failed; conflicts in app.py")
    
    result = runner.invoke(app, ["sync"], input="Y\nY\n")
    
    # Developer Note: Exit code must be 0 because sync to remote was successful!
    assert result.exit_code == 0
    assert "Conflict or error occurred while restoring stashed changes" in result.stdout
    assert "Synchronization completed successfully" in result.stdout

# ==========================================
# Setup Command Tests
# ==========================================

# Simple dummy data for basic tests
DUMMY_ENV_DATA = {
    "levels": {"1": ["git"]},
    "levels_info": {"1": "Core"},
    "tools": {
        "git": {
            "check_cmd": "git --version",
            "requires": [],
            "install": {
                "apt": "sudo apt install git",
                "default": "brew install git"
            }
        }
    }
}

# Complex dummy data for testing dependency resolution (Topological Sort)
# Dependency Chain: tool_c -> requires -> tool_a -> requires -> tool_b
# They are listed out of order intentionally in the 'levels' array.
DUMMY_ENV_DATA_DEPS = {
    "levels": {"1": ["tool_c", "tool_a", "tool_b"]},
    "levels_info": {"1": "Core"},
    "tools": {
        "tool_c": {
            "check_cmd": "cmd_c",
            "requires": ["tool_a"],
            "install": {"default": "install c"}
        },
        "tool_a": {
            "check_cmd": "cmd_a",
            "requires": ["tool_b"],
            "install": {"default": "install a"}
        },
        "tool_b": {
            "check_cmd": "cmd_b",
            "requires": [],
            "install": {"default": "install b"}
        }
    }
}


@patch("chegi.cli.EnvManager")
def test_setup_unsupported_environment(mock_env_manager: MagicMock):
    """Tests setup command with an environment not in the database."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_available_envs.return_value = ["python", "node"]

    result = runner.invoke(app, ["setup", "ruby"])

    assert result.exit_code == 1
    assert "is not supported" in result.stdout


@patch("chegi.cli.EnvManager")
def test_setup_failed_to_load_env_data(mock_env_manager: MagicMock):
    """Tests setup command when environment data fails to load."""
    mock_instance = mock_env_manager.return_value
    mock_instance.get_available_envs.return_value = ["python"]
    mock_instance.get_env.return_value = None

    result = runner.invoke(app, ["setup", "python"])

    assert result.exit_code == 1
    assert "Failed to load configuration data" in result.stdout


@patch("chegi.cli.SystemInstaller")
@patch("chegi.cli.EnvManager")
def test_setup_all_tools_already_installed(mock_env_manager: MagicMock, mock_installer: MagicMock):
    """Tests setup when all tools are already installed on the system."""
    mock_env_manager.return_value.get_available_envs.return_value = ["python"]
    mock_env_manager.return_value.get_env.return_value = DUMMY_ENV_DATA
    
    mock_installer.get_os_package_manager.return_value = "apt"
    mock_installer.is_tool_installed.return_value = (True, "git version 2.34.1")

    result = runner.invoke(app, ["setup", "python"])

    assert result.exit_code == 0
    assert "already installed" in result.stdout


@patch("chegi.cli.questionary")
@patch("chegi.cli.SystemInstaller")
@patch("chegi.cli.EnvManager")
def test_setup_interactive_abort(mock_env_manager: MagicMock, mock_installer: MagicMock, mock_questionary: MagicMock):
    """Tests setup when the user aborts the interactive tool selection."""
    mock_env_manager.return_value.get_available_envs.return_value = ["python"]
    mock_env_manager.return_value.get_env.return_value = DUMMY_ENV_DATA
    
    mock_installer.get_os_package_manager.return_value = "apt"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    
    mock_questionary.checkbox.return_value.ask.return_value = []

    result = runner.invoke(app, ["setup", "python"])

    assert result.exit_code == 0
    assert "Setup aborted by user" in result.stdout


@patch("chegi.cli.SystemInstaller")
@patch("chegi.cli.EnvManager")
def test_setup_auto_yes_installation_success(mock_env_manager: MagicMock, mock_installer: MagicMock):
    """Tests successful installation using the --yes flag."""
    mock_env_manager.return_value.get_available_envs.return_value = ["python"]
    mock_env_manager.return_value.get_env.return_value = DUMMY_ENV_DATA
    
    mock_installer.get_os_package_manager.return_value = "apt"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    mock_installer.run_custom_command.return_value = True

    result = runner.invoke(app, ["setup", "python", "--yes"])

    assert result.exit_code == 0
    assert "installed successfully" in result.stdout
    assert "Environment setup completed successfully" in result.stdout
    mock_installer.run_custom_command.assert_called_with("sudo apt install git")


@patch("chegi.cli.SystemInstaller")
@patch("chegi.cli.EnvManager")
def test_setup_installation_keyboard_interrupt(mock_env_manager: MagicMock, mock_installer: MagicMock):
    """Tests if Ctrl+C during installation is handled cleanly."""
    mock_env_manager.return_value.get_available_envs.return_value = ["python"]
    mock_env_manager.return_value.get_env.return_value = DUMMY_ENV_DATA
    
    mock_installer.get_os_package_manager.return_value = "apt"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    
    mock_installer.run_custom_command.side_effect = KeyboardInterrupt()

    result = runner.invoke(app, ["setup", "python", "--yes"])

    assert result.exit_code == 1
    assert "Installation interrupted by user" in result.stdout


@patch("chegi.cli.SystemInstaller")
@patch("chegi.cli.EnvManager")
def test_setup_dependency_resolution_order(mock_env_manager: MagicMock, mock_installer: MagicMock):
    """Tests if topological sort correctly reorders installation queue based on dependencies.
    
    Even though tools are defined in order c -> a -> b, they should be installed
    in order b -> a -> c because c requires a, and a requires b.
    """
    mock_env_manager.return_value.get_available_envs.return_value = ["python"]
    mock_env_manager.return_value.get_env.return_value = DUMMY_ENV_DATA_DEPS
    
    mock_installer.get_os_package_manager.return_value = "default"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    mock_installer.run_custom_command.return_value = True

    result = runner.invoke(app, ["setup", "python", "--yes"])

    assert result.exit_code == 0
    
    # Extract the order of calls to run_custom_command
    calls = mock_installer.run_custom_command.call_args_list
    installed_cmds = [call[0][0] for call in calls]
    
    # Verify the topological sort order
    assert installed_cmds == ["install b", "install a", "install c"]


@patch("chegi.cli.SystemInstaller")
@patch("chegi.cli.EnvManager")
def test_setup_dependency_missing_skip(mock_env_manager: MagicMock, mock_installer: MagicMock):
    """Tests if tools are skipped correctly when their prerequisites fail to install."""
    mock_env_manager.return_value.get_available_envs.return_value = ["python"]
    mock_env_manager.return_value.get_env.return_value = DUMMY_ENV_DATA_DEPS
    
    mock_installer.get_os_package_manager.return_value = "default"
    mock_installer.is_tool_installed.return_value = (False, "Not installed")
    
    # Simulate a failure when installing 'tool_b' (the base dependency)
    def mock_run_cmd(cmd):
        if cmd == "install b":
            return False
        return True
        
    mock_installer.run_custom_command.side_effect = mock_run_cmd

    result = runner.invoke(app, ["setup", "python", "--yes"])

    # Output should reflect that tool_b failed, and therefore tool_a and tool_c were skipped
    assert "Failed to install tool_b" in result.stdout
    assert "Skipping tool_a: Missing prerequisites (tool_b)" in result.stdout
    assert "Skipping tool_c: Missing prerequisites (tool_a)" in result.stdout
    
    # Only tool_b should have been attempted
    assert mock_installer.run_custom_command.call_count == 1
    mock_installer.run_custom_command.assert_called_once_with("install b")
